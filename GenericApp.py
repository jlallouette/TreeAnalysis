from ResultAnalyzers import *
from DashUtilities import *

class GenericApp(Parameterizable, Usable, DashInterfacable):
	def __init__(self):
		Parameterizable.__init__(self)
		Usable.__init__(self)
		DashInterfacable.__init__(self)

		self.simulations = []
		self.analyzers = []
		self.simManager = SimulationManager('{}_sims.pkl'.format(self.__class__.__name__))

	def GetDefaultParams(self):
		return ParametersDescr({
			'memoize': (False, bool,)
		})

	@Usable.Clickable('special', 'innerLayout', 'children')
	def Analyze(self):
		res = Results(self)
		for sim in self.simulations:
			#res += self.simManager.GetSimulationResult(sim, self.memoize)
			res.addResults(self.simManager.GetSimulationResult(sim, self.memoize))

		for analyzer in self.analyzers:
			#res += analyzer.Analyze(res)
			res.addResults(analyzer.Analyze(res))

		return self._getInnerLayout()
	
	def _getInnerLayout(self):
		simElems = [sim.GetLayout() for sim in self.simulations if isinstance(sim, DashInterfacable)]
		raElems = [ra.GetLayout() for ra in self.analyzers if isinstance(ra, DashInterfacable)]
		simLo = DashVerticalLayout().GetLayout(simElems, style={'vertical-align' :'top'})
		raLo = DashVerticalLayout().GetLayout(raElems)
		return DashHorizontalLayout(lambda ind, tot:25 if ind==0 else 75).GetLayout([simLo, raLo])

	def _buildInnerLayoutSignals(self, app):
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

	
