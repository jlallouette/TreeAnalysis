import math

import plotly.graph_objs as go

leafWidth = 1
#birthRateColorScale = [[0, 'rgb(0, 0, 255)'],[0.5, 'rgb(127, 127, 127)'],[1, 'rgb(255, 0, 0)']]
birthRateColorScale = [[0, 'rgb(0,0,131)'], [0.125, 'rgb(0,60,170)'],
	[0.375, 'rgb(5,255,255)'], [0.625, 'rgb(255,255,0)'],
	[0.875, 'rgb(250,0,0)'], [1, 'rgb(128,0,0)']
]

class NodePlotter:
	def __init__(self, node, EdgePlotCls, parent = None):
		self.node = node
		self.parent = parent
		if self.parent is None:
			self.time = self.node.edge.length
		else:
			self.time = parent.time + self.node.edge.length

		self.children = [NodePlotter(c, EdgePlotCls, self) for c in node.child_node_iter()]

		if self.node.is_leaf():
			self.width = leafWidth
		else:
			self.width = sum(c.width for c in self.children)
		self.xpos = 0
		self.left = 0
		self.brLeft = 0
		self.brRight = 0
		self.splitWidth = 2

		self.edge = EdgePlotCls(self.node.edge, self, self.parent)

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

	def GetColor(self):
		return 'rgb(0,0,0)'

	def GetSplitColor(self):
		return 'rgb(0,0,0)'

	def GetPlotElem(self):
		nodes = dict(type='scatter',
			x=self.GetAllAttr('time'),
			y=self.GetAllAttr('xpos'),
			mode='markers',
			marker=dict(color=[0 for v in self.GetAllAttr('time')], size=5, 
						colorscale=birthRateColorScale,showscale=True, cauto=False, 
						cmin=self.minRate, cmax=self.maxRate if self.maxRate > self.minRate else 1,
						colorbar = dict(title = 'Birth rate', titleside = 'top')),
			text=['node {}'.format(i) for i,n in enumerate(self.GetAllNodes())],
			hoverinfo='',
			name='allNodes'
		)
		allSplits = []
		for n in self.GetAllNodes():
			allSplits.append(dict(x0=n.time, x1=n.time, y0=n.brLeft, y1=n.brRight, type='line', layer='below', line=dict(color=self.GetSplitColor(),width=self.splitWidth)))

		allEdges = []
		for edge in self.GetAllAttr('edge'):
			allEdges += edge.GetPlotElem(self.minRate, self.maxRate)

		layout = dict(title='Tree Plot', shapes = allSplits + allEdges, xaxis=dict(showgrid=False), yaxis=dict(showgrid=False), hovermode='closest')
		return [nodes], layout

class EdgePlotter:
	def __init__(self, edge, child, parent):
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

	def ComputeAll(self):
		self.x = self.child.xpos
		self.allTimes = []
		self.allRates = []
		if hasattr(self.edge, 'birthRates'):
			for t, rate in self.edge.birthRates:
				self.allTimes.append(t)
				self.allRates.append(rate)
		if len(self.allTimes) == 0:
			self.allTimes.append(self.startTime)
		self.allTimes.append(self.endTime)

		self.minRate = min(self.allRates) if len(self.allRates) > 0 else 0
		self.maxRate = max(self.allRates) if len(self.allRates) > 0 else 0

	def GetColor(self, rate = None, minRate = None, maxRate = None):
		if rate is None or maxRate - minRate == 0:
			return 'rgb(0,0,0)'
		else:
			currVal = (rate-minRate)/(maxRate-minRate)
			for v1, v2 in zip(birthRateColorScale, birthRateColorScale[1:]):
				if v1[0] <= currVal <= v2[0]:
					c1 = [float(v) for v in v1[1][4:-1].split(',')]
					c2 = [float(v) for v in v2[1][4:-1].split(',')]
					relVal = (currVal-v1[0])/(v2[0]-v1[0])
					c3 = [int((v2-v1)*relVal+v1) for v1, v2 in zip(c1, c2)]
					return 'rgb({},{},{})'.format(*c3)
			return birthRateColorScale[-1][1]

	def GetPlotElem(self, minRate, maxRate):
		allSegments = []
		if len(self.allRates) == 0:
			allSegments.append(dict(x0=self.startTime, x1=self.endTime, y0=self.x, y1=self.x, type='line', layer='below', line=dict(color=self.GetColor(),width=self.edgeWidth)))
		else:
			for i, rate in enumerate(self.allRates):
				allSegments.append(dict(x0=self.allTimes[i], x1=self.allTimes[i+1], y0=self.x, y1=self.x, type='line', layer='below', line=dict(color=self.GetColor(rate, minRate, maxRate),width=self.edgeWidth)))
		return allSegments

def PlotTreeInNewFig(tree):
	tp = NodePlotter(tree.seed_node, EdgePlotter)
	tp.ComputeAll()
	nodes, layout = tp.GetPlotElem()
	return dict(data=nodes, layout=layout)


