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
import numpy as np
import copy
# TODO TMP
import json

RateNames = ['birth', 'death']

class TreeVisualizer(ResultAnalyzer, DashInterfacable):
	def __init__(self):
		ResultAnalyzer.__init__(self)
		DashInterfacable.__init__(self)

		self._setCustomLayout('params', DashHorizontalLayout())
		self.smoothedRate = {name:{} for name in RateNames}

	def GetDefaultParams(self):
		return ParametersDescr({
			'treeId' : (1, int),
			'rateToDisplay': ('birth', str, ['birth', 'death']),
			'filterWidth': (0.1,),
		})

	def Analyze(self, results):
		self.addResultsToSelf(results)
		res = Results()

		if self.treeId < len(self.trees):
			t = self.trees[self.treeId]
			t.calc_node_root_distances()
			t.calc_node_ages(set_node_age_fn = lambda n: t.seed_node.edge.length + n.root_distance)
			self.selectedMaxTime = max(nd.age for nd in t)
		else:
			self.selectedMaxTime = 1

		res.rawRate = {name:[] for name in RateNames}
		for i, t in enumerate(self.trees):
			t.calc_node_root_distances()
			t.calc_node_ages(set_node_age_fn = lambda n: t.seed_node.edge.length + n.root_distance)
			self._fillRawRateData(t.seed_node, res)

		self.addResultsToSelf(res)
		res.selectedTree = self.treeId
		return res

	def _fillRawRateData(self, node, res):
		# TODO Find some way to auto-compute epsilon
		epsilon = 0.00001
		stTotTime = max(nd.age for nd in node.leaf_nodes())
		sigs = Results()
		sigs.time = []
		sigs.rate = []
		sigs.nbLin = []
		res.rawRate['birth'].append(sigs)
		res.rawRate['death'].append(copy.deepcopy(sigs))
		tmpNbLin = 1
		for n in node.ageorder_iter(include_leaves = True):
			if stTotTime - n.age > epsilon:
				if n.is_leaf():
					res.rawRate['death'][-1].time.append(n.age)
					res.rawRate['death'][-1].rate.append(1)
					res.rawRate['death'][-1].nbLin.append(tmpNbLin)
					tmpNbLin -= 1
				else:
					res.rawRate['birth'][-1].time.append(n.age)
					res.rawRate['birth'][-1].rate.append(1)
					res.rawRate['birth'][-1].nbLin.append(tmpNbLin)
					tmpNbLin += 1

	# Integral of kernel should be equal to 1
	def _computeSmoothedRate(self, signal, kernelFunc, maxTime, nbSteps = 100):
		res = Results()
		res.time = np.linspace(0, maxTime, num = nbSteps)
		res.rate = []
		for t in res.time:
			tmp = 0
			for i, t2 in enumerate(signal.time):
				kv = kernelFunc(t2-t)
				tmp += kv * signal.rate[i] / signal.nbLin[i]
			res.rate.append(tmp)
		return res

	def _getInnerLayout(self):
		if hasattr(self, 'trees') and self.treeId < len(self.trees):
			figTree = PlotTreeInNewFig(self.trees[self.treeId], self.rateToDisplay)
			figTree['layout']['xaxis'] = dict(range=(0, self.selectedMaxTime))
			figAvgRate = self._getAvgRateFigure()
		else:
			figTree = {}
			figAvgRate = {}
		graphTree = dcc.Graph(
			style={'width':'100%'},
			id=self._getElemId('innerLayout', 'treeGraph'), 
			figure=figTree)
		graphAvgRate = dcc.Graph(
			style={'width':'100%'},
			id=self._getElemId('innerLayout', 'avgRateGraph'), 
			figure=figAvgRate)
		return html.Div([graphTree, graphAvgRate])
	
	def _getAvgRateFigure(self, selectedClade = None):
		sigma = self.selectedMaxTime * self.filterWidth
		kernel = lambda d: np.exp(-0.5*(d/sigma)**2)/(sigma*(2*np.pi)**0.5)
		for name in RateNames:
			self.smoothedRate[name][self.treeId] = self._computeSmoothedRate(self.rawRate[name][self.treeId], kernel, self.selectedMaxTime)

		allTraces = []
		if selectedClade is not None:
			res = Results()
			res.rawRate = {name:[] for name in RateNames}
			self._fillRawRateData(self.trees[self.treeId].nodes()[selectedClade], res)
			smoothedCladeBirth = self._computeSmoothedRate(res.rawRate['birth'][0], kernel, self.selectedMaxTime)
			smoothedCladeDeath = self._computeSmoothedRate(res.rawRate['death'][0], kernel, self.selectedMaxTime)
			allTraces.append(go.Scatter(x = smoothedCladeBirth.time, y=smoothedCladeBirth.rate, 
				mode='lines', line=dict(color='green', dash='dash'), name='clade birth rate'))
			allTraces.append(go.Scatter(x = smoothedCladeDeath.time, y=smoothedCladeDeath.rate, 
				mode='lines', line=dict(color='red', dash='dash'), name='clade death rate'))

		allTraces.append(go.Scatter(x = self.rawRate['birth'][self.treeId].time, y=[0]*len(self.rawRate['birth'][self.treeId].rate), 
			mode='markers', marker=dict(color='green'), hoverinfo='none', showlegend=False))
		allTraces.append(go.Scatter(x = self.smoothedRate['birth'][self.treeId].time, y=self.smoothedRate['birth'][self.treeId].rate, 
			mode='lines', line=dict(color='green'), name='birth rate'))

		allTraces.append(go.Scatter(x = self.rawRate['death'][self.treeId].time, y=[0]*len(self.rawRate['death'][self.treeId].rate), 
			mode='markers', marker=dict(color='red'), hoverinfo='none', showlegend=False))
		allTraces.append(go.Scatter(x = self.smoothedRate['death'][self.treeId].time, y=self.smoothedRate['death'][self.treeId].rate, 
			mode='lines', line=dict(color='red'), name='death rate'))

		layout = go.Layout(xaxis=dict(range=(0, self.selectedMaxTime)))

		return dict(data=allTraces, layout=layout)

	def _getTreeGraphCallback(self):
		def PlotTree(treeId, clickData):
			ind = None if clickData is None else clickData['points'][0]['pointIndex']
			if hasattr(self, 'trees') and self.treeId < len(self.trees):
				self.selectedMaxTime = max(nd.age for nd in self.trees[self.treeId])
				treeFig = PlotTreeInNewFig(self.trees[self.treeId], self.rateToDisplay, selectCladeInd = ind)
				treeFig['layout']['xaxis'] = dict(range=(0, self.selectedMaxTime))
				return treeFig
			else:
				return {}
		return PlotTree

	def _getCladeSelectionCallback(self):
		def CladeSelect(hoverData, treeFig):
			ind = 0 if hoverData is None else hoverData['points'][0]['pointIndex']
			return self._getAvgRateFigure(ind)
		return CladeSelect

	def _buildInnerLayoutSignals(self, app):
		app.callback(
			Output(self._getElemId('innerLayout', 'treeGraph'), 'figure'), 
			[
				Input(self._uselessDivIds['anyParamChange'], 'children'),
				Input(self._getElemId('innerLayout', 'treeGraph'), 'clickData')
			])(self._getTreeGraphCallback())
		app.callback(
			Output(self._getElemId('innerLayout', 'avgRateGraph'), 'figure'),
			[
				Input(self._getElemId('innerLayout', 'treeGraph'), 'clickData'), 
				Input(self._getElemId('innerLayout', 'treeGraph'), 'figure')
			])(self._getCladeSelectionCallback())

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

