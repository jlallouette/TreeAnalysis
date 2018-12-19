from SimulationManager import *
from DashUtilities import *

from TreeGenerators import *

class TreeStatSimulation(SimulationRunner, DashInterfacable):
	def __init__(self):
		SimulationRunner.__init__(self)
		DashInterfacable.__init__(self)

	def GetDefaultParams(self):
		return ParametersDescr({
			'nb_tree' : (10, int),
			'tree_size' : (20, int),
			'treeGenerator' : (NeutralTreeGenerator(), TreeGenerator)
		})

	def Simulate(self):
		res = Results()
		res.trees = []
		for i in range(self.nb_tree):
			t = None
			while t is None or len(t.leaf_nodes()) < self.tree_size:
				if t is not None:
					print('Rejected tree with {} leaves (need {}).'.format(len(t.leaf_nodes()), self.tree_size))
				t = self.treeGenerator.generate(self.tree_size)
			res.trees.append(t)
		return res

