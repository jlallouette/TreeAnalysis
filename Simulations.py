from SimulationManager import *
from DashUtilities import *

from TreeGenerators import *

class TreeStatSimulation(SimulationRunner, DashInterfacable):
	def __init__(self):
		SimulationRunner.__init__(self)
		DashInterfacable.__init__(self)

	def GetDefaultParams(self):
		return ParametersDescr({
			'endCondition' : ('num_extant_tips', str, ['num_extant_tips', 'max_time']),
			'nb_tree' : (10, int),
			'max_time' : (20.0, float),
			'num_extant_tips' : (20, int),
			'treeGenerator' : (NeutralTreeGenerator(), TreeGenerator)
		})

	def GetOutputs(self):
		return ['trees']

	def Simulate(self):
		res = Results(self)
		res.trees = []
		for i in range(self.nb_tree):
			t = None
			while t is None or (self.endCondition == 'num_extant_tips' and len(t.leaf_nodes()) < self.num_extant_tips):
				if t is not None:
					print('Rejected tree with {} leaves (need {}).'.format(len(t.leaf_nodes()), self.num_extant_tips))
				#t = self.treeGenerator.generate(tree_size = self.tree_size)
				t = self.treeGenerator.generate(**{self.endCondition:getattr(self, self.endCondition)})
			res.trees.append(t)
		return res

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

