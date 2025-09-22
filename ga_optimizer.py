from ga_manual import GeneticAlgorithm
from workspace_simulation import WorkspaceSimulation

def run_ga_optimization():
    """Runs the entire GA optimization process and returns the best solution."""
    # [t_norm_mid, t_hot_start, t_hot_mid, v_low_mid, v_med_start, v_med_mid, v_med_end, v_high_start, v_high_mid, r_low_mid, r_med_mid, r_crit_mid]
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
        chromosome_len=len(BOUNDS_LOW), # Should be 12
        crossover_rate=0.7,
        mutation_rate=0.2
    )

    best_params, best_fit = ga.run(generations=15)
    return best_params, best_fit