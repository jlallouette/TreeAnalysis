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
		})

	@Usable.Clickable('special', 'innerLayout', 'children')
	def Analyze(self):
		res = Results()
		for sim in self.simulations:
			print(self.simManager.GetKeyTuple(sim))
			res += self.simManager.GetSimulationResult(sim)
		self.simManager.SaveSimulations()

		for analyzer in self.analyzers:
			res += analyzer.Analyze(res)

		return self._getInnerLayout()
	
	def _getInnerLayout(self):
		simElems = [sim.GetLayout() for sim in self.simulations if isinstance(sim, DashInterfacable)]
		raElems = [ra.GetLayout() for ra in self.analyzers if isinstance(ra, DashInterfacable)]
		simLo = DashHorizontalLayout().GetLayout(simElems)
		raLo = DashHorizontalLayout().GetLayout(raElems)
		return DashVerticalLayout().GetLayout([simLo, raLo])

	def _buildInnerLayoutSignals(self, app):
		for sim in self.simulations:
			if isinstance(sim, DashInterfacable):
				sim.BuildAllSignals(app)
		for ra in self.analyzers:
			if isinstance(ra, DashInterfacable):
				ra.BuildAllSignals(app)

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
		print(self.simulations, self.analyzers)

	
