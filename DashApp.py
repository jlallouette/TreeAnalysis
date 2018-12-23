import dash

from GenericApp import *

# TODO TMP
class TestDep(ResultAnalyzer, DashInterfacable):
	def __init__(self):
		ResultAnalyzer.__init__(self)
		DashInterfacable.__init__(self)

	def GetDefaultParams(self):
		dct = {
			'treeId' : (0, int),
			'rateToDisplay': ('birth', str, ['birth', 'death']),
			'filterWidth': (0.05,)
		}
		if hasattr(self, 'appOwner') and self.appOwner is not None:
			allSources = self.appOwner.GetProducers('trees')
			dct['source'] = (ReferenceHolder(allSources[0]), ReferenceHolder, [ReferenceHolder(None)] + [ReferenceHolder(s) for s in allSources])
		else:
			dct['source'] = (ReferenceHolder(None), ReferenceHolder) 
		return ParametersDescr(dct)

	def Analyze(self, results):
		if self.source != ReferenceHolder(None):
			print(self.source.value.nb_tree)
		return Results(self)

	def GetInputs(self):
		return ['trees']
# END TMP

class TreeStatsApp(GenericApp):
	def __init__(self):
		GenericApp.__init__(self)
		#self.AddSimulation(TreeLoaderSim())
		#self.AddAnalyzer(TreeVisualizer())
		#self.AddAnalyzer(TreeStatAnalyzer())
		self.AddSimulation(TreeStatSimulation())
		self.AddSimulation(TreeStatSimulation())
		self.AddAnalyzer(TestDep())

app = dash.Dash(__name__)

tsa = TreeStatsApp()

app.layout = html.Div(children = [
		tsa.GetLayout()
	])

tsa.BuildAllSignals(app)

app.run_server(debug=True)
