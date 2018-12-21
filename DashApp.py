import dash

from GenericApp import *

class TreeStatsApp(GenericApp):
	def __init__(self):
		GenericApp.__init__(self)
		#self.AddSimulation(TreeLoaderSim())
		self.AddAnalyzer(TreeVisualizer())
		self.AddAnalyzer(TreeStatAnalyzer())

app = dash.Dash(__name__)

tsa = TreeStatsApp()

app.layout = html.Div(children = [
		tsa.GetLayout()
	])

tsa.BuildAllSignals(app)

app.run_server(debug=True)
