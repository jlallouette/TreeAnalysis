from WROCTesting import *
from SimulationManager import *
from spyre import server

SimManager = SimulationManager()

class WROCTestingApp(server.App):
	title = 'ROC W Testing'
	inputs = [
			dict(
				type = 'dropdown',
				label = 'Non-neutral tree generator',
				options = [
					{"label": "Neutral Tree", "value":"NeutralTreeGenerator(Parameters(birth_rate=1, death_rate=0))", "checked":True},
					{"label":"Explosive Radiation", "value":"NonNeutralTreeGenerator(Parameters(rf = ExplosiveRadiationRateFunc(Parameters(timeDelay=0.1, basalRate=2, lowRate=0.05))))"},
					{"label":"Trait Evolution Linear Brownian", "value":"NonNeutralTreeGenerator(Parameters(rf=TraitEvolLinearBrownian(Parameters(basalRate=1, sigma=0.8, lowestRate=0.01))))"}
				],
				key = 'treeGenerator'),
			dict(
				type='text',
				key='nbTrees',
				label='Number of trees',
				value='10'),
			dict(
				type='text',
				key='treeSize',
				label='Tree size',
				value='20')
			]

	outputs = [
			dict(
				type='plot',
				id='ROCPlot',
				control_id='goButton',
				action_id='computeVals')
			]
	
	controls = [dict(type='button',
					id='goButton',
					label='Compute!')]

	def GetParams(self, params):
		params = Parameters(
			nb_tree = int(params['nbTrees']),
			tree_size = int(params['treeSize']),
			treeGenerator = eval(params['treeGenerator']))
		return params

	def ROCPlot(self, params):
		params = self.GetParams(params)

		neutTreeGen = NeutralTreeGenerator(Parameters(birth_rate=1, death_rate=0))

		allRes = Results()
		allRes.nonneutral = SimManager.GetSimulationResult(WROCTestingSimRunner(params))
		SimManager.SaveSimulations()

		params.SetParam('treeGenerator', neutTreeGen)
		allRes.neutral = SimManager.GetSimulationResult(WROCTestingSimRunner(params))
		SimManager.SaveSimulations()

		rp = WROCPlotter(allRes)
		ax = rp.Plot()
		return ax
		

app = WROCTestingApp()
app.launch()

