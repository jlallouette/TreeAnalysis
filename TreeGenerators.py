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
		#lastleaf=[n for n in t.leaf_nodes() if n.edge_length == 0][0]
		#parent=lastleaf.parent_node
		#parent.remove_child(lastleaf, suppress_unifurcations=True)
		return t


class NonNeutralTreeGenerator(TreeGenerator):
	def __init__(self):
		TreeGenerator.__init__(self)


	def GetDefaultParams(self):
		return ParametersDescr({
			'birth_rf' : (TraitEvolLinearBrownian(), NonNeutralRateFunction),
			'death_rf' : (ConstantRateFunction(), NonNeutralRateFunction)
		})
		
	def generate(self, num_extant_tips):
		epsilon = 0.00001 / (self.birth_rf.getHighestPosisbleRate() + self.death_rf.getHighestPosisbleRate()) / num_extant_tips
		self.birth_rf.updateValues()
		self.death_rf.updateValues()

		taxon_namespace = dendropy.TaxonNamespace()
		tree = dendropy.Tree(taxon_namespace=taxon_namespace)
		tree.is_rooted = True
		tree.seed_node.edge.length = 0.0
		extant_tips = [tree.seed_node]
		extinct_tips = set()
		
		total_time = 0

		# Init Birth rates in edge
		tree.seed_node.edge.birthRates = [(0, self.birth_rf.getRate(tree.seed_node, 0, total_time=0))]
		tree.seed_node.edge.deathRates = [(0, self.death_rf.getRate(tree.seed_node, 0, total_time=0))]

		while len(extant_tips) < num_extant_tips and len(extant_tips) > 0:
			localTime = 0
			noEvent = True
			eventProb = 0
			# Determine the time of the next event
			while noEvent and len(extant_tips) > 0:
				allNextChange = [(self.birth_rf.getNextChange(n, n.edge.length + localTime, total_time=total_time+localTime), True) for n in extant_tips]
				allNextChange += [(self.death_rf.getNextChange(n, n.edge.length + localTime, total_time=total_time+localTime), False) for n in extant_tips]
				sortedNextChange = sorted(enumerate(allNextChange), key=lambda x:x[1][0])
				IndNC, vNC = sortedNextChange[0]
				minNextChange, nextChangeIsBirth = vNC

				allProbs = [(self.birth_rf.getRate(n, n.edge.length + localTime, total_time=total_time+localTime), True) for n in extant_tips]
				allProbs += [(self.death_rf.getRate(n, n.edge.length + localTime, total_time=total_time+localTime), False) for n in extant_tips]
				eventProb = sum(prob for prob, tp in allProbs)

				waiting_time = random.expovariate(eventProb)
				localTime += min(waiting_time, minNextChange + epsilon)
				noEvent = waiting_time > minNextChange
				# Build rate variations in edges
				if noEvent:
					for n, changeIsBirth in [(extant_tips[nc[0] - (len(extant_tips) if not nc[1][1] else 0)], nc[1][1]) for nc in sortedNextChange if nc[1][0] <= minNextChange + epsilon]:
						if changeIsBirth:
							n.edge.birthRates.append((total_time + localTime, self.birth_rf.getRate(n, n.edge.length+localTime, total_time=total_time+localTime)))
						else:
							n.edge.deathRates.append((total_time + localTime, self.death_rf.getRate(n, n.edge.length+localTime, total_time=total_time+localTime)))
					

			# add waiting time to nodes
			for nd in extant_tips:
				try:
					nd.edge.length += localTime
				except TypeError:
					nd.edge.length = localTime
					
			total_time += localTime

			# Determine in which branch will the event happen
			event_nodes = [(n, True) for n in extant_tips] + [(n, False) for n in extant_tips]
			event_rates = [self.birth_rf.getRate(n, n.edge.length, total_time=total_time) / eventProb for n in extant_tips]
			event_rates += [self.death_rf.getRate(n, n.edge.length, total_time=total_time) / eventProb for n in extant_tips]
			nd, isBirth = probability.weighted_choice(event_nodes, event_rates, rng=random)

			if isBirth:
				# Branch
				extant_tips.remove(nd)
				c1 = nd.new_child()
				c2 = nd.new_child()
				c1.edge.length = 0
				c2.edge.length = 0
				c1.edge.birthRates = [(total_time, self.birth_rf.getRate(c1, 0, total_time=total_time))]
				c2.edge.birthRates = [(total_time, self.birth_rf.getRate(c2, 0, total_time=total_time))]
				c1.edge.deathRates = [(total_time, self.death_rf.getRate(c1, 0, total_time=total_time))]
				c2.edge.deathRates = [(total_time, self.death_rf.getRate(c2, 0, total_time=total_time))]
				extant_tips.append(c1)
				extant_tips.append(c2)
			else:
				extant_tips.remove(nd)

		# Get last nodes generated (a cherry with branch lenghts = 0) and replace a cherry by one single node
		#lastleaf=[n for n in tree.leaf_nodes() if n.edge_length == 0][0]
		#parent=lastleaf.parent_node
		#parent.remove_child(lastleaf, suppress_unifurcations=True)
		return tree

##################
# Rate Functions #
##################

class NonNeutralRateFunction(Parameterizable, DashInterfacable):
	def __init__(self):
		Parameterizable.__init__(self)
		DashInterfacable.__init__(self)

	@abstractmethod
	def getRate(self, node, time, **kwargs):
		pass

	@abstractmethod
	def getNextChange(self, node, time, **kwargs):
		pass

	@abstractmethod
	def getHighestPosisbleRate(self):
		pass

	# Overload when some parameter dependent values are computed
	def updateValues(self):
		pass

class ConstantRateFunction(NonNeutralRateFunction):
	def GetDefaultParams(self):
		return ParametersDescr({
			'rate' : (0.0,),
		})

	def getRate(self, node, time, **kwargs):
		return self.rate
	
	def getNextChange(self, node, time, **kwargs):
		return math.inf

	def getHighestPosisbleRate(self):
		return self.rate

class ExplosiveRadiationRateFunc(NonNeutralRateFunction):
	def GetDefaultParams(self):
		return ParametersDescr({
			'timeDelay' : (0.1,),
			'basalRate' : (1.0,),
			'lowRate' : (0.01,)
		})

	def getRate(self, node, time, **kwargs):
		return self.basalRate if time <= self.timeDelay else self.lowRate
	
	def getNextChange(self, node, time, **kwargs):
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

	def getRate(self, node, time, **kwargs):
		if hasattr(node, 'traitVal'):
			return node.traitVal
		else:
			if node.parent_node is None:
				node.traitVal = self.basalRate
			else:
				node.traitVal = max(self.lowestRate, node.parent_node.traitVal + np.random.normal(0, self.sigma))
			return node.traitVal

	def getNextChange(self, node, time, **kwargs):
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

	def getRate(self, node, time, **kwargs):
		ind = 0
		while ind < len(self.stepTimes) and time > self.stepTimes[ind]:
			ind += 1
		return (self.basalRate-self.lowRate)*(len(self.stepTimes) - ind)/(len(self.stepTimes)) + self.lowRate

	def getNextChange(self, node, time, **kwargs):
		ind = 0
		while ind < len(self.stepTimes) and time > self.stepTimes[ind]:
			ind += 1
		return self.stepTimes[ind] - time if ind < len(self.stepTimes) else math.inf

	def getHighestPosisbleRate(self):
		return self.basalRate

	def updateValues(self):
		self.stepTimes = [self.endDelay * ((i+1) / self.nbSteps) for i in range(self.nbSteps)]
		
class PhaseBirthRateFunc(NonNeutralRateFunction):
	def __init__(self):
		NonNeutralRateFunction.__init__(self)
		self.stepVals = []
		self.actualFunc = lambda x:x
	
	def GetDefaultParams(self):
		return ParametersDescr({
			'period' : (10.0,float),
			'nbSteps' : (10, int),
			'maxRate' : (1.0,float),
			'minRate' : (0.01,float),
			'periodFunc' : ('lambda t:(1+math.sin(t*2*math.pi))/2',)
		})

	def updateValues(self):
		self.actualFunc = eval(self.periodFunc)
		self.stepVals = [self.actualFunc(i/self.nbSteps)*(self.maxRate-self.minRate) + self.minRate for i in range(self.nbSteps)]

	def getRate(self, node, time, total_time = 0, **kwargs):
		rateInd = int(total_time*self.nbSteps/self.period) % self.nbSteps
		return self.stepVals[rateInd]

	def getNextChange(self, node, time, total_time = 0, **kwargs):
		return (int(total_time*self.nbSteps/self.period) + 1) * self.period / self.nbSteps - total_time

	def getHighestPosisbleRate(self):
		return self.maxRate
	

