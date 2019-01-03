from ResultAnalyzers import *
from DashUtilities import *
from GenericAppState import *

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

	
