import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from Utilities import *

# Interfacable abstract base class
class Interfacable(ABC):
	@abstractmethod
	def GetLayout(self, hideParams = False, hideUsage = False):
		pass

def getDCCElemForType(elemId, name, cls, val):
	elem = None
	elemIdsFieldNames = []
	if cls == str:
		elem = html.Div([html.Label(name),dcc.Input(id=elemId, type='text', value=val)])
		elemIdsFieldNames.append((elemId, 'value'))
	elif cls in [int, float]:
		elem = html.Div([html.Label(name),dcc.Input(id=elemId, type='number', value=val)])
		elemIdsFieldNames.append((elemId, 'value'))
	elif cls == bool:
		elem = dcc.Checklist(id=elemId, options=[{'label': name, 'value': name}], values=[name] if val else [])
		elemIdsFieldNames.append((elemId, 'values'))
	elif cls == tuple:
		subelems = []
		for i,v in enumerate(val):
			eid = elemId+'_{}'.format(i)
			subelems.append(dcc.Input(
						id=eid, 
						type='number' if type(v) in [int, float] else 'text', 
						value=v))
			elemIdsFieldNames.append((eid, 'value', i))
		elem = html.Div([html.Label(name), html.Div(subelems)])
	elif cls == range:
		elem = html.Div([html.Label(name),
			html.Label('start:'),dcc.Input(id=elemId+'_start', type='number', value=val.start),
			html.Label('end:'),dcc.Input(id=elemId+'_end', type='number', value=val.start + len(val))
			])
		elemIdsFieldNames.append((elemId+'_start', 'value', 0))
		elemIdsFieldNames.append((elemId+'_end', 'value', 1))
	return elem, elemIdsFieldNames

# Small structures responsible for signal mapping
class DashFieldData:
	def __init__(self, elemId, fieldName, obj, attrName, subKey=None):
		self.id = elemId
		self.fieldName = fieldName
		self.obj = obj
		self.attrName = attrName
		self.subKey = subKey

class DashUseData:
	def __init__(self, elemId, fieldName, obj, func):
		self.id = elemId
		self.fieldName = fieldName
		self.obj = obj
		self.func = func

class DashDropDownData:
	def __init__(self, elemId, fieldName, obj, attrName, ddDivId, allSavkKeys):
		self.id = elemId
		self.fieldName = fieldName
		self.obj = obj
		self.attrName = attrName
		self.divId = ddDivId
		self.allSavkKeys = allSavkKeys

# Interfacable elements for Dash
class DashInterfacable(Interfacable):
	def __init__(self):
		self.subAuthValsObj = {}
		self._fullDivId = self._getElemId('special', 'all')
		self._uselessDivIds = {name:self._getElemId('special', 'uselessDiv'+name) for name in ['use', 'all', 'anyParamChange']}

		self._fillFieldData = True
		self._fieldData = []
		self._useData = []
		self._dropDownData = []
		self._customLayouts = {}
		self._defaultLayout = DashVerticalLayout()

	def _getElemId(self, elemType, name):
		return '{}_{}_{}'.format(id(self), elemType, name)

	def _getSubAuthValKey(self, name, cls):
		return '{}_{}'.format(name, cls if type(cls) == str else cls.__name__)

	# Overload this method to display more than just parameters
	def _getInnerLayout(self):
		return None

	# Overload this method to build the signals of the inner layout
	def _buildInnerLayoutSignals(self):
		return None

	def _getCustomLayout(self, name):
		if name in self._customLayouts:
			return self._customLayouts[name]
		else:
			return self._defaultLayout
	
	# Call this method to set special layouts for sub elements
	def _setCustomLayout(self, name, layout):
		self._customLayouts[name] = layout

	# Generate the callback function that will be called upon modifications of fields
	def _generateFieldCallback(self):
		def UpdateValues(*values):
			# First update all values
			for v, dfd in zip(values, self._fieldData):
				if dfd.subKey is None:
					oldVal = getattr(dfd.obj, dfd.attrName)
					if isinstance(oldVal, Parameterizable):
						savk = self._getSubAuthValKey(dfd.attrName, v)
						setattr(dfd.obj, dfd.attrName, self.subAuthValsObj[savk])
					else:
						cls = type(oldVal)
						setattr(dfd.obj, dfd.attrName, cls(v))
				else:
					oldVal = getattr(dfd.obj, dfd.attrName)
					if type(oldVal) == tuple:
						cls = type(oldVal[dfd.subKey])
						oldVal = list(oldVal)
						oldVal[dfd.subKey] = cls(v)
						oldVal = tuple(oldVal)
					elif type(oldVal) == range:
						if dfd.subKey == 0:
							oldVal = range(int(v), int(v) + len(oldVal))
						else:
							oldVal = range(oldVal.start, int(v))
					else:
						try:
							cls = type(oldVal[dfd.subKey])
							oldVal[dfd.subKey] = cls(v)
						except:
							raise ValueError('Attribute {} of object {} cannot be updated with subkey {}.'.format(dfd.attrName, dfd.obj, dfd.subKey))
					setattr(dfd.obj, dfd.attrName, oldVal)
			# Then re-generate the layout
			#fullLayout = self.GetLayout()# TODO Options ?
			return ''
		return UpdateValues

	def _generateUseCallback(self):
		def CallMethods(*values):
			for v, ufd in zip(values, self._useData):
				if v is not None and v > 0:
					ufd.func(ufd.obj)
			fullLayout = self.GetLayout()# TODO Options ?
			return fullLayout.children
		return CallMethods

	def _generateDropDownCallback(self, ddd):
		def UpdateDropDown(value):
			subLayouts = []
			for key in ddd.allSavkKeys:
				currObj = self.subAuthValsObj[key]
				subLayouts.append(currObj.GetLayout(hideFull = (type(currObj).__name__ != value)))
			return subLayouts
		return UpdateDropDown

	def _generateAnyChangeCallback(self, acc):
		def AnyChangeCB(*values):
			return acc(values)
		return AnyChangeCB

	# Bind all signals
	# anyChangeCallBacks should be a dict of (outputId, outputField) -> callBackFunction that returns what to put there
	def BuildAllSignals(self, app, anyChangeCallBacks = {}):
		anyChangeInputs = []

		# First handle signals linked with own fields
		allInputs = [Input(fd.id, fd.fieldName) for fd in self._fieldData]
		app.callback(Output(self._uselessDivIds['all'], 'children'), allInputs)(self._generateFieldCallback())

		anyChangeInputs.append(Input(self._uselessDivIds['all'], 'children'))

		# Then handle signals tied to dropdowns
		for ddd in self._dropDownData:
			app.callback(Output(ddd.divId, 'children'), [Input(ddd.id, ddd.fieldName)])(self._generateDropDownCallback(ddd))

			anyChangeInputs.append(Input(ddd.divId, 'children'))

		# Then handle action signals
		allInputs = [Input(ud.id, ud.fieldName) for ud in self._useData]
		app.callback(Output(self._fullDivId, 'children'), allInputs)(self._generateUseCallback())

		# Then treat signals of parameters sublayouts
		for name, obj in self.subAuthValsObj.items():
			obj.BuildAllSignals(app)

			anyChangeInputs.append(Input(obj._uselessDivIds['anyParamChange'], 'children'))

		# Bind signals to detect any change in parameters or subparameters
		app.callback(Output(self._uselessDivIds['anyParamChange'], 'children'), anyChangeInputs)(lambda *x:'')
		for key, callBack in anyChangeCallBacks.items():
			app.callback(Output(key[0], key[1]), anyChangeInputs)(self._generateAnyChangeCallback(callBack))

		# Build inner layout signals
		self._buildInnerLayoutSignals()
						

	# Returns the current layout
	def GetLayout(self, hideParams = False, hideUsage = False, hideFull = False):
		params = []
		uses = []
		defaultTypes = [str, int, bool, float, tuple, range]

		# First display self parameters
		if isinstance(self, Parameterizable):
			paramDescr = self.GetDefaultParams()
			# Sort params to always have the same display order
			srtParams = sorted(paramDescr.description.items())
			for name, val in srtParams:
				defVal, cls, authVals = tuple(val[i] if len(val) > i else None for i in range(3))
				currVal = getattr(self, name)
				elemId = self._getElemId('params', name)

				# Infer default values from the cls attribute if we can
				if authVals is None and cls is not None and cls not in defaultTypes:
					authVals = cls.__subclasses__()
				# Infer cls attribute if it's not filled
				if cls is None:
					cls = type(currVal)
				# Raise exceptions if the currentValue is not of the correct class
				if not issubclass(type(currVal), cls):
					raise ValueError('{} is not of the correct type / class: {}'.format(currVal, cls.__name__))

				# Make a dropdown in case several authorized values are available
				if authVals is not None:
					if (cls in defaultTypes and currVal not in authVals) or (cls not in defaultTypes and currVal.__class__ not in authVals):
						raise ValueError('{} is not part of the authorized values: {}'.format(currVal, authVals))
					strValName = lambda av: str(av) if cls in defaultTypes else av.__name__
					params.append(
						html.Div([
						html.Label(name),
						dcc.Dropdown(
							id = elemId,
							options=[{'label': strValName(av), 'value': strValName(av)} for av in authVals], 
							value=currVal if cls in defaultTypes else currVal.__class__.__name__,
							clearable=False
						)]))
					if self._fillFieldData:
						self._fieldData.append(DashFieldData(elemId, 'value', self, name))
				# If the value has a default type
				elif cls in defaultTypes:
					elem, elemIdsFieldNames = getDCCElemForType(elemId, name, cls, currVal)
					params.append(elem)

					if self._fillFieldData:
						for eifd in elemIdsFieldNames:
							self._fieldData.append(DashFieldData(eifd[0], eifd[1], self, name, eifd[2] if len(eifd) > 2 else None))

				# If there are subparams to be displayed
				subLayouts = []
				allSavkKeys = []
				if isinstance(currVal, Interfacable):
					# Add the visible one
					subLayouts.append(currVal.GetLayout())
					savk = self._getSubAuthValKey(name, type(currVal))
					allSavkKeys.append(savk)
					if savk not in self.subAuthValsObj:
						self.subAuthValsObj[savk] = currVal
				# Also add all the other possibilities but hide them (for signal building later)
				if cls not in defaultTypes and authVals is not None and len(authVals) > 1:
					for av in authVals:
						if av != currVal.__class__ and DashInterfacable in av.mro():
							savk = self._getSubAuthValKey(name, av)
							allSavkKeys.append(savk)
							if savk not in self.subAuthValsObj:
								self.subAuthValsObj[savk] = av()
							subLayouts.append(self.subAuthValsObj[savk].GetLayout(hideFull = True))
				if len(subLayouts) > 0:
					ddDivId = self._getElemId('dropDownDiv', name)
					params.append(html.Div(subLayouts, id=ddDivId, style={'border-style':'solid', 'border-width':'1px'}))
					if self._fillFieldData and len(subLayouts) > 1:
						self._dropDownData.append(DashDropDownData(elemId, 'value', self, name, ddDivId, allSavkKeys))

		# Then display self uses
		if not hideUsage and isinstance(self, Usable):
			allUses = self.GetUsableMethods()
			for name, func in allUses.items():
				elemId = self._getElemId('uses', name)
				uses.append(html.Button(name, id=elemId))
				if self._fillFieldData:
					self._useData.append(DashUseData(elemId, 'n_clicks', self, func))

		# Then display inner layout if it exists
		innerElem = html.Div(self._getInnerLayout(), id=self._getElemId('special', 'innerLayout'))

		# Build Final Layout
		# TODO Write different layout arrangements
		paramStyle = {'display': 'none' if hideParams else 'inline-block'}
		useStyle = {'display': 'none' if hideUsage else 'inline-block'}
		fullStyle = {'display':'none' if hideFull else 'inline-block', 'width':'100%'}
		uselessStyle = {'display':'none'}

		uselessDivs = [html.Div(id=idv, style=uselessStyle) for nm, idv in self._uselessDivIds.items()]

		controlDivs = [self._getCustomLayout('params').GetLayout(params, style = paramStyle)]
		if len(uses) > 0:
			controlDivs.append(self._getCustomLayout('uses').GetLayout(uses, style=useStyle))
		controls = self._getCustomLayout('controls').GetLayout(controlDivs)

		allDivs = uselessDivs + [controls]
		if innerElem is not None:
			allDivs.append(innerElem)

		allDiv = self._getCustomLayout('all').GetLayout(allDivs)

		finalElem = html.Div(id=self._fullDivId, children=allDiv, style=fullStyle)

		self._fillFieldData = False
		return finalElem


# Abstract Base Class for dash layouts
class DashLayout(ABC):
	@abstractmethod
	def GetLayout(self, elems, style={}):
		pass

# Horizontal layout
class DashHorizontalLayout(DashLayout):
	def __init__(self, widthFunc = lambda ind, tot:int(100/tot)):
		self.widthFunc = widthFunc

	def GetLayout(self, elems, style={}):
		# Count visible elements
		nbVisElems = len([e for e in elems if not hasattr(e,'style') or 'display' not in e.style or e.style['display']!='none'])
		visInd = 0
		for e in elems:
			if not hasattr(e, 'style'):
				e.style = {}
			if 'display' not in e.style or e.style['display'] != 'none':
				e.style['display'] = 'inline-block'
				e.style['width'] = '{}%'.format(self.widthFunc(visInd, nbVisElems))
				visInd += 1
		return html.Div(elems, style=style) if len(style) > 0 else html.Div(elems)

# Vertical layout
class DashVerticalLayout(DashLayout):
	def GetLayout(self, elems, style={}):
		return html.Div(elems, style=style) if len(style) > 0 else html.Div(elems)
