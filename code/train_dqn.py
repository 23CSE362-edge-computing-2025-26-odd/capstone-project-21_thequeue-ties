import numpy as np
import os

def train_dqn(agent, env, num_episodes=500, batch_size=32, save_dir="./CI_Model"):
    """
    Trains the DQN agent on the given environment.

    Args:
        agent: The DQNAgent instance.
        env: The scheduling environment with reset() and step(action).
        num_episodes: Number of episodes to train for.
        batch_size: Minibatch size for replay.
        save_dir: Directory to save models.
    """
    os.makedirs(save_dir, exist_ok=True)

    for e in range(num_episodes):
        state = env.reset()
        state = np.reshape(state, [1, agent.state_size])

        episode_reward = 0
        done = False
        step = 0

        while not done:
            # Get legal actions mask from environment
            legal_actions_mask = env.get_legal_actions_mask()

            # Agent chooses an action
            action = agent.act(state, legal_actions_mask)

            # Environment responds
            next_state, reward, done, _ = env.step(action)
            next_state = np.reshape(next_state, [1, agent.state_size])

            # Store experience
            agent.remember(state, action, reward, next_state, done)

            # Train agent
            if len(agent.memory) > batch_size:
                agent.replay(batch_size)

            state = next_state
            episode_reward += reward
            step += 1

        # Decay epsilon at end of episode
        agent.end_episode()

        # Logging
        print(f"Episode {e+1}/{num_episodes} | Steps: {step} | Reward: {episode_reward:.2f} | Epsilon: {agent.epsilon:.3f}")

        # Save model every 50 episodes
        if (e + 1) % 50 == 0:
            agent.save(os.path.join(save_dir, f"dqn_model_{e+1}.weights.h5"))

    # Save final model
    agent.save(os.path.join(save_dir, "dqn_model_final.weights.h5"))
