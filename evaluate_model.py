import json
import numpy as np
from CI_Model.dqn_agent import DQNAgent
from CI_Model.genetic_algorithm import GeneticAlgorithm
from existing_code.workspace_simulation import WorkspaceSimulation

def run_evaluation(agent, jobs_data, machine_data):
    """
    Runs a single simulation episode with a trained agent in evaluation mode.
    """
    print("\n--- Running Evaluation on Trained Model ---")
    
    agent.epsilon = 0.0 # greedy policy during evaluation

    # The simulation environment is created but not yet reset
    simulation = WorkspaceSimulation(
        jobs_data=jobs_data, 
        machine_data=machine_data, 
        agent=agent,
        silent_mode=False, # We want to see the output during evaluation
        enable_mqtt=False
    )

    try:
        # --- FIX: Call reset() to initialize the episode state ---
        state = simulation.reset()
        
        total_reward = 0
        steps = 0
        max_steps = 10000

        for t in range(max_steps):
            legal_mask = simulation.get_legal_actions_mask()
            action = agent.act(state, legal_mask)

            next_state, reward, done, _ = simulation.step(action)
            state = next_state

            total_reward += reward
            steps = t + 1

            if done:
                print(f"🏁 Evaluation finished after {steps} timesteps.")
                break

        if steps == max_steps:
            print("Evaluation ended because max timesteps were reached.")

        print("\n📊 Evaluation Summary:")
        print(f"   Total timesteps: {steps}")
        print(f"   Total reward: {total_reward:.2f}")
        print(f"   Jobs completed: {len(simulation.completed_jobs)}/{len(simulation.jobs)}")

    except KeyboardInterrupt:
        print("\nEvaluation stopped by user.")


if __name__ == "__main__":
    try:
        with open('scenario_test.json', 'r') as f:
            jobs_data = json.load(f)
    except FileNotFoundError:
        print("Error: `scenario_test.json` not found. Please create it before evaluating.")
        exit()
        
    with open('machines.json', 'r') as f:
        machine_data = json.load(f)

    num_machines = len(machine_data['machines'])
    state_size = (num_machines * 4) + (3 * 3)
    action_size = num_machines + 1
    agent = DQNAgent(state_size, action_size)

    # Load the trained model
    model_path = "./CI_Model/dqn_model_450.weights.h5"
    try:
        print(f"Loading trained model from: {model_path}")
        agent.load(model_path)
    except Exception as e:
        print(f"Error: Could not load the trained model. Make sure training has been run. Details: {e}")
        exit()

    run_evaluation(agent, jobs_data, machine_data)