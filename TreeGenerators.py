import math
import random
from dendropy.calculate import probability
import dendropy
from dendropy.simulate import treesim 
import numpy as np
from Utilities import *
from DashUtilities import *

class TreeGenerator(Parameterizable, DashInterfacable):
	def __init__(self):
		Parameterizable.__init__(self)
		DashInterfacable.__init__(self)

	@abstractmethod
	def generate(self, num_extant_tips):
		pass

class NeutralTreeGenerator(TreeGenerator):
	def GetDefaultParams(self):
		return ParametersDescr({
			'birth_rate' : (1.0,),
			'death_rate' : (0.0,)
		})

	def generate(self, num_extant_tips):
		t = treesim.birth_death_tree(birth_rate=self.birth_rate, death_rate=self.death_rate, num_extant_tips=num_extant_tips, is_retain_extinct_tips = True)
		# Get last nodes generated (a cherry with branch lenghts = 0) and replace a cherry by one single node
		lastleaf=[n for n in t.leaf_nodes() if n.edge_length == 0][0]
		parent=lastleaf.parent_node
		parent.remove_child(lastleaf, suppress_unifurcations=True)
		return t


class NonNeutralTreeGenerator(TreeGenerator):
	def __init__(self):
		TreeGenerator.__init__(self)


	def GetDefaultParams(self):
		return ParametersDescr({
			'rf' : (TraitEvolLinearBrownian(), NonNeutralRateFunction)
		})
		
	def generate(self, num_extant_tips):
		epsilon = 0.00001 / self.rf.getHighestPosisbleRate() / num_extant_tips
		self.rf.updateValues()

		taxon_namespace = dendropy.TaxonNamespace()
		tree = dendropy.Tree(taxon_namespace=taxon_namespace)
		tree.is_rooted = True
		tree.seed_node.edge.length = 0.0
		extant_tips = set([tree.seed_node])
		extinct_tips = set()
		
		total_time = 0

		while len(extant_tips) < num_extant_tips:
			localTime = 0
			noEvent = True
			eventProb = 0
			# Determine the time of the next event
			while noEvent:
				minNextChange = min(self.rf.getNextChange(n, n.edge.length + localTime) for n in extant_tips)
				eventProb = sum(self.rf.getRate(n, n.edge.length + localTime) for n in extant_tips)
				waiting_time = random.expovariate(eventProb)
				localTime += min(waiting_time, minNextChange + epsilon)
				noEvent = waiting_time > minNextChange

			# add waiting time to nodes
			for nd in extant_tips:
				try:
					nd.edge.length += waiting_time
				except TypeError:
					nd.edge.length = waiting_time
			total_time += waiting_time

			# Determine in which branch will the even happen
			event_nodes = [n for n in extant_tips]
			event_rates = [self.rf.getRate(n, n.edge.length) / eventProb for n in event_nodes]
			nd = probability.weighted_choice(event_nodes, event_rates, rng=random)

			# Branch
			extant_tips.remove(nd)
			c1 = nd.new_child()
			c2 = nd.new_child()
			c1.edge.length = 0
			c2.edge.length = 0
			extant_tips.add(c1)
			extant_tips.add(c2)

		# Get last nodes generated (a cherry with branch lenghts = 0) and replace a cherry by one single node
		lastleaf=[n for n in tree.leaf_nodes() if n.edge_length == 0][0]
		parent=lastleaf.parent_node
		parent.remove_child(lastleaf, suppress_unifurcations=True)
		return tree

##################
# Rate Functions #
##################

class NonNeutralRateFunction(Parameterizable, DashInterfacable):
	def __init__(self):
		Parameterizable.__init__(self)
		DashInterfacable.__init__(self)

	@abstractmethod
	def getRate(self, node, time):
		pass

	@abstractmethod
	def getNextChange(self, node, time):
		pass

	@abstractmethod
	def getHighestPosisbleRate(self):
		pass

	# Overload when some parameter dependent values are computed
	def updateValues(self):
		pass

class ExplosiveRadiationRateFunc(NonNeutralRateFunction):
	def GetDefaultParams(self):
		return ParametersDescr({
			'timeDelay' : (0.1,),
			'basalRate' : (1.0,),
			'lowRate' : (0.01,)
		})

	def getRate(self, node, time):
		return self.basalRate if time <= self.timeDelay else self.lowRate
	
	def getNextChange(self, node, time):
		return self.timeDelay - time if time <= self.timeDelay else math.inf

	def getHighestPosisbleRate(self):
		return self.basalRate

class TraitEvolLinearBrownian(NonNeutralRateFunction):
	def GetDefaultParams(self):
		return ParametersDescr({
			'basalRate' : (1.0,),
			'sigma' : (0.8,),
			'lowestRate' : (0.01,)
		})

	def getRate(self, node, time):
		if hasattr(node, 'traitVal'):
			return node.traitVal
		else:
			if node.parent_node is None:
				node.traitVal = self.basalRate
			else:
				node.traitVal = max(self.lowestRate, node.parent_node.traitVal + np.random.normal(0, self.sigma))
			return node.traitVal

	def getNextChange(self, node, time):
		return math.inf

	def getHighestPosisbleRate(self):
		return self.basalRate

class ExtendedExplRadRateFunc(NonNeutralRateFunction):
	def __init__(self):
		NonNeutralRateFunction.__init__(self)
		self.stepTimes = []

	def GetDefaultParams(self):
		return ParametersDescr({
			'endDelay' : (0.1,),
			'nbSteps' : (4, int),
			'basalRate' : (1.0,),
			'lowRate' : (0.01,)
		})

	def getRate(self, node, time):
		ind = 0
		while ind < len(self.stepTimes) and time > self.stepTimes[ind]:
			ind += 1
		return (self.basalRate-self.lowRate)*(len(self.stepTimes) - ind)/(len(self.stepTimes)) + self.lowRate

	def getNextChange(self, node, time):
		ind = 0
		while ind < len(self.stepTimes) and time > self.stepTimes[ind]:
			ind += 1
		return self.stepTimes[ind] - time if ind < len(self.stepTimes) else math.inf

	def getHighestPosisbleRate(self):
		return self.basalRate

	def updateValues(self):
		self.stepTimes = [self.endDelay * ((i+1) / self.nbSteps) for i in range(self.nbSteps)]
		
	

