import math

import plotly.graph_objs as go

import sys
sys.setrecursionlimit(10000)

leafWidth = 1
birthRateColorScale = [[0, 'rgb(0,0,131)'], [0.125, 'rgb(0,60,170)'],
	[0.375, 'rgb(5,255,255)'], [0.625, 'rgb(255,255,0)'],
	[0.875, 'rgb(250,0,0)'], [1, 'rgb(128,0,0)']
]

class NodePlotter:
	def __init__(self, node, EdgePlotCls, parent = None, rateToDisplay = 'birth'):
		self.node = node
		self.parent = parent
		if self.parent is None:
			self.time = self.node.edge.length if self.node.edge.length is not None else 0
		else:
			self.time = parent.time + self.node.edge.length

		self.children = [NodePlotter(c, EdgePlotCls, self, rateToDisplay=rateToDisplay) for c in node.child_node_iter()]

		if self.node.is_leaf():
			self.width = leafWidth
		else:
			self.width = sum(c.width for c in self.children)
		self.xpos = 0
		self.left = 0
		self.brLeft = 0
		self.brRight = 0

		self.edge = EdgePlotCls(self.node.edge, self, self.parent, rateToDisplay = rateToDisplay)
		self.rateToDisplay = rateToDisplay

	def ComputeAll(self):
		# Positions
		self.ComputePos()
		# Edges
		self.minRate, self.maxRate = math.inf, -math.inf
		for edge in self.GetAllAttr('edge'):
			edge.ComputeAll()
			self.minRate = min(self.minRate, edge.minRate)
			self.maxRate = max(self.maxRate, edge.maxRate)
		# Colors
		self.color = self.GetColor()

	def ComputePos(self, left = 0):
		self.left = left
		if len(self.children) > 0:
			for c in self.children:
				c.ComputePos(left)
				left += c.width
			self.brLeft = self.children[0].xpos
			self.brRight = self.children[-1].xpos
			self.xpos = sum(c.xpos for c in self.children) / len(self.children)
		else:
			self.xpos = self.left + self.width / 2

	def GetAllAttr(self, name):
		res = [getattr(self, name) if hasattr(self, name) else None]
		for c in self.children:
			res += c.GetAllAttr(name)
		return res

	def GetAllNodes(self):
		res = [self]
		for c in self.children:
			res += c.GetAllNodes()
		return res
	
	def GetNodeFromInd(self, ind):
		for nd in self.GetAllNodes():
			if nd.node.cladeInd == ind:
				return nd
		return None

	def GetColor(self):
		return 'rgb(0,0,0)'

	def _getCladeBoxLineColor(self):
		return 'rgb(128, 128, 128)'

	def _getCladeBoxFillColor(self):
		return 'rgb(240, 240, 240)'

	def IsInClade(self, cladeInd):
		tmp = self
		isInClade = False
		while not isInClade and tmp is not None:
			isInClade = (tmp.node.cladeInd == cladeInd)
			tmp = tmp.parent
		return isInClade

	def GetPlotElem(self, selectCladeInd = None):
		allX = self.GetAllAttr('time')
		allY = self.GetAllAttr('xpos')
		nodes = dict(type='scatter',
			x=allX,
			y=allY,
			mode='markers',
			marker=dict(color=[0 for v in self.GetAllAttr('time')], size=5, 
						colorscale=birthRateColorScale,showscale=True, cauto=False, 
						cmin=self.minRate, cmax=self.maxRate if self.maxRate > self.minRate else 1,
						colorbar = dict(title = self.rateToDisplay + ' rate', titleside = 'top')),
			text=['node {}'.format(i) for i,n in enumerate(self.GetAllNodes())],
			hoverinfo='',
			name='allNodes'
		)

		# Clade selection rectangle
		cladeRects = []
		if selectCladeInd is not None:
			cld = self.GetNodeFromInd(selectCladeInd)
			tStart = cld.time-cld.edge.length / 2
			tEnd = max(allX)
			cladeRects.append(dict(
				type='rect', x0=tStart, y0=cld.left, x1=tEnd, y1=cld.left+cld.width, 
				line=dict(color=self._getCladeBoxLineColor(), width=2), 
				fillcolor=self._getCladeBoxFillColor(),
				layer='below')
			)

		allEdges = []
		for edge in self.GetAllAttr('edge'):
			allEdges += edge.GetPlotElem(self.minRate, self.maxRate, selectCladeInd)

		layout = dict(shapes = cladeRects + allEdges, xaxis=dict(showgrid=False, title=dict(text='Time'), range = (0, max(allX)*1.01), ticklen=5, tickwidth=1), yaxis=dict(showgrid=False, showticklabels=False, range=(0, max(allY)+leafWidth/2), autorange=False), hovermode='closest')
		return [nodes], layout

class EdgePlotter:
	def __init__(self, edge, child, parent, rateToDisplay):
		self.edge = edge
		self.child = child
		self.parent = parent
		self.length = self.edge.length
		if self.parent is not None:
			self.startTime = self.parent.time
		else:
			self.startTime = 0
		self.endTime = self.child.time
		self.edgeWidth = 2
		self.rateToDisplay = rateToDisplay

	def ComputeAll(self):
		self.x = self.child.xpos
		self.allTimes = []
		self.allRates = []
		if hasattr(self.edge, self.rateToDisplay + 'Rates'):
			for t, rate in eval('self.edge.' + self.rateToDisplay + 'Rates'):
				self.allTimes.append(t)
				self.allRates.append(rate)
		if len(self.allTimes) == 0:
			self.allTimes.append(self.startTime)
		self.allTimes.append(self.endTime)

		self.minRate = min(self.allRates) if len(self.allRates) > 0 else 0
		self.maxRate = max(self.allRates) if len(self.allRates) > 0 else 0

	def GetColor(self, rate = None, minRate = None, maxRate = None, inClade = True):
		if rate is None or maxRate - minRate == 0:
			return 'rgb(0,0,0)' if inClade else 'rgb(128,128,128)'
		else:
			currVal = (rate-minRate)/(maxRate-minRate)
			for v1, v2 in zip(birthRateColorScale, birthRateColorScale[1:]):
				if v1[0] <= currVal <= v2[0]:
					c1 = [float(v) for v in v1[1][4:-1].split(',')]
					c2 = [float(v) for v in v2[1][4:-1].split(',')]
					relVal = (currVal-v1[0])/(v2[0]-v1[0])
					c3 = [int((v2-v1)*relVal+v1) for v1, v2 in zip(c1, c2)]
					if inClade:
						return 'rgb({},{},{})'.format(*c3)
					else:
						return 'rgb({0},{0},{0})'.format(sum(coeff*v for coeff, v in zip([0.2989, 0.5870, 0.1140], c3)))
			return birthRateColorScale[-1][1]

	def GetPlotElem(self, minRate, maxRate, selectCladeInd = None):
		if self.parent is not None:
			inClade = self.parent.IsInClade(selectCladeInd) if selectCladeInd is not None else True
		else:
			inClade = True if selectCladeInd is None or selectCladeInd == 0 else False
		allSegments = []
		if len(self.allRates) == 0:
			if self.parent is not None:
				allSegments.append(dict(x0=self.allTimes[0], x1=self.allTimes[0], y0=self.x, y1=self.parent.xpos, type='line', layer='below', line=dict(color=self.GetColor(inClade=inClade),width=self.edgeWidth)))
			allSegments.append(dict(x0=self.startTime, x1=self.endTime, y0=self.x, y1=self.x, type='line', layer='below', line=dict(color=self.GetColor(inClade = inClade),width=self.edgeWidth)))
		else:
			if self.parent is not None:
				allSegments.append(dict(x0=self.allTimes[0], x1=self.allTimes[0], y0=self.x, y1=self.parent.xpos, type='line', layer='below', line=dict(color=self.GetColor(self.allRates[0], minRate, maxRate, inClade),width=self.edgeWidth)))
			for i, rate in enumerate(self.allRates):
				allSegments.append(dict(x0=self.allTimes[i], x1=self.allTimes[i+1], y0=self.x, y1=self.x, type='line', layer='below', line=dict(color=self.GetColor(rate, minRate, maxRate, inClade),width=self.edgeWidth)))
		return allSegments

def PlotTreeInNewFig(tree, rateToDisplay = 'birth', selectCladeInd = None):
	for i, nd in enumerate(tree):
		nd.cladeInd = i
	tp = NodePlotter(tree.seed_node, EdgePlotter, rateToDisplay=rateToDisplay)
	tp.ComputeAll()
	nodes, layout = tp.GetPlotElem(selectCladeInd = selectCladeInd)
	return dict(data=nodes, layout=layout)


