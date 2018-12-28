from multiprocess import Pool

from SimulationManager import *
from DashUtilities import *

from TreeGenerators import *

def treeGenSimFunc(v):
	endCond, treeGen = v
	rej = 0
	t = None
	while t is None or not endCond.isFinished(t):
		if t is not None:
			rej += 1
		t = treeGen.generate(endCond)
	return (t, rej)

class TreeStatSimulation(SimulationRunner, DashInterfacable):
	def __init__(self):
		SimulationRunner.__init__(self)
		DashInterfacable.__init__(self)

		self.rejected = None
		self.total = None

	def GetDefaultParams(self):
		return ParametersDescr({
			'endCondition' : (NumExtantStopCrit(), StoppingCriteria),
			'nb_tree' : (10, int),
			'treeGenerator' : (RateFunctionTreeGenerator(), TreeGenerator)
		})

	def GetOutputs(self):
		return ['trees']

	def Simulate(self):

		res = Results(self)
		res.trees = []
		self.rejected = 0
		self.total = 0
		with Pool() as pool:
			params = [(self.endCondition, self.treeGenerator)]*self.nb_tree
			for t, rej in pool.imap_unordered(treeGenSimFunc, params):
				res.trees.append(t)
				self.rejected += rej
				self.total += rej + 1

#		for i in range(self.nb_tree):
#			t = None
#			while t is None or not self.endCondition.isFinished(t):
#				if t is not None:
#					self.rejected += 1
#				t = self.treeGenerator.generate(self.endCondition)
#				self.total += 1
#			res.trees.append(t)
		return res

	def _getInnerLayout(self):
		if self.total is not None and self.rejected is not None:
			return html.P('rejected Trees: {}/{}'.format(self.rejected, self.total))
		else:
			return ''

from dendropy import Tree
import os
class TreeLoaderSim(SimulationRunner, DashInterfacable):
	def __init__(self):
		SimulationRunner.__init__(self)
		DashInterfacable.__init__(self)

	def GetDefaultParams(self):
		return ParametersDescr({
			'path' : ('data/apes.nwk', str)
		})

	def GetOutputs(self):
		return ['trees']

	def Simulate(self):
		res = Results(self)
		if os.path.isfile(self.path):
			try:
				with open(self.path, 'r') as f:
					res.trees = [Tree.get(file=f, schema='newick', tree_offset=0)]
			except:
				pass
		return res

