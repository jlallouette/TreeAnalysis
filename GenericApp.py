import dill as pickle
import os

from ResultAnalyzers import *
from DashUtilities import *


class GenericAppStateSaver(Parameterizable, Usable, DashInterfacable):
	def __init__(self, app, dataFolder = 'data', listFile = 'statesList'):
		self.listFile = listFile
		self.dataFolder = dataFolder

		Parameterizable.__init__(self)
		Usable.__init__(self)
		DashInterfacable.__init__(self)

		self.app = app

	def GetDefaultParams(self):
		return ParametersDescr({
			'name':('defaultName', str)
		})

	def _getData(self):
		return (self.app.simulations, self.app.analyzers, self.app.results)

	@Usable.Clickable()
	def SaveState(self):
		print('Saving state')
		filePath = os.path.join(self.dataFolder, '{}.pkl'.format(self.name))
		listPath = os.path.join(self.dataFolder, '{}.pkl'.format(self.listFile))
		# Write results
		with open(filePath, 'wb') as f:
			pickle.dump(self._getData(), f)
		# Write results list
		if os.path.isfile(listPath):
			try:
				with open(listPath, 'rb') as f:
					states = pickle.load(f)
			except:
				states = {}
		else:
			states = {}
		states[self.name] = filePath
		with open(listPath, 'wb') as f:
			pickle.dump(states, f)

		return self._getInnerLayout()

class GenericAppStateLoader(Parameterizable, Usable, DashInterfacable):
	def __init__(self, app, dataFolder = 'data', listFile = 'statesList'):
		self.listFile = listFile
		self.dataFolder = dataFolder

		Parameterizable.__init__(self)
		Usable.__init__(self)
		DashInterfacable.__init__(self)

		self.app = app
		self.innerMsg = ''

	def _getAllStateNames(self):
		listPath = os.path.join(self.dataFolder, '{}.pkl'.format(self.listFile))
		# Write results list
		if os.path.isfile(listPath):
			try:
				with open(listPath, 'rb') as f:
					states = pickle.load(f)
			except:
				states = {}
		else:
			states = {}

		return [''] + [name for name, v in states.items()]

	def GetDefaultParams(self):
		return ParametersDescr({
			'name':('', str, self._getAllStateNames())
		})

	def _getInnerLayout(self):
		return self.innerMsg

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
			filePath = os.path.join(self.dataFolder, '{}.pkl'.format(self.name))
			if os.path.isfile(filePath):
				try:
					with open(filePath, 'rb') as f:
						data = pickle.load(f)
					ok = True
				except:
					self.innerMsg = 'Could not load {}.'.format(filePath)
					ok = False
				if ok:
					self.innerMsg = 'Loaded.'
					self._loadData(data)
			else:
				self.innerMsg = 'Could not load {}.'.format(filePath)
		else:
			self.innerMsg = 'Nothing to load.'
		return self._getInnerLayout()

class GenericApp(Parameterizable, Usable, DashInterfacable):
	def __init__(self):
		Parameterizable.__init__(self)
		Usable.__init__(self)
		DashInterfacable.__init__(self)

		self.simulations = []
		self.analyzers = []
		self.simManager = SimulationManager('{}_sims.pkl'.format(self.__class__.__name__))
		self.results = None

		self.stateSaver = GenericAppStateSaver(self)
		self.stateLoader = GenericAppStateLoader(self)

	def GetDefaultParams(self):
		return ParametersDescr({
			'memoize': (False, bool,)
		})

	def GetElemFromName(self, name):
		for elem in self.simulations + self.analyzers:
			if elem.GetUniqueName() == name:
				return elem
		return None

	@Usable.Clickable('special', 'innerLayout', 'children')
	def Analyze(self):
		self.results = Results(self)
		for sim in self.simulations:
			self.results.addResults(self.simManager.GetSimulationResult(sim, self.memoize))

		for analyzer in self.analyzers:
			self.results.addResults(analyzer.Analyze(self.results))

		return self._getInnerLayout()

	def _getStateLayout(self):
		# State Layout
		simElems = [sim.GetLayout() for sim in self.simulations if isinstance(sim, DashInterfacable)]
		raElems = [ra.GetLayout() for ra in self.analyzers if isinstance(ra, DashInterfacable)]
		simLo = DashVerticalLayout().GetLayout(simElems, style={'vertical-align' :'top'})
		raLo = DashVerticalLayout().GetLayout(raElems)
		stateLayout = DashHorizontalLayout(lambda ind, tot:25 if ind==0 else 75, id=self._getElemId('layout', 'state')).GetLayout([simLo, raLo])
		return stateLayout

	def _getInnerLayout(self):
		# Menu Layout
		menuLayout = DashHorizontalLayout().GetLayout([self.stateSaver.GetLayout(), self.stateLoader.GetLayout()])
		stateLayout = self._getStateLayout()
		return DashVerticalLayout().GetLayout([stateLayout, menuLayout])

	def _generateUpdateStateCallback(self):
		def updateState(value):
			return self._getStateLayout().children
		return updateState
	
	def _buildInnerLayoutSignals(self, app):
		# Build menu signals
		self.stateSaver.BuildAllSignals(app)
		self.stateLoader.BuildAllSignals(app)
		app.callback(Output(self.stateLoader._getElemId('params', 'name'), 'options'), 
			[Input(self.stateSaver._fullDivId, 'children')])(self.stateLoader._generateOptionsCallback())
		app.callback(Output(self._getElemId('layout', 'state'), 'children'), 
			[Input(self.stateLoader._fullDivId, 'children')])(self._generateUpdateStateCallback())
		# Build state signals
		for sim in self.simulations:
			if isinstance(sim, DashInterfacable):
				sim.BuildAllSignals(app)
		for ra in self.analyzers:
			if isinstance(ra, DashInterfacable):
				ra.BuildAllSignals(app)
			# First try to add automatic updates
			for raCls in ra.DefaultUpdateOnModif():
				for src in self.analyzers:
					if isinstance(src, raCls):
						src.AddToUpdateOnModif(ra)

		# Build Result analyzers update signals
		for ra in self.analyzers:
			if isinstance(ra, DashInterfacable):
				for toUpdt in ra._toUpdateOnModif:
					if isinstance(toUpdt, DashInterfacable):
						app.callback(Output(toUpdt._getElemId('special', 'innerLayout'), 'children'), 
							[Input(ra._uselessDivIds['anyParamChange'], 'children')])(toUpdt._getUpdateOnModifCallback(ra))

	def AddSimulation(self, sim):
		self.simulations.append(sim)

	def AddAnalyzer(self, analyzer):
		deps = analyzer.DependsOn()
		for dep in deps:
			if SimulationRunner in dep.mro():
				# If it is not already added
				if not any(isinstance(sim, dep) for sim in self.simulations):
					self.simulations.append(dep())
			elif ResultAnalyzer in dep.mro():
				isThere = False
				for ra in self.analyzers:
					if isinstance(ra, dep):
						isThere = True
						break
				if not isThere:
					self.AddAnalyzer(dep())
			else:
				raise ValueError('Dependencies can only be of classResultAnalyzer or SimulationRunner, received class {}'.format(dep.__name__))
		self.analyzers.append(analyzer)
		analyzer.setAppOwner(self)

	def GetProducers(self, name):
		return [e for e in self.simulations + self.analyzers if name in e.GetOutputs()]

	def GetConsumers(self, name):
		return [e for e in self.simulations + self.analyzers  if name in e.GetInputs()]

	
