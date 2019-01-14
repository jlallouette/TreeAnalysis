from multiprocess import Pool

from SimulationManager import *
from DashUtilities import *

from TreeGenerators import *

# Utility function for TreeStatSimulation
def treeGenSimFunc(v):
	endCond, treeGen = v
	rej = 0
	t = None
	while t is None or not endCond.isFinished(t):
		if t is not None:
			rej += 1
		t = treeGen.generate(endCond)
	return (t, rej)

# Generates n trees
class TreeStatSimulation(SimulationRunner, DashInterfacable):
	def __init__(self):
		SimulationRunner.__init__(self)
		DashInterfacable.__init__(self)

	def GetDefaultParams(self):
		return ParametersDescr({
			'endCondition' : (NumExtantStopCrit(), StoppingCriteria),
			'nb_tree' : (10, int),
			'treeGenerator' : (RateFunctionTreeGenerator(), TreeGenerator)
		})

	def GetOutputs(self):
		return ['trees']

	def Simulate(self):
		self.results = Results(self)
		self.results.trees = []
		self.results.rejected = 0
		self.results.total = 0
		with Pool() as pool:
			params = [(self.endCondition, self.treeGenerator)]*self.nb_tree
			for t, rej in pool.imap_unordered(treeGenSimFunc, params):
				self.results.trees.append(t)
				self.results.rejected += rej
				self.results.total += rej + 1
		return self.results

	def _getInnerLayout(self):
		rejected = self.results.GetOwnedAttr('rejected', ind=0, defVal=None, filterFunc=lambda oah: oah.owner == self)
		total = self.results.GetOwnedAttr('total', ind=0, defVal=None, filterFunc=lambda oah: oah.owner == self)
		if total is not None and rejected is not None:
			return html.P('rejected Trees: {}/{}'.format(rejected, total))
		else:
			return ''

from dendropy import Tree
import os
import random
# Loads a tree from a file
class TreeLoaderSim(SimulationRunner, DashInterfacable):
	def __init__(self):
		SimulationRunner.__init__(self)
		DashInterfacable.__init__(self)

	def GetDefaultParams(self):
		return ParametersDescr({
			'path' : ('data/apes.nwk', str),
			'nbLeavesToSample' : (-1, int),
			'nbTreesToSample' : (20, int)
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
		if self.nbLeavesToSample > -1:
			res.trees = self.sampleFromTree(res.trees[0])
		return res

	def sampleFromTree(self, tree):
		trees = []
		allLeaves = tree.leaf_nodes()
		for i in range(self.nbTreesToSample):
			sampledLeaves = random.sample(allLeaves, self.nbLeavesToSample)
			trees.append(tree.extract_tree(node_filter_fn = lambda n: n in sampledLeaves))
		return trees

