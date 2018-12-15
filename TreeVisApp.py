import dash, dash_html_components as html, dash_core_components as dcc
from dash.dependencies import Input, Output
from DashUtilities import *
from TreeGenerators import *

import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import plotly.plotly as py
import plotly.tools as tls
import numpy as np

app = dash.Dash(__name__)

leafWidth = 1
labelXpos = 0.07

class NodePlot:
	def __init__(self, node, parent = None):
		self.node = node
		self.parent = parent
		if parent is None:
			self.time = 0
		else:
			self.time = parent.time + node.edge.length

		self.children = [NodePlot(c, self) for c in node.child_node_iter()]

		if self.node.is_leaf():
			self.width = leafWidth
		else:
			self.width = sum(c.width for c in self.children)
		self.xpos = 0
		self.left = 0
		self.brLeft = 0
		self.brRight = 0
	
	def computePos(self, left = 0):
		self.left = left
		if len(self.children) > 0:
			for c in self.children:
				c.computePos(left)
				left += c.width
			self.brLeft = self.children[0].xpos
			self.brRight = self.children[-1].xpos
			self.xpos = sum(c.xpos for c in self.children) / len(self.children)
		else:
			self.xpos = self.left + self.width / 2

	def plot(self, ax, clade):
		if len(self.children) > 0:
			ax.plot([self.time, self.time], [self.brLeft, self.brRight], 'b')
		ax.plot(self.time, self.xpos, 'ro' if self.node != clade else 'go')
		for c in self.children:
			ax.plot([self.time, c.time], [c.xpos, c.xpos], 'b')
			c.plot(ax, clade)


class TreePlotter(Parameterizable, Usable, DashInterfacable):
	def __init__(self):
		Parameterizable.__init__(self)
		Usable.__init__(self)
		DashInterfacable.__init__(self)

		self.pltFig = None
		self.rateFig = None

		wFunc = lambda ind, tot: (25 if ind == 0 else int(75/(tot-1))) if tot > 1 else 100
		self._setCustomLayout('all', DashHorizontalLayout(wFunc))
		self._setCustomLayout('controls', DashVerticalLayout())

	def GetDefaultParams(self):
		return ParametersDescr({
			'tree_size' : (20, int),
			'treeGenerator' : (NeutralTreeGenerator(), TreeGenerator),
			'maxTime' : (20.0, float)
		})

	@Usable.Clickable
	def Plot(self):
		t = self.treeGenerator.generate(self.tree_size)
		allNodes = t.internal_nodes(exclude_seed_node = True)

		fig, ax = plt.subplots()
		tp = NodePlot(t.seed_node)
		tp.computePos()
		tp.plot(ax, None)

		self.pltFig = tls.mpl_to_plotly(fig)

		if hasattr(self.treeGenerator, 'rf'):
			times = np.arange(0, self.maxTime, self.maxTime / 100)
			rate = [self.treeGenerator.rf.getRate(allNodes[0], tm) for tm in times]
			fig, ax = plt.subplots()
			ax.plot(times, rate)
			self.rateFig = tls.mpl_to_plotly(fig)

	def _getInnerLayout(self):
		figs = []
		if self.rateFig is not None:
			figs.append(dcc.Graph(figure=self.rateFig))
		if self.pltFig is not None:
			figs.append(dcc.Graph(figure=self.pltFig))
		if len(figs) > 0:
			return DashHorizontalLayout().GetLayout(figs)
		else:
			return html.Div(children='lol')

treePlt = TreePlotter()

app.layout = html.Div(children = [
		treePlt.GetLayout()
	])

treePlt.BuildAllSignals(app)

app.run_server(debug=True)


#Dependencied : dataspyre, dendropy

#from spyre import server
#import pandas as pd
#import numpy as np
#import matplotlib
#import matplotlib.pyplot as plt
#
#from dendropy.simulate import treesim 
#
#from SurrogateTesting import *
#from TreeGenerators import *
#
#leafWidth = 1
#labelXpos = 0.07
#
#class NodePlot:
#	def __init__(self, node, parent = None):
#		self.node = node
#		self.parent = parent
#		if parent is None:
#			self.time = 0
#		else:
#			self.time = parent.time + node.edge.length
#
#		self.children = [NodePlot(c, self) for c in node.child_node_iter()]
#
#		if self.node.is_leaf():
#			self.width = leafWidth
#		else:
#			self.width = sum(c.width for c in self.children)
#		self.xpos = 0
#		self.left = 0
#		self.brLeft = 0
#		self.brRight = 0
#	
#	def computePos(self, left = 0):
#		self.left = left
#		if len(self.children) > 0:
#			for c in self.children:
#				c.computePos(left)
#				left += c.width
#			self.brLeft = self.children[0].xpos
#			self.brRight = self.children[-1].xpos
#			self.xpos = sum(c.xpos for c in self.children) / len(self.children)
#		else:
#			self.xpos = self.left + self.width / 2
#
#	def plot(self, ax, clade):
#		if len(self.children) > 0:
#			ax.plot([self.time, self.time], [self.brLeft, self.brRight], 'b')
#		ax.plot(self.time, self.xpos, 'ro' if self.node != clade else 'go')
#		txt = []
#		if hasattr(self.node, 'nbAlive'):
#			txt.append('na='+str(self.node.nbAlive))
#		if hasattr(self.node, 'nbCladeAlive'):
#			txt.append('ncl='+str(self.node.nbCladeAlive))
#		if hasattr(self.node, 'p_i'):
#			txt.append('pi='+str(self.node.p_i))
#		if hasattr(self.node, 'k_i'):
#			txt.append('ki='+str(len(self.node.k_i)))
#		if hasattr(self.node, 'W2_num'):
#			txt.append('numPri='+str((self.node.W2_num)))
#		if hasattr(self.node, 'W2_den'):
#			txt.append('denPri='+str((self.node.W2_den)))
#		if hasattr(self.node, 'W2_numJules'):
#			txt.append('numJul='+str((self.node.W2_numJules)))
#		if hasattr(self.node, 'W2_denJules'):
#			txt.append('denJul='+str((self.node.W2_denJules)))
#		for c in self.children:
#			ax.plot([self.time, c.time], [c.xpos, c.xpos], 'b')
#			c.plot(ax, clade)
#		
#
#class TreeApp(server.App):
#	title = 'Tree App'
#	inputs = [
#		dict(
#			type = 'dropdown',
#			label = 'Tree generator',
#			options = [
#				{"label": "Neutral Tree", "value":"NeutralTreeGenerator(Parameters(birth_rate=1, death_rate=0))", "checked":True},
#				{"label":"Explosive Radiation", "value":"NonNeutralTreeGenerator(Parameters(rf = ExplosiveRadiationRateFunc(Parameters(timeDelay=0.1, basalRate=2, lowRate=0.05))))"},
#				{"label":"Trait Evolution Linear Brownian", "value":"NonNeutralTreeGenerator(Parameters(rf=TraitEvolLinearBrownian(Parameters(basalRate=1, sigma=0.8, lowestRate=0.01))))"}
#			],
#			key = 'treeGenerator'),
#		dict(
#			type='slider',
#			key='treeSize',
#			label='Tree Size',
#			action_id='plot1')
#		]
#
#	outputs = [
#			dict(
#				type='plot',
#				id='TreePlot',
#				control_id='button1')
#			]
#	
#	controls = [dict(type='button',
#					id='button1',
#					label='Go!')]
#
#
#	def TreePlot(self, params):
#		treeGenerator = eval(params['treeGenerator'])
#		t = treeGenerator.generate(params['treeSize'])
#
#		allNodes = t.internal_nodes(exclude_seed_node = True)
#		#c = random.choice(allNodes)
#		#W2 = computeW2(t, c)
#
#		#computeW2(t)
#
#		fig, ax = plt.subplots()
#		tp = NodePlot(t.seed_node)
#		tp.computePos()
#		tp.plot(ax, None)
#
#		return ax
#
#
#
#app = TreeApp()
#app.launch()
#
#
#
#
