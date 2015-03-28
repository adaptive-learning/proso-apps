import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

import proso.models.simulator
import proso.models.prediction
import proso.models.environment
import proso.models.item_selection
import pylab as plt

model_pfae = proso.models.prediction.PriorCurrentPredictiveModel()
item_selectors = []
simulator = proso.models.simulator.MoreImprovingUsersSimulator(range(100), range(100))
evaluator = proso.models.simulator.Evaluator(simulator, 10000)

for prob in [0.8]:
    item_selectors.append(proso.models.item_selection.ScoreItemSelection(model_pfae, target_probability=prob, recompute_parent_score=False))

for item_selection in item_selectors:
    environment = proso.models.environment.InMemoryEnvironment()
    evaluator.prepare(environment, model_pfae, item_selection)
    print '--------------------------------------------------------------------------------'
    print '{}'.format(item_selection)
    print '--------------------------------------------------------------------------------'
    evaluator.print_stats(sys.stdout)
    fig = plt.figure()
    fig.suptitle('{}'.format(item_selection))
    evaluator.plot_model_precision(environment, model_pfae, fig.add_subplot(111))
    fig.savefig(type(item_selection).__name__ + '.png', bbox_inches='tight')
