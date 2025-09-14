import json
import os
from CI_Model.dqn_agent import DQNAgent
from existing_code.workspace_simulation import WorkspaceSimulation
from CI_Model.train_dqn import train_dqn

def main():
    # 1. Load Configuration
    with open('machines.json', 'r') as f:
        machine_data = json.load(f)
    with open('scenario_full.json', 'r') as f:
        jobs_data = json.load(f)

    # 2. Initialize Agent and Environment
    num_machines = len(machine_data['machines'])
    state_size = (num_machines * 4) + (3 * 3)
    action_size = num_machines + 1
    agent = DQNAgent(state_size, action_size)

    env = WorkspaceSimulation(
        jobs_data=jobs_data,
        machine_data=machine_data,
        agent=agent,
        silent_mode=True
    )

    # 3. Load pre-trained model if it exists
    model_dir = "./CI_Model"
    final_model_path = os.path.join(model_dir, "dqn_model_final.weights.h5")
    try:
        agent.load(final_model_path)
        print("Loaded pre-trained DQN model.")
    except:
        print("No pre-trained model found. Starting new training session.")

    # 4. Run the high-level training process with interruption handling
    print("\n--- Starting High-Performance DQN Agent Training ---")
    try:
        train_dqn(agent=agent, env=env, num_episodes=5000, batch_size=64, save_dir=model_dir)
    except KeyboardInterrupt:
        print("\n\n--- Training interrupted by user ---")
    finally:
        # This block will run whether the training finishes or is interrupted
        print("\n--- Training Process Ended: Saving final model state ---")
        agent.save(final_model_path)
        print(f"✅ Final model progress saved to: {final_model_path}")

if __name__ == "__main__":
    main()