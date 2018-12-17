from Utilities import *
from Simulations import *

# Result analyzer ABC
class ResultAnalyzer(Parameterizable):
	def __init__(self):
		Parameterizable.__init__(self)

	# Returns a new result object containing newly computed values
	@abstractmethod
	def Analyze(self, results):
		pass

	# Returns a list of class dependencies, other results analyzers or simulation runners
	def DependsOn(self):
		return []

	# Convenience function to access results as if they were members of the analyzer
	def addResultsToSelf(self, results):
		for name, val in results.__dict__.items():
			setattr(self, name, val)

# TMP TODO Maybe move to another file?
import dendropy
import plotly.graph_objs as go
import dash_core_components as dcc

class TreeStatAnalyzer(ResultAnalyzer, DashInterfacable):
	def __init__(self):
		ResultAnalyzer.__init__(self)
		DashInterfacable.__init__(self)

		self.colless_tree_imba = []
		self.sackin_index = []

	def DependsOn(self):
		return [TreeStatSimulation]
	
	def Analyze(self, results):
		self.addResultsToSelf(results)

		res = Results()
		res.colless_tree_imba = []
		res.sackin_index = []
		for t in self.trees:
			res.colless_tree_imba.append(dendropy.calculate.treemeasure.colless_tree_imbalance(t))
			res.sackin_index.append(dendropy.calculate.treemeasure.sackin_index(t))

		self.addResultsToSelf(res)
		return res

	def _getInnerLayout(self):
		allHists = [
			dcc.Graph(figure={
				'data':[go.Histogram(x=self.colless_tree_imba)],
				'layout': go.Layout(
					xaxis={
						'title': 'Colless Tree Imbalance',
						'type': 'linear'
					},
					yaxis={
						'title': 'Count',
						'type': 'linear'
					},
					margin={'l': 40, 'b': 30, 't': 10, 'r': 0},
					height=450,
					hovermode='closest'
				)
			}),
			dcc.Graph(figure={
				'data':[go.Histogram(x=self.sackin_index)],
				'layout': go.Layout(
					xaxis={
						'title': 'Sackin Index',
						'type': 'linear'
					},
					yaxis={
						'title': 'Count',
						'type': 'linear'
					},
					margin={'l': 40, 'b': 30, 't': 10, 'r': 0},
					height=450,
					hovermode='closest'
				)
			})
		]
		return DashHorizontalLayout().GetLayout(allHists)

