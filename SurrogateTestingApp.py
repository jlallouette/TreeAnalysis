from SurrogateTesting import *
from SimulationManager import *
from spyre import server

import cProfile

SimManager = SimulationManager()

class SurrogateTestingApp(server.App):
	title = 'Surrogate testing App'
	inputs = [
			dict(
				type = 'dropdown',
				label = 'Tree generator',
				options = [
					{"label": "Neutral Tree", "value":"NeutralTreeGenerator(Parameters(birth_rate=1, death_rate=0))", "checked":True},
					{"label":"Explosive Radiation", "value":"NonNeutralTreeGenerator(Parameters(rf = ExplosiveRadiationRateFunc(Parameters(timeDelay=0.1, basalRate=2, lowRate=0.05))))"},
					{"label":"Trait Evolution Linear Brownian", "value":"NonNeutralTreeGenerator(Parameters(rf=TraitEvolLinearBrownian(Parameters(basalRate=1, sigma=0.8, lowestRate=0.01))))"}
				],
				key = 'treeGenerator'),
			dict(
				type = 'dropdown',
				label = 'Surrogate strategy',
				options = [
					{"label": "Bernoulli", "value":"BernoulliSurrogateStrat()", "checked":True},
					{"label":"Simulated", "value":"SimulatedNeutralSurrogate()"}],
				key = 'surrogateStrat'),
			dict(
				type='text',
				key='nbTrees',
				label='Number of trees',
				value='10'),
			dict(
				type='text',
				key='treeSize',
				label='Tree size',
				value='20'),
			dict(
				type='text',
				key='nbClades',
				label='Number of clades',
				value='1'),
			dict(
				type='text',
				key='cladeThrMin',
				label='Minimum clade level',
				value='5'),
			dict(
				type='text',
				key='cladeThrMax',
				label='Maximum clade level',
				value='19')
			]

	outputs = [
			dict(
				type='plot',
				id='correlPlot',
				control_id='goButton',
				action_id='computeVals')
			#dict(
			#	type='plot',
			#	id='ROCPlot',
			#	control_id='goButton',
			#	action_id='computeVals')
			]
	
	controls = [dict(type='button',
					id='goButton',
					label='Compute!')]

	def GetParams(self, params):
		params = Parameters(
			nb_tree = int(params['nbTrees']),
			tree_size = int(params['treeSize']),
			nb_clades = int(params['nbClades']),
			cladeThrMin = float(params['cladeThrMin']),
			cladeThrMax = float(params['cladeThrMax']),
			surrogateStrat = eval(params['surrogateStrat']),
			treeGenerator = eval(params['treeGenerator']))
		return params

	def correlPlot(self, params):
		params = self.GetParams(params)

		res = SimManager.GetSimulationResult(W2SurrogateTestingSimRunner(params))
		SimManager.SaveSimulations()

		rp = W2SurrogateTestingPlotter(res)
		ax = rp.Plot()
		return ax[0][1]

	def ROCPlot(self, params):
		nonNeutTreeGen = eval(params['treeGenerator'])

		params = self.GetParams(params)

		neutTreeGen = NeutralTreeGenerator(Parameters(birth_rate=1, death_rate=0))
		#nonNeutTreeGen = NonNeutralTreeGenerator(Parameters(rf=TraitEvolLinearBrownian(Parameters(basalRate=1, sigma=0.8, lowestRate=0.01))))
		bernSurrStrat = BernoulliSurrogateStrat()
		simSurrStrat = SimulatedNeutralSurrogate()

		allRes = Results()
		params.SetParam('surrogateStrat', bernSurrStrat)
		params.SetParam('treeGenerator', neutTreeGen)
		allRes.bernneutral = SimManager.GetSimulationResult(W2SurrogateTestingSimRunner(params))
		SimManager.SaveSimulations()

		params.SetParam('treeGenerator', nonNeutTreeGen)
		allRes.bernnonNeutral = SimManager.GetSimulationResult(W2SurrogateTestingSimRunner(params))
		SimManager.SaveSimulations()

		params.SetParam('surrogateStrat', simSurrStrat)
		params.SetParam('treeGenerator', neutTreeGen)
		allRes.simneutral = SimManager.GetSimulationResult(W2SurrogateTestingSimRunner(params))
		SimManager.SaveSimulations()

		params.SetParam('treeGenerator', nonNeutTreeGen)
		allRes.simnonNeutral = SimManager.GetSimulationResult(W2SurrogateTestingSimRunner(params))
		SimManager.SaveSimulations()

		rp = W2SurrogateTestingROCPlotter(allRes)
		ax = rp.Plot()
		return ax
		

app = SurrogateTestingApp()
app.launch()
