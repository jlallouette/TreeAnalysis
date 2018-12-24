from Utilities import *
from Simulations import *

# Result analyzer ABC
class ResultAnalyzer(AppParameterizable, InputOutput):
	def __init__(self):
		AppParameterizable.__init__(self)
		InputOutput.__init__(self)
		self._toUpdateOnModif = []
		self.results = Results(self)

	# Returns a new result object containing newly computed values
	@abstractmethod
	def Analyze(self, results):
		pass

	# Returns a list of class dependencies, other results analyzers or simulation runners
	def DependsOn(self):
		return []

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

RateNames = ['birth', 'death']

class TreeVisualizer(ResultAnalyzer, DashInterfacable):
	def __init__(self):
		ResultAnalyzer.__init__(self)
		DashInterfacable.__init__(self)

		self._setCustomLayout('params', DashHorizontalLayout())
		self.smoothedRate = {name:{} for name in RateNames}
		self.maxTimes = {}

	def GetDefaultParams(self):
		dct = {
			'treeId' : (0, int),
			'rateToDisplay': ('birth', str, ['birth', 'death']),
			'filterWidth': (0.05,),
			'source' : self._getInputReferenceParam('trees')
		}
		return ParametersDescr(dct)

	def GetInputs(self):
		return ['trees']

	def Analyze(self, results):
		self.results = Results(self)
		if not results.HasAttr('trees'):
			return self.results

		self.maxTimes = {}
		self.results.addResults(results)
		res = self.results
		for ownedTrees in results.GetOwnedAttr('trees'):
			with ownedTrees:
				trees = ownedTrees.GetValue()
				mtKey = id(ownedTrees.owner)

				ageFunc = lambda t: (lambda n: (t.seed_node.edge.length if t.seed_node.edge.length is not None else 0) + n.root_distance)

				res.rawRate = {name:[] for name in RateNames}
				self.maxTimes[mtKey] = []
				for i, t in enumerate(trees):
					t.calc_node_root_distances()
					t.calc_node_ages(set_node_age_fn = ageFunc(t))
					self.maxTimes[mtKey].append(max(nd.age for nd in t))
					self._fillRawRateData(t.seed_node, res)

		res.selectedTree = self.treeId
		res.selectedSource = self.source
		return res

	def _fillRawRateData(self, node, res):
		# TODO Find some way to auto-compute epsilon
		epsilon = 0.00001
		stTotTime = max(nd.age for nd in node.leaf_nodes())
		sigs = TmpObject()
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
		res = TmpObject()
		res.time = np.linspace(0, maxTime, num = nbSteps)

		# Compute partial kernel integral for border effect correction
		dt = res.time[1]-res.time[0]
		kernInteg = [sum(kernelFunc(t-res.time[0]) for t in res.time)*dt]
		for i, t in enumerate(res.time[1:]):
			kernInteg.append(kernInteg[-1] + dt *(-kernelFunc((nbSteps-1-i)*dt) + kernelFunc(-(i+1)*dt)))

		res.rate = []
		for j, t in enumerate(res.time):
			tmp = 0
			for i, t2 in enumerate(signal.time):
				kv = kernelFunc(t2-t)
				tmp += kv * signal.rate[i] / signal.nbLin[i]
			res.rate.append(tmp / kernInteg[j])
		return res

	def _updateTrees(self):
		ownedTrees = self.results.GetOwnedAttr('trees', lambda oah: oah.owner == self.source.value)
		if len(ownedTrees) > 0:
			self.trees = ownedTrees[0].GetValue()
			mtKey = id(ownedTrees[0].owner)
			if mtKey in self.maxTimes and self.treeId < len(self.trees):
				self.selectedMaxTime = self.maxTimes[mtKey][self.treeId]

			rawRates = self.results.GetOwnedAttr('rawRate', lambda oah: ownedTrees[0] in oah.sources)
			if len(rawRates) > 0:
				self.selectedRawRate = rawRates[0].GetValue()
			else:
				self.selectedRawRate = None
		else:
			self.trees = None
			self.selectedMaxTime = 1
			self.selectedRawRate = None

	def _getInnerLayout(self):
		self._updateTrees()
		if self.trees is not None and self.treeId < len(self.trees):
			figTree = self._getTreeFigure()
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

	def _getTreeFigure(self, cladeInd = None):
		self._updateTrees()
		if self.trees is None:
			return {}
		else:
			treeFig = PlotTreeInNewFig(self.trees[self.treeId], self.rateToDisplay, selectCladeInd = cladeInd)
			treeFig['layout']['margin'] = dict(r=50, b=30, pad=4, l=50, t=50)
			return treeFig
	
	def _getAvgRateFigure(self, selectedClade = None):
		self._updateTrees()
		if self.trees is None or self.selectedRawRate is None:
			return {}
		else:
			sigma = self.selectedMaxTime * self.filterWidth
			kernel = lambda d: np.exp(-0.5*(d/sigma)**2)/(sigma*(2*np.pi)**0.5)
			for name in RateNames:
				self.smoothedRate[name][self.treeId] = self._computeSmoothedRate(self.selectedRawRate[name][self.treeId], kernel, self.selectedMaxTime)

			allTraces = []
			if selectedClade is not None:
				res = TmpObject()
				res.rawRate = {name:[] for name in RateNames}
				self._fillRawRateData(self.trees[self.treeId].nodes()[selectedClade], res)
				smoothedCladeBirth = self._computeSmoothedRate(res.rawRate['birth'][0], kernel, self.selectedMaxTime)
				smoothedCladeDeath = self._computeSmoothedRate(res.rawRate['death'][0], kernel, self.selectedMaxTime)
				allTraces.append(go.Scatter(x = smoothedCladeBirth.time, y=smoothedCladeBirth.rate, 
					mode='lines', line=dict(color='green', dash='dash'), name='clade birth rate'))
				allTraces.append(go.Scatter(x = smoothedCladeDeath.time, y=smoothedCladeDeath.rate, 
					mode='lines', line=dict(color='red', dash='dash'), name='clade death rate'))

			allTraces.append(go.Scatter(x = self.selectedRawRate['birth'][self.treeId].time, y=[0]*len(self.selectedRawRate['birth'][self.treeId].rate), 
				mode='markers', marker=dict(color='green'), hoverinfo='none', showlegend=False))
			allTraces.append(go.Scatter(x = self.smoothedRate['birth'][self.treeId].time, y=self.smoothedRate['birth'][self.treeId].rate, 
				mode='lines', line=dict(color='green'), name='birth rate'))

			allTraces.append(go.Scatter(x = self.selectedRawRate['death'][self.treeId].time, y=[0]*len(self.selectedRawRate['death'][self.treeId].rate), 
				mode='markers', marker=dict(color='red'), hoverinfo='none', showlegend=False))
			allTraces.append(go.Scatter(x = self.smoothedRate['death'][self.treeId].time, y=self.smoothedRate['death'][self.treeId].rate, 
				mode='lines', line=dict(color='red'), name='death rate'))

			layout = go.Layout(xaxis=dict(range=(0, self.selectedMaxTime)), margin=dict(r=50, b=30, pad=4, l=50, t=50), legend=dict(x=0.05,y=0.95))

			return dict(data=allTraces, layout=layout)

	def _getTreeGraphCallback(self):
		def PlotTree(treeId, clickData):
			ind = None if clickData is None else clickData['points'][0]['pointIndex']
			return self._getTreeFigure(ind)
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

		self.selectedTree = None
		self.selectedSource = None

	def DependsOn(self):
		return [TreeStatSimulation]

	def GetInputs(self):
		return ['trees']

	def GetOutputs(self):
		return ['colless_tree_imba', 'sackin_index']
	
	def Analyze(self, results):
		self.results = Results(self)

		self.selectedTree = results.GetOwnedAttr('selectedTree', ind=0, defVal=None)
		self.selectedSource = results.GetOwnedAttr('selectedSource', ind=0, defVal=None)

		for ownedTrees in results.GetOwnedAttr('trees'):
			with ownedTrees:
				trees = ownedTrees.GetValue()
				self.results.colless_tree_imba = []
				self.results.sackin_index = []
				for t in trees:
					self.results.colless_tree_imba.append(dendropy.calculate.treemeasure.colless_tree_imbalance(t))
					self.results.sackin_index.append(dendropy.calculate.treemeasure.sackin_index(t))

		return self.results
	
	def DefaultUpdateOnModif(self):
		return [TreeVisualizer]

	def _update(self, source):
		if isinstance(source, TreeVisualizer):
			self.selectedTree = source.treeId
			self.selectedSource = source.source

	def _getInnerLayout(self):
		opacity = 0.75

		sciShapes = []
		sciHist = []
		for ownedSci in self.results.GetOwnedAttr('colless_tree_imba'):
			with ownedSci:
				sciHist.append(go.Histogram(x=ownedSci.GetValue(), opacity = opacity, name = ownedSci.GetFullSourceName(layersToPeel=1)))
				if self.selectedTree is not None and self.selectedSource.value in ownedSci.GetAllSources():
					xVal = ownedSci.GetValue()[self.selectedTree]
					sciShapes.append(dict(x0=xVal, x1=xVal, y0=0, y1=1, yref='paper', type='line', line=dict(color='red',width=2)))

		siShapes = []
		siHist = []
		for ownedSi in self.results.GetOwnedAttr('sackin_index'):
			with ownedSi:
				siHist.append(go.Histogram(x=ownedSi.GetValue(), opacity = opacity, name = ownedSi.GetFullSourceName(layersToPeel=1)))
				if self.selectedTree is not None and self.selectedSource.value in ownedSi.GetAllSources():
					xVal = ownedSi.GetValue()[self.selectedTree]
					siShapes.append(dict(x0=xVal, x1=xVal, y0=0, y1=1, yref='paper', type='line', line=dict(color='red',width=2)))

		allHists = [
			dcc.Graph(figure=dict(
				data=sciHist, 
				layout=go.Layout(
					xaxis=dict(title='Colless Tree Imbalance'), 
					yaxis=dict(title='Count'), 
					margin=dict(l=40,b=30,t=10,r=0), 
					hovermode='closest', 
					barmode='overlay',
					shapes=sciShapes)
				)
			),
			dcc.Graph(figure=dict(
				data=siHist, 
				layout=go.Layout(
					xaxis=dict(title='Sackin Index'), 
					yaxis=dict(title='Count'), 
					margin=dict(l=40,b=30,t=10,r=0), 
					hovermode='closest', 
					barmode='overlay',
					shapes=siShapes)
				)
			)
		]
		return DashHorizontalLayout().GetLayout(allHists)

