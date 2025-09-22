from ga_optimizer import run_ga_optimization
from workspace_simulation import WorkspaceSimulation

if __name__ == "__main__":
    # Stage 1: Optimize with GA
    print("Stage 1: Running GA optimization...")
    optimized_params, best_fit = run_ga_optimization()

    print("\n" + "="*50)
    print("Optimization Complete!")
    print(f"   - Best Fitness: {best_fit}")
    print(f"   - Evolved Params: {[round(p, 2) for p in optimized_params]}")
    print("="*50 + "\n")

    # Stage 2: Running the optimized fuzzy system
    print("Stage 2: Running demo simulation...")
    sim = WorkspaceSimulation(fuzzy_params=optimized_params, run_headless=False)
    sim.run_simulation(max_timesteps=20)

    print("\n Simulation Finished.")
