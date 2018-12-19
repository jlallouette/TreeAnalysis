from Utilities import *
from Simulations import *

# Result analyzer ABC
class ResultAnalyzer(Parameterizable):
	def __init__(self):
		Parameterizable.__init__(self)
		self._toUpdateOnModif = []

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

	# Add a specific result analyzer to update on modification
	def AddToUpdateOnModif(self, ra):
		self._toUpdateOnModif.append(ra)
	
	# Returns the list of ResultAnalyzer types whose modifications require an update of the current one
	def DefaultUpdateOnModif(self):
		return []

	# Returns the update callback, the returned callback can depend on which object was updated
	def _getUpdateOnModifCallback(self, source):
		def updateFunc(val):
			self._update(source)
			return self._getInnerLayout()
		return updateFunc

	# Cascades update to all result analyzers to update
	def _cascadeUpdates(self):
		for ra in self._toUpdateOnModif:
			ra._update(self)

	# Overload this to define the update on modif behavior
	def _update(self, source):
		pass

# TMP TODO Maybe move to another file?
import dendropy
import plotly.graph_objs as go
import dash_core_components as dcc
from TreeUtilities import *
# TODO TMP
import json

class TreeVisualizer(ResultAnalyzer, DashInterfacable):
	def __init__(self):
		ResultAnalyzer.__init__(self)
		DashInterfacable.__init__(self)

		self._setCustomLayout('params', DashHorizontalLayout())

	def GetDefaultParams(self):
		return ParametersDescr({
			'treeId' : (1, int),
			'rateToDisplay': ('birth', str, ['birth', 'death'])
		})

	def Analyze(self, results):
		self.addResultsToSelf(results)
		res = Results()

		res.selectedTree = self.treeId

		return res

	def _getInnerLayout(self):
		if hasattr(self, 'trees') and self.treeId < len(self.trees):
			fig = PlotTreeInNewFig(self.trees[self.treeId], self.rateToDisplay)
		else:
			fig = {}
		graph = dcc.Graph(
			style={'width':'100%'},
			id=self._getElemId('innerLayout', 'treeGraph'), 
			figure=fig)
		#TODO TMP
		return html.Div([graph, html.Div(id='testTmp3')])

	def getTreeGraphCallback(self):
		def PlotTree(treeId):
			if hasattr(self, 'trees') and self.treeId < len(self.trees):
				return PlotTreeInNewFig(self.trees[self.treeId], self.rateToDisplay)
			else:
				return {}
		return PlotTree

	def _buildInnerLayoutSignals(self, app):
		app.callback(
			Output(self._getElemId('innerLayout', 'treeGraph'), 'figure'), 
			[Input(self._uselessDivIds['anyParamChange'], 'children')])(self.getTreeGraphCallback())
			#[Input(self._getElemId('params', 'treeId'), 'value')])(self.getTreeGraphCallback())
		#TODO TMP
		app.callback(
			Output('testTmp3', 'children'),
			[Input(self._getElemId('innerLayout', 'treeGraph'), 'hoverData')])(lambda x:json.dumps(x,indent=2))

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
	
	def DefaultUpdateOnModif(self):
		return [TreeVisualizer]

	def _update(self, source):
		if isinstance(source, TreeVisualizer):
			self.selectedTree = source.treeId

	def _getInnerLayout(self):
		sciShapes = []
		sciHist = []
		if hasattr(self, 'colless_tree_imba'):
			sciHist = [go.Histogram(x=self.colless_tree_imba)]
			if hasattr(self, 'selectedTree'):
				xVal = self.colless_tree_imba[self.selectedTree]
				sciShapes = [dict(x0=xVal, x1=xVal, y0=0, y1=1, yref='paper', type='line', line=dict(color='red',width=2))]
		siShapes = []
		siHist = []
		if hasattr(self, 'sackin_index'):
			siHist = [go.Histogram(x=self.sackin_index)]
			if hasattr(self, 'selectedTree'):
				xVal = self.sackin_index[self.selectedTree]
				siShapes = [dict(x0=xVal, x1=xVal, y0=0, y1=1, yref='paper', type='line', line=dict(color='red',width=2))]
		allHists = [
			dcc.Graph(figure={
				'data':sciHist,
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
					hovermode='closest',
					shapes=sciShapes
				)
			}),
			dcc.Graph(figure={
				'data':siHist,
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
					hovermode='closest',
					shapes=siShapes
				)
			})
		]
		return DashHorizontalLayout().GetLayout(allHists)

