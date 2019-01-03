import dill as pickle
import os

from DashUtilities import *
from datetime import datetime

class GenericAppStateSaver(Parameterizable, Usable, DashInterfacable):
	def __init__(self, app, stateFolder= 'data/states'):
		self.stateFolder = stateFolder

		Parameterizable.__init__(self)
		Usable.__init__(self)
		DashInterfacable.__init__(self)

		self.app = app
		self.innerMsg = ''

	def GetDefaultParams(self):
		return ParametersDescr({
			'name':('defaultName', str)
		})

	def _getInnerLayout(self):
		return self.innerMsg

	def _getData(self):
		return (self.app.simulations, self.app.analyzers, self.app.results)

	@Usable.Clickable()
	def SaveState(self):
		print('Saving state')
		filePath = os.path.join(self.stateFolder, '{}.pkl'.format(self.name))
		# Write results
		try:
			with open(filePath, 'wb') as f:
				pickle.dump(self._getData(), f)
			saved = True
		except:
			saved = False
		self.innerMsg = '{}: {}.'.format(datetime.now(), 'Saved' if saved else 'Could not save')

		return self._getInnerLayout()

class GenericAppStateLoader(Parameterizable, Usable, DashInterfacable):
	def __init__(self, app, stateFolder = 'data/states'):
		self.stateFolder = stateFolder

		Parameterizable.__init__(self)
		Usable.__init__(self)
		DashInterfacable.__init__(self)

		self.app = app
		self.innerMsg = ''

	def _getAllStateNames(self):
		try:
			return [''] + [fname[0:-4] for fname in os.listdir(self.stateFolder) if os.path.isfile(os.path.join(self.stateFolder, fname)) and fname.endswith('.pkl')]
		except:
			return ['']

	def GetDefaultParams(self):
		return ParametersDescr({
			'name':('', str, self._getAllStateNames())
		})

	def _getInnerLayout(self):
		return self.innerMsg

	def _buildInnerLayoutSignals(self, app):
		app.callback(Output(self.app.stateSaver._getElemId('params', 'name'), 'value'), 
			[Input(self._getElemId('uses', 'LoadState'), 'n_clicks')], 
			[State(self._getElemId('params', 'name'), 'value')])(self._getLoadStateCallback())

	def _getLoadStateCallback(self):
		def loadState(clicks, val):
			if clicks is not None and clicks > 0:
				return val
			else:
				raise dash.exceptions.PreventUpdate
		return loadState

	def _generateOptionsCallback(self):
		def updateOptions(value):
			options = [{'label': self._getDropDownValName(av, str, [str]),
						'value': self._getDropDownValName(av, str, [str])} for av in self._getAllStateNames()]
			return options
		return updateOptions

	def _loadData(self, data):
		simulations, analyzers, results = data
		elemNames = {}
		# Copy parameters
		for loadedElem in simulations + analyzers:
			name = loadedElem.GetUniqueName()
			elem = self.app.GetElemFromName(name)
			if elem is not None:
				elemNames[name] = elem
				elem.CopyParamsFrom(loadedElem)
			else:
				raise Exception('{} could not be found in the current application.'.format(name))
		# Re-attribute sources and owners in loaded results
		for attrName, lst in results.attributes.items():
			for oah in lst:
				name = oah.owner.GetUniqueName()
				if name in elemNames:
					oah.owner = elemNames[name]
				else:
					raise Exception('{} could not be found in the current application. Results element could not be re-owned.'.format(name))

		# Set all results
		self.app.results = results
		for elem in self.app.simulations + self.app.analyzers:
			elem.SetResults(self.app.results)

	@Usable.Clickable()
	def LoadState(self):
		if self.name != '':
			filePath = os.path.join(self.stateFolder, '{}.pkl'.format(self.name))
			if os.path.isfile(filePath):
				try:
					with open(filePath, 'rb') as f:
						data = pickle.load(f)
					ok = True
				except:
					self.innerMsg = '{}: Could not load {}.'.format(datetime.now(), filePath)
					ok = False
				if ok:
					self.innerMsg = '{}: Loaded.'.format(datetime.now())
					self._loadData(data)
			else:
				self.innerMsg = '{}: Could not load {}.'.format(datetime.now(), filePath)
		else:
			self.innerMsg = '{}: Nothing to load.'.format(datetime.now())
		return self._getInnerLayout()

