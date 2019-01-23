import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash
import random
import math

from Utilities import *

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
	def __init__(self, elemId, fieldName, obj, clickData):
		self.id = elemId
		self.fieldName = fieldName
		self.obj = obj
		self.clickData = clickData

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
		Interfacable.__init__(self)

		self.subAuthValsObj = {}
		self._fullDivId = self._getElemId('special', 'fullDiv')
		self._uselessDivIds = {name:self._getElemId('special', 'uselessDiv'+name) for name in ['use', 'all', 'anyParamChange']}

		self._fillFieldData = True
		self._fieldData = []
		self._useData = []
		self._dropDownData = []
		self._customLayouts = {}

	def _getElemId(self, elemType, name):
		return '{}_{}_{}'.format(id(self), elemType, name)

	def _getSubAuthValKey(self, name, cls):
		return '{}_{}'.format(name, cls if type(cls) == str else cls.__name__)

	# Overload this method to display more than just parameters
	def _getInnerLayout(self):
		return None

	# Overload this method to build the signals of the inner layout
	def _buildInnerLayoutSignals(self, app):
		return None

	def _getDefaultLayout(self):
		return DashVerticalLayout()

	def _getCustomLayout(self, name):
		if name not in self._customLayouts:
			self._setCustomLayout(name, self._getDefaultLayout())
		return self._customLayouts[name]

	
	# Call this method to set special layouts for sub elements
	def _setCustomLayout(self, name, layout):
		layout.id = self._getElemId('special', name)
		self._customLayouts[name] = layout

	def _getDropDownValName(self, av, cls, defaultTypes):
		if cls == list:
			return av
		else:
			return str(av) if cls in defaultTypes else av.__name__

	# Generate the callback function that will be called upon modifications of fields
	def _generateFieldCallback(self):
		def UpdateValues(*values):
			# First update all values
			oneUpdt = False
			for v, dfd in zip(values, self._fieldData):
				if dfd.subKey is None:
					oldVal = getattr(dfd.obj, dfd.attrName)
					if isinstance(oldVal, Parameterizable):
						savk = self._getSubAuthValKey(dfd.attrName, v)
						if oldVal != self.subAuthValsObj[savk]:
							setattr(dfd.obj, dfd.attrName, self.subAuthValsObj[savk])
							oneUpdt = True
					else:
						cls = type(oldVal)
						try:
							# First try to build it from cls and value
							newVal = cls(v)
						except:
							# Otherwise, try by interpreting it
							newVal = eval(v)
						if oldVal != newVal:
							setattr(dfd.obj, dfd.attrName, newVal)
							oneUpdt = True
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
					if getattr(dfd.obj, dfd.attrName) != oldVal:
						setattr(dfd.obj, dfd.attrName, oldVal)
						oneUpdt = True
			if not oneUpdt:
				raise dash.exceptions.PreventUpdate
			return random.random()
		return UpdateValues

	def _generateUseCallback(self):
		def CallMethods(*values):
			specifUseData = [ud for ud in self._useData if ud.clickData.outputName is None]
			for v, ufd in zip(values, specifUseData):
				if v is not None and v > 0:
					ufd.clickData.func(ufd.obj)
			fullLayout = self.GetLayout()
			return fullLayout.children
		return CallMethods

	def _generateTargetedUseCallback(self, ud):
		def CallMethods(value):
			if value is not None and value > 0:
				return ud.clickData.func(ud.obj)
			else:
				raise dash.exceptions.PreventUpdate
		return CallMethods

	def _generateDropDownCallback(self, obj):
		def UpdateDropDown(value, style):
			if value == obj.__class__.__name__:
				if style['display'] == 'none':
					style['display'] = 'block'
				else:
					raise dash.exceptions.PreventUpdate
			else:
				if style['display'] != 'none':
					style['display'] = 'none'
				else:
					raise dash.exceptions.PreventUpdate
			return style
		return UpdateDropDown

	def _generateAnyChangeCallback(self, acc = lambda *v:random.random()):
		def AnyChangeCB(*values):
			if any(val != '' for val in values):
				return acc(values)
			else:
				raise dash.exceptions.PreventUpdate
			return ''
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
			for key in ddd.allSavkKeys:
				obj = self.subAuthValsObj[key]
				outId = obj._fullDivId
				app.callback(Output(outId, 'style'), [Input(ddd.id, ddd.fieldName)], [State(outId, 'style')])(self._generateDropDownCallback(obj))
				anyChangeInputs.append(Input(outId, 'style'))

		# Then handle default action signals
		allInputs = [Input(ud.id, ud.fieldName) for ud in self._useData if ud.clickData.outputName is None]
		app.callback(Output(self._fullDivId, 'children'), allInputs)(self._generateUseCallback())

		# Then handle targeted action signals
		for ud in self._useData:
			if ud.clickData.outputName is not None:
				ot, on, of = ud.clickData.outputType, ud.clickData.outputName, ud.clickData.outputField
				app.callback(Output(self._getElemId(ot, on), of), [Input(ud.id, ud.fieldName)])(self._generateTargetedUseCallback(ud))

		# Then treat signals of parameters sublayouts
		for name, obj in self.subAuthValsObj.items():
			obj.BuildAllSignals(app)

			anyChangeInputs.append(Input(obj._uselessDivIds['anyParamChange'], 'children'))

		# Bind signals to detect any change in parameters or subparameters
		app.callback(Output(self._uselessDivIds['anyParamChange'], 'children'), anyChangeInputs)(self._generateAnyChangeCallback())
		for key, callBack in anyChangeCallBacks.items():
			app.callback(Output(key[0], key[1]), anyChangeInputs)(self._generateAnyChangeCallback(callBack))

		# Build inner layout signals
		self._buildInnerLayoutSignals(app)
						

	# Returns the current layout
	def GetLayout(self, hideParams = False, hideUsage = False, hideFull = False, hideTitle = False):
		print('getting Layout for {}'.format(self))
		params = []
		uses = []
		defaultTypes = [str, int, bool, float, tuple, range, ReferenceHolder, list]

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
					if (cls in defaultTypes and currVal not in authVals) or (cls != list and cls not in defaultTypes and currVal.__class__ not in authVals):
						if isinstance(currVal, ReferenceHolder) and currVal.value is None:
							# Special case of reference holder
							currVal = authVals[0]
							setattr(self, name, currVal)
						elif not (isinstance(currVal, list) and all(v in authVals for v in currVal)):
							# Otherwise
							raise ValueError('{} is not part of the authorized values: {}'.format(currVal, authVals))
					params.append(
						html.Div([
						html.Label(name),
						dcc.Dropdown(
							id = elemId,
							options=[{'label': self._getDropDownValName(av, cls, defaultTypes),
									'value': self._getDropDownValName(av, cls, defaultTypes)} for av in authVals], 
							value=self._getDropDownValName(currVal, cls, defaultTypes) if cls in defaultTypes else currVal.__class__.__name__,
							clearable=isinstance(currVal, list),
							multi=(cls == list)
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
					subLayouts.append(currVal.GetLayout(hideTitle = True))
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
							subLayouts.append(self.subAuthValsObj[savk].GetLayout(hideFull = True, hideTitle=True))
				if len(subLayouts) > 0:
					ddDivId = self._getElemId('dropDownDiv', name)
					params.append(html.Div(subLayouts, id=ddDivId))#, style={'border-style':'solid', 'border-width':'1px'}))
					if self._fillFieldData and len(subLayouts) > 1:
						self._dropDownData.append(DashDropDownData(elemId, 'value', self, name, ddDivId, allSavkKeys))

		# Then display self uses
		if not hideUsage and isinstance(self, Usable):
			allUses = self.GetUsableMethods()
			for name, clickData in allUses.items():
				elemId = self._getElemId('uses', name)
				uses.append(html.Button(name, id=elemId))
				if self._fillFieldData:
					self._useData.append(DashUseData(elemId, 'n_clicks', self, clickData))

		# Then display inner layout if it exists
		innerElem = html.Div(self._getInnerLayout(), id=self._getElemId('special', 'innerLayout'))

		# Build Final Layout
		paramStyle = {'display': 'none' if hideParams else 'inline-block'}
		useStyle = {'display': 'none' if hideUsage else 'inline-block'}
		fullStyle = {'display':'none' if hideFull else 'inline-block'}
		titleStyle = {'display':'none' if hideTitle else 'inline-block'}
		uselessStyle = {'display':'none'}

		titleDiv = html.Div(html.H5(self.GetUniqueName()), style=titleStyle)

		uselessDivs = [html.Div(id=idv, style=uselessStyle, children='') for nm, idv in self._uselessDivIds.items()]

		controlDivs = [self._getCustomLayout('params').GetLayout(params, style = paramStyle)]
		if len(uses) > 0:
			controlDivs.append(self._getCustomLayout('uses').GetLayout(uses, style=useStyle))
		controls = self._getCustomLayout('controls').GetLayout(controlDivs)

		allDivs = [titleDiv] + uselessDivs + [controls]
		if innerElem is not None:
			allDivs.append(innerElem)

		allDiv = self._getCustomLayout('all').GetLayout(allDivs)

		finalElem = html.Div(id=self._fullDivId, children=allDiv, style=fullStyle, className='InterfaceBlock')

		self._fillFieldData = False
		return finalElem


# Abstract Base Class for dash layouts
class DashLayout(ABC):
	def __init__(self, id=None, maxNbElem = math.inf):
		if id is None:
			self.id = str(random.random())
		else:
			self.id = id
		self.maxNbElem = maxNbElem

	@abstractmethod
	def GetLayout(self, elems, style={}):
		pass

# Horizontal layout
class DashHorizontalLayout(DashLayout):
	def __init__(self, widthFunc = lambda ind, tot:int(100/(tot+0.001)), id=None, maxNbElem = math.inf):
		DashLayout.__init__(self, id=id, maxNbElem=maxNbElem)
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
				e.style['vertical-align'] = 'top'
				e.style['width'] = '{}%'.format(self.widthFunc(visInd, nbVisElems))
				visInd += 1
		return html.Div(elems, style=style, id=self.id) if len(style) > 0 else html.Div(elems, id=self.id)

# Vertical layout
class DashVerticalLayout(DashLayout):
	def __init__(self, id=None, maxNbElem = math.inf):
		DashLayout.__init__(self, id=id, maxNbElem=maxNbElem)

	def GetLayout(self, elems, style={}):
		for e in elems:
			if not hasattr(e, 'style'):
				e.style = {}
			if 'display' not in e.style or e.style['display'] != 'none':
				e.style['display'] = 'block'
		return html.Div(elems, style=style, id=self.id) if len(style) > 0 else html.Div(elems, id=self.id)


class DashGridLayout(DashVerticalLayout):
	def __init__(self, columns = 2, id=None, maxNbElem = math.inf):
		DashVerticalLayout.__init__(self, id=id, maxNbElem=maxNbElem)
		self.columns = columns

	def GetLayout(self, elems, style={}):
		nbRows = math.ceil(len(elems) / self.columns)
		rows = []
		for i in range(nbRows):
			row = []
			for j in range(self.columns):
				ind = i*self.columns + j
				if ind < len(elems):
					row.append(elems[ind])
			rows.append(DashHorizontalLayout().GetLayout(row, style=style))
		return DashVerticalLayout.GetLayout(self, rows, style=style)

# Composite layout allowing more intricate positioning
class DashStructSeqLayout(DashLayout):
	def __init__(self, id=None, layoutStructure=None):
		DashLayout.__init__(self, id=id)
		if isinstance(layoutStructure, tuple):
			self.layout, child = layoutStructure
			if isinstance(child, list):
				self.subLayouts = [DashStructSeqLayout(layoutStructure=c) for c in child]
				self.maxNbElem = sum(sl.maxNbElem for sl in self.subLayouts)
			else:
				raise ValueError('The second element of the layoutStructure tuple must be a list of children.')
		elif isinstance(layoutStructure, DashLayout):
			self.layout = layoutStructure
			self.subLayouts = []
			self.maxNbElem = layoutStructure.maxNbElem
		else:
			raise ValueError('The layoutStructure parameter must either be a tuple or a DashLayout.')
		# Structure is given through a tuple in which the first element is the parent and the second a list of childs (each described as tuples)

	def GetLayout(self, elems, style={}):
		currInd = 0
		subElems = []
		if len(self.subLayouts) > 0:
			for sl in self.subLayouts:
				nextInd = min(currInd + sl.maxNbElem, len(elems))
				subElems.append(sl.GetLayout(elems[currInd:nextInd], style=style))
				currInd = nextInd
				if currInd >= len(elems):
					break
		else:
			subElems = elems
		return self.layout.GetLayout(subElems, style=style)
	
	
