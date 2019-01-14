import dash

from GenericApp import *

class TreeStatsApp(GenericApp):
	def __init__(self):
		GenericApp.__init__(self)
		self.AddSimulation(TreeLoaderSim())
		#self.AddSimulation(TreeStatSimulation())
		self.AddSimulation(TreeStatSimulation())
		self.AddSimulation(TreeStatSimulation())
		#self.AddSimulation(TreeLoaderSim())
		self.AddAnalyzer(TreeVisualizer())
		self.AddAnalyzer(TreeStatAnalyzer())

app = dash.Dash(__name__)

# TODO TMP
#from werkzeug.contrib.profiler import ProfilerMiddleware
#f = open('profiler.log', 'a')
#app.server.wsgi_app = ProfilerMiddleware(app.server.wsgi_app, f, sort_by=['cumtime'], profile_dir='.')
# END TMP

tsa = TreeStatsApp()

app.layout = html.Div(children = [
		tsa.GetLayout()
	])

tsa.BuildAllSignals(app)

app.run_server(debug=True)
