from ga_optimizer import run_ga_optimization
from workspace_simulation import WorkspaceSimulation

if __name__ == "__main__":
    print("🚀 Stage 1: Evolving the optimal Fuzzy Logic model...")
    optimized_params, best_fitness = run_ga_optimization()
    
    print("\n" + "="*50 + f"\n✅ Optimization Complete!\n   - Best Fitness: {best_fitness}\n   - Evolved Params: {[round(p, 2) for p in optimized_params]}\n" + "="*50 + "\n")

    print("🚀 Stage 2: Running the final simulation with the optimized model...")
    simulation = WorkspaceSimulation(fuzzy_params=optimized_params, run_headless=False)
    simulation.run_simulation(max_timesteps=50)
    print("\n✅ Simulation Finished.")