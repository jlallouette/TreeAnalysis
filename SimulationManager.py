import dill as pickle
import os
from Utilities import *
import copy

class SimulationManager:
	def __init__(self, fname = 'Simulations.pkl'):
		self.fname = fname
		if os.path.isfile(fname):
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

	def GetSimulationResult(self, simRunner, useMemoization = False):
		if useMemoization:
			kt = self.GetKeyTuple(simRunner)
			if kt not in self.simulations:
				print('Running simulation')
				self.simulations[kt] = simRunner.Simulate()
				res = self.simulations[kt]
			else:
				res = copy.deepcopy(self.simulations[kt])
				# Re-owns the simulation
				res.ReOwn(simRunner)
			self.SaveSimulations()
			return res
		else:
			return simRunner.Simulate()

# ABC for SimulationRunner and ResultAnalyzer
class InputOutput:
	def GetInputs(self):
		return []
	
	def GetOutputs(self):
		return []

# Interface for simulation runner classes
class SimulationRunner(AppParameterizable, Usable, InputOutput):
	def __init__(self):
		AppParameterizable.__init__(self)
		Usable.__init__(self)
		InputOutput.__init__(self)

	# returns a result object
	@abstractmethod
	def Simulate(self):
		pass

