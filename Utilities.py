from abc import ABC, abstractmethod

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
				kt.append((name, type(val).__name__, val.params.GetKeyTuple()))
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

# Parameterizable abstract base class
class Parameterizable(ABC):
	def __init__(self, params = None):
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

# Usable abstract base class
class Usable(ABC):
	reg = {}

	def GetUsableMethods(self):
		ret = []
		for className, funcs in Usable.reg.items():
			if className in [cls.__name__ for cls in self.__class__.mro()]:
				ret += funcs
		return {f.__name__:f for f in ret}

	def Clickable(f):
		if f.__code__.co_argcount > 1:
			raise SyntaxWarning('Clickable methods should not take any parameters besides self.')
		scn = f.__qualname__.split('.')
		if len(scn) == 1:
			raise SyntaxWarning('Clickable should only decorate methods of subclasses of "Usable".')
		className = scn[-2]
		if className in Usable.reg:
			Usable.reg[className].append(f)
		else:
			Usable.reg[className] = [f]
		return f

# Wraps results from a simulation
class Results(object):
	def __add__(self, other):
		res = Results()
		for name, val in self.__dict__.items():
			setattr(res, name, val)
		for name, val in other.__dict__.items():
			if not hasattr(self, name):
				setattr(res, name, val)
			else:
				raise Exception('Name collision in Results object: {}'.format(name))
		return res
		


