from SimulationManager import *
from DashUtilities import *

from TreeGenerators import *

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
		res = Results(self)
		res.trees = []
		for i in range(self.nb_tree):
			t = None
			while t is None or not self.endCondition.isFinished(t):
				# TODO TMP
				if t is not None:
					print('Rejected tree with {} leaves (need {}).'.format(len(t.leaf_nodes()), 'not this'))
				# TMP
				t = self.treeGenerator.generate(self.endCondition)
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

