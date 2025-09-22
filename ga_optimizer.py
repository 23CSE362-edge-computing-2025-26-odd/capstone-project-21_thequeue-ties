from ga_manual import GeneticAlgorithm
from workspace_simulation import WorkspaceSimulation

def run_ga_optimization():
    BOUNDS_LOW =  [40, 70, 90,  2, 4,  7, 10,  8, 12, 10, 40, 70]
    BOUNDS_HIGH = [70, 90, 120, 6, 8, 10, 14, 12, 18, 40, 60, 95]

    def fitness(params):
        sim = WorkspaceSimulation(fuzzy_params=params, run_headless=True)
        score = sim.run_simulation(max_timesteps=100)
        return score if score is not None else -float("inf")

    ga = GeneticAlgorithm(
        fitness_func=fitness,
        param_bounds_low=BOUNDS_LOW,
        param_bounds_high=BOUNDS_HIGH,
        pop_size=40,
        chromosome_len=len(BOUNDS_LOW),
        crossover_rate=0.7,
        mutation_rate=0.2
    )
    return ga.run(generations=15)