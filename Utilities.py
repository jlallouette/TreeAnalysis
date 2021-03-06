from abc import ABC, abstractmethod
import copy

# Parameter wrapper
class Parameters:
	def __init__(self, **kwargs):
		self.allParams = kwargs

	def SetParam(self, name, val):
		self.allParams[name] = val

	def GetKeyTuple(self):
		kt = []
		for name, val in self.allParams.items():
			if any(isinstance(val, tp) for tp in [str, int, bool, float, tuple, range]):
				kt.append((name, None, val))
			elif isinstance(val, Parameterizable):
				kt.append((name, type(val).__name__, val.GetParamKeyTuple()))
			elif isinstance(val, ReferenceHolder):
				raise ValueError('Cannot use ReferenceHolder field for memoization.')
			else:
				raise NotImplementedError()
				
		return KeyTuple(sorted(kt, key=lambda x:x[0]))

class KeyTuple(tuple):
	def __init__(self, b):
		tuple.__init__(tuple(b))

# Describe parameters for automatic UI generation
class ParametersDescr:
	def __init__(self, paramD = {}):
		# dictionary with param name as key and tuple as value:
		# tuple contains (default value, class, authorizedValues)
		self.description = paramD
	
	def getParams(self):
		return Parameters(**{name : tup[0] for name, tup in self.description.items()})

class NamedObject(ABC):
	allInstances = {}

	def __init__(self):
		# Initialize unique name
		if not hasattr(self, 'uniqueName'):
			clsName = self.__class__.__name__
			if clsName in NamedObject.allInstances:
				NamedObject.allInstances[clsName].append(self)
			else:
				NamedObject.allInstances[clsName] = [self]
			self.uniqueName = '{} {}'.format(clsName, len(NamedObject.allInstances[clsName]))

	# Returns a human readable unique name
	def GetUniqueName(self):
		return self.uniqueName
		
# Parameterizable abstract base class
class Parameterizable(NamedObject):
	def __init__(self, params = None):
		NamedObject.__init__(self)
		if params is None:
			params = self.GetDefaultParams().getParams()
		self.SetParameters(params)

	def SetParameters(self, params):
		self.params = params
		if isinstance(params, Parameters):
			for name, val in params.allParams.items():
				setattr(self, name, val)
		elif isinstance(params, KeyTuple):
			for name, objName, vals in params:
				if objName is None:
					setattr(self, name, vals)
				else:
					setattr(self, name, eval(objName + '(vals)'))
		else:
			raise NotImplementedError()

	def GetParamKeyTuple(self):
		newParam = Parameters(**{name:getattr(self, name) for name in self.GetDefaultParams().description.keys()})
		return newParam.GetKeyTuple()

	def GetDefaultParams(self):
		return ParametersDescr()

	def CopyParamsFrom(self, other):
		for name, val in self.GetDefaultParams().description.items():
			p = getattr(self, name)
			if isinstance(p, Parameterizable):
				otherp = getattr(other, name)
				if isinstance(otherp, type(p)):
					p.CopyParamsFrom(otherp)
				# TODO isinstance would be bettre here but it creates a cyclical dependency with DashUtilities, TOFIX later.
				elif 'DashInterfacable' in [cls.__name__ for cls in self.__class__.mro()]:
					savk = self._getSubAuthValKey(name, type(otherp))
					setattr(self, name, self.subAuthValsObj[savk])
					getattr(self, name).CopyParamsFrom(otherp)
				else:
					raise NotImplementedError()
			elif not isinstance(p, ReferenceHolder):
				# TODO Maybe something to do about the specific reference holder being selected here
				setattr(self, name, getattr(other, name))

# Utility class for Usable
class ClickableData:
	def __init__(self, func, ot, on, of):
		self.func = func
		self.outputType = ot
		self.outputName = on
		self.outputField = of

# Usable abstract base class
class Usable(NamedObject):
	reg = {}

	def __init__(self):
		NamedObject.__init__(self)

	def GetUsableMethods(self):
		ret = []
		for className, funcs in Usable.reg.items():
			if className in [cls.__name__ for cls in self.__class__.mro()]:
				ret += funcs
		return {f.func.__name__:f for f in ret}

	def Clickable(outType = None, outName = None, outField = None):
		def InternalClickable(f):
			if f.__code__.co_argcount > 1:
				raise SyntaxWarning('Clickable methods should not take any parameters besides self.')
			scn = f.__qualname__.split('.')
			if len(scn) == 1:
				raise SyntaxWarning('Clickable should only decorate methods of subclasses of "Usable".')
			className = scn[-2]
			if className in Usable.reg:
				Usable.reg[className].append(ClickableData(f, outType, outName, outField))
			else:
				Usable.reg[className] = [ClickableData(f, outType, outName, outField)]
			return f
		return InternalClickable

# Interfacable abstract base class
class Interfacable(NamedObject):
	def __init__(self):
		NamedObject.__init__(self)

	@abstractmethod
	def GetLayout(self, hideParams = False, hideUsage = False):
		pass

# Parametrizable class that is linked to an app
class AppParameterizable(Parameterizable):
	def __init__(self):
		self.appOwner = None
		Parameterizable.__init__(self)

	# Sets the subclass of GenericApp that owns it
	def setAppOwner(self, appOwner):
		self.appOwner = appOwner
		
	# Get the param description corresponding to name
	def _getInputReferenceParam(self, name):
		if hasattr(self, 'appOwner') and self.appOwner is not None:
			allSources = self.appOwner.GetProducers(name)
			return (ReferenceHolder(allSources[0]), ReferenceHolder, [ReferenceHolder(s) for s in allSources])
		else:
			return (ReferenceHolder(None), ReferenceHolder) 

# Utility class
class TmpObject(object):
	pass

# Utility class for Results
class OwnedAttributeHolder:
	def __init__(self, name, owner, value, sources):
		self.name = name
		self.owner = owner
		self.value = value
		self.sources = sources

	def GetValue(self):
		return self.value

	def __enter__(self):
		# Sets a thread local class variable in Results that tracks which data are being used to make the new one
		Results.usedSources.append(self)

	def __exit__(self, exc_type, exc_value, traceback):
		Results.usedSources.remove(self)

	def HasSameSourcesAs(self, other):
		return set(self.sources) == set(other.sources if isinstance(other, OwnedAttributeHolder) else other)
	
	def GetAllSources(self):
		res = [self.owner]
		for s in self.sources:
			res += s.GetAllSources()
		return res
	
	def GetFullSourceName(self, layersToPeel = 0, onlyFinalSources = False):
		if onlyFinalSources:
			if len(self.sources) > 0:
				return ', '.join(s.GetFullSourceName(onlyFinalSources = True) for s in self.sources)
			else:
				return self.owner.GetUniqueName()
		elif layersToPeel > 0:
			return ', '.join(s.GetFullSourceName(layersToPeel = layersToPeel - 1) for s in self.sources)
		else:
			return '{}({})'.format(self.owner.GetUniqueName(), ', '.join(s.GetFullSourceName() for s in self.sources))

# Wraps results from a simulation
class Results(object):
	# thread-local list that tracks which sources are being used to synthesize data
	# TODO make it thread local
	usedSources = []#threading.local()

	def __init__(self, owner):
		# Dict mapping attribute name -> list of owned attribute holders
		object.__setattr__(self, 'attributes', {})
		object.__setattr__(self, 'owner', owner)
		#self.attributes = {}
		#self.owner = owner

	#def __add__(self, other):
	#	res = Results()
	#	for name, val in self.__dict__.items():
	#		setattr(res, name, val)
	#	for name, val in other.__dict__.items():
	#		if not hasattr(self, name):
	#			setattr(res, name, val)
	#		else:
	#			raise Exception('Name collision in Results object: {}'.format(name))
	#	return res
	def addResults(self, other):
		for name, lst in other.attributes.items():
			if name in self.attributes:
				for oah in lst:
					querry = self.GetOwnedAttr(name, lambda o: o.HasSameSourcesAs(oah) and o.owner == oah.owner)
					if len(querry) > 0:
						for q in querry:
							q.value = oah.value
					else:
						self.attributes[name].append(oah)
			else:
				self.attributes[name] = copy.copy(lst)

	def ReOwn(self, newOner):
		object.__setattr__(self, 'owner', newOner)
		for name, lst in self.attributes.items():
			for oah in lst:
				oah.owner = newOner
				oah.sources = []

	# Sets a new attribute or update an already existing attribute from the same owner
	def __setattr__(self, name, value):
		ah = OwnedAttributeHolder(name, self.owner, value, copy.copy(Results.usedSources))
		if name in self.attributes:
			modif = False
			for h in self.attributes[name]:
				if h.owner == self.owner and h.HasSameSourcesAs(ah):
					h.value = value
					modif = True
					break
			if not modif:
				self.attributes[name].append(ah)
		else:
			self.attributes[name] = [ah]

	# Returns the attribute corresponding to the owner and the current sources
	def __getattr__(self, name):
		if name.startswith('__'):
			return object.__getattr__(self, name)
		else:
			for h in self.attributes[name]:
				if h.owner == self.owner and h.HasSameSourcesAs(Results.usedSources):
					return h.value
		raise Exception('Cannot directly access an attribute that is not owned by the Results object.')
		
	def GetOwnedAttr(self, name, filterFunc = lambda x:True, ind = None, defVal = None):
		if name in self.attributes:
			res = [oah for oah in self.attributes[name] if filterFunc(oah)]
			if ind is None:
				return res
			elif ind < len(res):
				return res[ind].GetValue()
			else:
				return defVal
		else:
			return [] if ind is None else defVal

	def HasAttr(self, name, filterFunc = lambda x:True):
		if not name in self.attributes:
			return False
		else:
			for oah in self.attributes[name]:
				if filterFunc(oah):
					return True
			return False
			
		return name in self.attributes

# Holds a reference, useful when a Parameterizable object has a parameter that can link 
# to several different objects, without owning these objects
class ReferenceHolder:
	allRefs = {}

	def __init__(self, val):
		if type(val) == str:
			self.value = ReferenceHolder.allRefs[val]
		else:
			self.value = val
			ReferenceHolder.allRefs[str(self)] = self.value
	
	def __repr__(self):
		if self.value is None:
			return 'EmptyReferenceHolder'
		elif isinstance(self.value, NamedObject):
			return self.value.GetUniqueName()
		else:
			raise NotImplementedError('Only NamdeObject objects can be held by ReferenceHolder.')

	def __eq__(self, other):
		return self.value == other.value

# Abstract Base class for all object that hold a result object
class ResultHolder:
	def __init__(self):
		self.results = Results(self)

	def SetResults(self, res):
		self.results = res

