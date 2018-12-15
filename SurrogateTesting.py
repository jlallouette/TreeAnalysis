import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import copy
import random
from scipy.stats import spearmanr, levene
import math

from TreeGenerators import *
from WComputations import *

class W2SurrogateTestingSimRunner(SimulationRunner):
	def GetDefaultParams(self):
		return ParametersDescr({
			'nb_tree' : (10, int),
			'tree_size' : (20, int),
			'nb_clades' : (1, int),
			'cladeThrMin' : (5, int),
			'cladeThrMax' : (9, int),
			'surrogateStrat' : (BernoulliSurrogateStrat(), SurrogateStrat),
			'treeGenerator' : (NeutralTreeGenerator(), TreeGenerator)
		})

	def Simulate(self):
		res = Results()
		res.origW2 = []
		res.surrW2 = []
		res.stats = {}

		for i in range(self.nb_tree):
			# Generate tree
			t = self.treeGenerator.generate(self.tree_size)

			# Sample a clade
			allNodes = [n for i,n in enumerate(t.ageorder_node_iter(include_leaves = True, descending = True)) if self.cladeThrMin <= i <= self.cladeThrMax]
			for c in random.sample(allNodes, self.nb_clades):
				res.origW2.append(computeW2(t, c))
				res.surrW2.append(self.surrogateStrat.generate(t, c))

		# Compute stats
		res.stats['correl'], res.stats['correlPval'] = spearmanr(res.origW2, res.surrW2)
		res.stats['origW2Mean'] = np.mean(res.origW2)
		res.stats['origW2Std'] = np.std(res.origW2)
		res.stats['surrW2Mean'] = np.mean(res.surrW2)
		res.stats['surrW2Std'] = np.std(res.surrW2)
		leveneVal, res.stats['LevenePVal'] = levene(res.origW2, res.surrW2)

		return res

class W2SurrogateTestingPlotter(ResultPlotter):
	def Plot(self):
		fig, ax = plt.subplots(2,2, figsize=(14,10))
		allMin = min(min(self.surrW2), min(self.origW2))
		allMax = max(max(self.surrW2), max(self.origW2))
		lineH = len(self.surrW2) / 20

		ax[0][0].hist(self.surrW2, orientation='horizontal', range=(allMin, allMax), bins=20)
		ax[0][0].plot([0, lineH], [self.stats['surrW2Mean']]*2, 'k', linewidth=2)
		ax[0][0].plot([0, lineH], [self.stats['surrW2Mean'] + self.stats['surrW2Std']]*2, 'r')
		ax[0][0].plot([0, lineH], [self.stats['surrW2Mean'] - self.stats['surrW2Std']]*2, 'r')
		ax[0][0].set_ylim(allMin, allMax)
		ax[0][0].set_title('Surrogate W2 distribution')
		ax[1][1].hist(self.origW2, orientation='vertical', range=(allMin, allMax), bins=20)
		ax[1][1].plot([self.stats['origW2Mean']]*2, [0, lineH], 'k', linewidth=2)
		ax[1][1].plot([self.stats['origW2Mean'] + self.stats['origW2Std']]*2, [0, lineH], 'r')
		ax[1][1].plot([self.stats['origW2Mean'] - self.stats['origW2Std']]*2, [0, lineH], 'r')
		ax[1][1].set_xlim(allMin, allMax)
		ax[1][1].set_title('Original W2 distribution')
		ax[0][1].plot(self.origW2, self.surrW2, 'bo')
		ax[0][1].set_xlim(allMin, allMax)
		ax[0][1].set_ylim(allMin, allMax)
		ax[0][1].set_xlabel('Original W2 value')
		ax[0][1].set_ylabel('Surrogate W2 value')
		ax[0][1].set_title('Spearman rho:' + str(self.stats['correl']) + ', p-val: ' + str(self.stats['correlPval']))

		#txt = '\n'.join(k + ' = ' + str(v) for k, v in self.stats.items())
		#ax[1][0].text(0, 0, txt)

		return ax

class W2SurrogateTestingROCPlotter(ResultPlotter):
	def getROCVals(self, ns, no, nns, nno):
		truePos = []
		falsePos = []
		for pval in np.arange(0, 1.01, 0.01):
			minv, maxv = ns[int(pval/2*len(ns))], ns[-int(pval/2*len(ns))-1]
			filtNo = list(filter(lambda x: minv <= x <= maxv, no))
			truePos.append(len(filtNo) / len(no))

			minv, maxv = nns[int(pval/2*len(nns))], nns[-int(pval/2*len(nns))-1]
			filtNno = list(filter(lambda x: minv <= x <= maxv, nno))
			falsePos.append(len(filtNno) / len(no))
		return truePos, falsePos

	def Plot(self):
		fig, ax = plt.subplots()

		ns = sorted(self.bernneutral.surrW2)
		no = self.bernneutral.origW2
		nns = sorted(self.bernnonNeutral.surrW2)
		nno = self.bernnonNeutral.origW2
		truePos, falsePos = self.getROCVals(ns, no, nns, nno)

		ax.plot(falsePos, truePos, 'r')

		ns = sorted(self.simneutral.surrW2)
		no = self.simneutral.origW2
		nns = sorted(self.simnonNeutral.surrW2)
		nno = self.simnonNeutral.origW2
		truePos, falsePos = self.getROCVals(ns, no, nns, nno)

		ax.plot(falsePos, truePos, 'g')

		ax.plot([0, 1], [0, 1], '-k')

		ax.legend(['Bernoulli surrogate', 'Simulated surrogate'])
		ax.set_ylabel('True positives')
		ax.set_xlabel('False positives')

		return ax

class SurogateStrat(Parameterizable):
	@abstractmethod
	def generate(self, tree, clade):
		pass

class BernoulliSurrogateStrat(SurogateStrat):
	def generate(self, tree, clade):
		W2_num = 0
		W2_den = 0
		for n in tree.ageorder_node_iter(include_leaves = True, descending = True, filter_fn = lambda x: x.age < clade.age):
			W2_num += 1 - n.p_i if random.random() < n.p_i else -n.p_i
			W2_den += n.p_i*(1.0-n.p_i)
		return W2_num / math.sqrt(W2_den) if W2_den > 0 else 0


class SimulatedNeutralSurrogate(SurogateStrat):
	def generate(self, t, clade):
		# Cut tree t at time t_i
		nb_tips = len(t.leaf_nodes())
		nodes = list(t.ageorder_node_iter(include_leaves=True, descending=False))
		t_i = clade.age
		for n in nodes:
			if n.age >= t_i:
				break
			else:
				p = n.parent_node 
				if p.age > t_i:	# Adjust edge
					n.edge_length = n.parent_node.age - t_i
				else: # Remove node
					p.remove_child(n, suppress_unifurcations=False)

		# Neutrally evolve tree from time t_i until it reaches n leaves again
		delta_t = 1#sum(n.edge.length for n in t.leaf_nodes())/len(t.leaf_nodes())

		while len(t.leaf_nodes()) < nb_tips:
			evolved_tip = random.choice(t.leaf_nodes())
			evolved_tip.taxon = ""

			# Branch node
			ch1 = evolved_tip.new_child()
			ch2 = evolved_tip.new_child()

			ch1.edge.length = 0.0
			ch2.edge.length = 0.0

			# Update time for all tips
			for tip in t.leaf_nodes():
				tip.edge.length += delta_t

		t.randomly_assign_taxa()

		t.calc_node_ages()
		return computeW2(t, clade)

