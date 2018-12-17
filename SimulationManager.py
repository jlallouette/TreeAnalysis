import pickle
import os
from Utilities import *

# TODO Remove?
#def LoadSimulations(fname):
#	with open(fname, 'rb') as f:
#		return pickle.load(f)

class SimulationManager:
	def __init__(self, fname = 'Simulations.pkl'):
		self.fname = fname
		if os.path.exists(fname):
			with open(fname, 'rb') as f:
				self.simulations = pickle.load(f)
		else:
			self.simulations = {}

	def SaveSimulations(self):
		with open(self.fname, 'wb') as f:
			pickle.dump(self.simulations, f)

	def __del__(self):
		self.SaveSimulations()

	def GetKeyTuple(self, simRunner):
		return (type(simRunner).__name__,) + simRunner.GetParamKeyTuple()

	def GetSimulationResult(self, simRunner):
		kt = self.GetKeyTuple(simRunner)
		if kt not in self.simulations:
			print('Running simulation')
			self.simulations[kt] = simRunner.Simulate()
		return self.simulations[kt]

# Interface for simulation runner classes
class SimulationRunner(Parameterizable, Usable):
	def __init__(self):
		Parameterizable.__init__(self)
		Usable.__init__(self)

	# returns a result object
	@abstractmethod
	def Simulate(self):
		pass

