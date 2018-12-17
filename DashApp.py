import dash

from GenericApp import *

class TreeStatsApp(GenericApp):
	def __init__(self):
		GenericApp.__init__(self)
		self.AddAnalyzer(TreeStatAnalyzer())

app = dash.Dash(__name__)

tsa = TreeStatsApp()
lo = tsa.GetLayout()

app.layout = html.Div(children = [
		lo,
	])

tsa.BuildAllSignals(app)

app.run_server(debug=True)
