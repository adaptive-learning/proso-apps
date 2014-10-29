import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

import proso.models.simulator
import proso.models.prediction
import proso.models.environment
import proso.models.recommendation
import pylab as plt

model_pfae = proso.models.prediction.PriorCurrentPredictiveModel()
recommendations = []
simulator = proso.models.simulator.MoreImprovingUsersSimulator(range(100), range(100))
evaluator = proso.models.simulator.Evaluator(simulator, 10000)

for prob in [0.8]:
    recommendations.append(proso.models.recommendation.ScoreRecommendation(model_pfae, target_probability=prob))

for recommendation in recommendations:
    environment = proso.models.environment.InMemoryEnvironment()
    evaluator.prepare(environment, model_pfae, recommendation)
    print '--------------------------------------------------------------------------------'
    print '{}'.format(recommendation)
    print '--------------------------------------------------------------------------------'
    evaluator.print_stats(sys.stdout)
    fig = plt.figure()
    fig.suptitle('{}'.format(recommendation))
    evaluator.plot_model_precision(environment, model_pfae, fig.add_subplot(111))
    fig.savefig(type(recommendation).__name__ + '.png', bbox_inches='tight')
