import numpy as np
import random
from collections import deque
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Lambda
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.losses import Huber
from tensorflow.keras import backend as K

class DQNAgent:
    def __init__(self, state_size, action_size, target_update_freq=1000):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=10000)

        # Core hyperparameters from expert review
        self.gamma = 0.99
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 1e-4

        self.loss_fn = Huber()
        self.model = self._build_model()
        self.target_model = self._build_model()
        self.update_target_model()

        self.target_update_freq = target_update_freq
        self.train_step_counter = 0

    def _build_model(self):
        """Builds a Dueling DQN model."""
        model = Sequential()
        model.add(Dense(128, input_dim=self.state_size, activation='relu'))
        model.add(Dense(128, activation='relu'))

        # Dueling Architecture: V(s) and A(s,a) streams
        model.add(Dense(self.action_size + 1, activation='linear'))
        
        def dueling_combine(x):
            v = x[:, -1:]  # State value V(s)
            a = x[:, :-1]  # Action advantages A(s,a)
            return v + (a - K.mean(a, axis=1, keepdims=True))
        
        model.add(Lambda(dueling_combine))

        model.compile(loss=self.loss_fn, optimizer=Adam(learning_rate=self.learning_rate))
        return model

    def update_target_model(self):
        self.target_model.set_weights(self.model.get_weights())

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state, legal_actions_mask):
        if np.random.rand() <= self.epsilon:
            legal_indices = np.flatnonzero(legal_actions_mask)
            return np.random.choice(legal_indices) if len(legal_indices) > 0 else 0

        q_values = self.model.predict(state, verbose=0)[0]
        q_values[~legal_actions_mask] = -np.inf
        return np.argmax(q_values)

    def replay(self, batch_size):
        if len(self.memory) < batch_size:
            return

        minibatch = random.sample(self.memory, batch_size)
        states = np.vstack([exp[0] for exp in minibatch])
        next_states = np.vstack([exp[3] for exp in minibatch])

        # Double DQN target calculation
        q_next_online = self.model.predict(next_states, verbose=0)
        best_next_actions = np.argmax(q_next_online, axis=1)
        q_next_target = self.target_model.predict(next_states, verbose=0)

        targets = self.model.predict(states, verbose=0)

        for i, (state, action, reward, next_state, done) in enumerate(minibatch):
            if done:
                targets[i, action] = reward
            else:
                targets[i, action] = reward + self.gamma * q_next_target[i, best_next_actions[i]]

        self._train_step(states, targets)

        self.train_step_counter += 1
        if self.train_step_counter % self.target_update_freq == 0:
            self.update_target_model()

    @tf.function
    def _train_step(self, states, targets):
        with tf.GradientTape() as tape:
            q_values = self.model(states, training=True)
            loss = self.loss_fn(targets, q_values)
        
        grads = tape.gradient(loss, self.model.trainable_variables)
        grads, _ = tf.clip_by_global_norm(grads, 5.0) # Gradient clipping
        self.model.optimizer.apply_gradients(zip(grads, self.model.trainable_variables))

    def end_episode(self):
        """Call this after each episode for epsilon decay."""
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def load(self, name):
        self.model.load_weights(name)
        self.update_target_model()

    def save(self, name):
        self.model.save_weights(name)