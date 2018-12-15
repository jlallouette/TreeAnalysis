from scipy.stats import normaltest
import matplotlib
import matplotlib.pyplot as plt
from TreeGenerators import *
from WComputations import *
from Utilities import *

class WROCTestingSimRunner(SimulationRunner):
	def GetDefaultParams(self):
		return ParametersDescr({
			'nb_tree' : (10, int),
			'tree_size' : (20, int),
			'treeGenerator' : (NeutralTreeGenerator(), TreeGenerator)
		})

	def Simulate(self):
		res = Results()
		res.Wvals = []
		res.stats = {}

		for i in range(self.nb_tree):
			# Generate tree
			t = self.treeGenerator.generate(self.tree_size)
			res.Wvals.append(computeW(t, t.seed_node))

		# Compute stats
		res.stats['WMean'] = np.mean(res.Wvals)
		res.stats['WStd'] = np.std(res.Wvals)
		testVals, res.stats['normTestPval'] = normaltest(res.Wvals)

		return res

class WROCPlotter(ResultPlotter):
	def getROCVals(self, n, nn):
		truePos = []
		falsePos = []
		for pval in np.arange(0, 1.01, 0.01):
			minv, maxv = n[int(pval/2*len(n))], n[-int(pval/2*len(n))-1]
			filtN = list(filter(lambda x: minv <= x <= maxv, n))
			filtNn = list(filter(lambda x: minv <= x <= maxv, nn))
			truePos.append(len(filtN) / len(n))
			falsePos.append(len(filtNn) / len(nn))
		return truePos, falsePos

	def Plot(self):
		fig, ax = plt.subplots(2, 2, figsize=(14,10))

		n = sorted(self.neutral.Wvals)
		nn = sorted(self.nonneutral.Wvals)
		truePos, falsePos = self.getROCVals(n, nn)

		allMin = min(min(n), min(nn))
		allMax = max(max(n), max(nn))

		ax[0][0].hist(n, range=(allMin, allMax), bins=20)
		ax[0][0].set_xlim(allMin, allMax)
		ax[0][0].set_xlabel('W score')
		ax[0][0].set_title('W score of Neutral Trees')

		ax[0][1].hist(nn, range=(allMin, allMax), bins=20)
		ax[0][1].set_xlim(allMin, allMax)
		ax[0][1].set_xlabel('W score')
		ax[0][1].set_title('W score of Non Neutral Trees')

		ax[1][1].plot(falsePos, truePos, 'r')
		ax[1][1].plot([0, 1], [0, 1], '-k')
		ax[1][1].set_ylabel('True positives')
		ax[1][1].set_xlabel('False positives')
		ax[1][1].set_title('ROC curve')

		return ax[0][0]
