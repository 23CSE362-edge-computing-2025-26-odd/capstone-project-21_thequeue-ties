import json
import numpy as np
from CI_Model.dqn_agent import DQNAgent
from existing_code.workspace_simulation import WorkspaceSimulation

# --- Define controlled breakdown scenarios and expected reassignments --- #
BREAKDOWN_SCENARIOS = [
    {
        "timestep": 5,
        "failed_machine": "A_1",
        "ideal_reassignment": {
            "test_job_1": "A_2"   # Move Job1’s op from A_1 → A_2
        }
    },
    {
        "timestep": 12,
        "failed_machine": "A_2",
        "ideal_reassignment": {
            "test_job_3": "A_1"   # Move Job3’s op from A_2 → A_1
        }
    },
    {
        "timestep": 20,
        "failed_machine": "B_1",
        "ideal_reassignment": {
            # No backup available; correct action is "do nothing" (action=0)
        }
    }
]


def run_evaluation(agent, jobs_data, machine_data):
    """
    Runs simulation with scripted breakdowns and evaluates DQN reassignments
    against ideal outcomes.
    """
    print("\n--- Running Evaluation with Controlled Failures ---")

    agent.epsilon = 0.0  # greedy during evaluation
    simulation = WorkspaceSimulation(
        jobs_data=jobs_data,
        machine_data=machine_data,
        agent=agent,
        silent_mode=False,
        enable_mqtt=False
    )

    state = simulation.reset()
    total_reward, steps = 0, 0
    dqn_decisions = []   # (timestep, job_id, chosen_machine)
    max_steps = 200

    for t in range(max_steps):
        # If breakdown occurs at this timestep
        for scenario in BREAKDOWN_SCENARIOS:
            if t == scenario["timestep"]:
                failed_machine = scenario["failed_machine"]
                print(f"\n💥 Simulated breakdown: {failed_machine} at timestep {t}")
                simulation.simulate_machine_failure(failed_machine)

                # DQN decides how to respond
                legal_mask = simulation.get_legal_actions_mask()
                action = agent.act(state, legal_mask)

                next_state, reward, done, _ = simulation.step(action)

                # Decode chosen action
                if action == 0:
                    chosen_machine = "NONE"  # do nothing
                    job_id = None
                else:
                    machine_idx = action - 1
                    chosen_machine = simulation.machines[machine_idx].machine_id
                    # Pick the highest priority job in queue compatible with this machine
                    job_id = None
                    for job in simulation.job_queue:
                        if job.machine_requirement[job.current_operation] == chosen_machine:
                            job_id = job.job_id
                            break

                dqn_decisions.append((t, job_id, chosen_machine))

                state = next_state
                total_reward += reward
                steps += 1

                if done:
                    break

        if done:
            break

        # Normal step
        legal_mask = simulation.get_legal_actions_mask()
        action = agent.act(state, legal_mask)
        next_state, reward, done, _ = simulation.step(action)
        state = next_state
        total_reward += reward
        steps += 1

        if done:
            break

    # --- Evaluation Metrics --- #
    correct, total = 0, 0
    for timestep, job_id, chosen_machine in dqn_decisions:
        scenario = next((s for s in BREAKDOWN_SCENARIOS if s["timestep"] == timestep), None)
        if not scenario:
            continue

        if scenario["ideal_reassignment"]:
            if job_id in scenario["ideal_reassignment"]:
                ideal_machine = scenario["ideal_reassignment"][job_id]
                if chosen_machine == ideal_machine:
                    correct += 1
                total += 1
        else:
            # Ideal is "do nothing"
            if chosen_machine == "NONE":
                correct += 1
            total += 1

    accuracy = (correct / total * 100) if total > 0 else 0

    print("\n📊 Evaluation Summary:")
    print(f"    Total timesteps: {steps}")
    print(f"    Total reward: {total_reward:.2f}")
    print(f"    Jobs completed: {len(simulation.completed_jobs)}/{len(simulation.jobs)}")
    print(f"    Breakdown scenarios tested: {len(BREAKDOWN_SCENARIOS)}")
    print(f"    DQN decisions checked: {total}")
    print(f"    ✅ Accuracy vs Ideal Reassignment: {accuracy:.2f}%")


if __name__ == "__main__":
    try:
        with open("scenario_test.json", "r") as f:
            jobs_data = json.load(f)
    except FileNotFoundError:
        print("Error: scenario_test.json not found.")
        exit()

    with open("machines.json", "r") as f:
        machine_data = json.load(f)

    num_machines = len(machine_data["machines"])
    state_size = (num_machines * 4) + (3 * 3) 
    action_size = num_machines + 1
    agent = DQNAgent(state_size, action_size)

    model_path = "./CI_Model/dqn_model_500.weights.h5"
    print(f"Loading trained model from: {model_path}")
    agent.load(model_path)

    run_evaluation(agent, jobs_data, machine_data)
