from calculate_cooling_time import get_cooling_time
from ABB_control import fetch_number_of_layer
import random
import pickle

class QAgent:
    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.2, temp_threshold=400):
        self.q_table = {}  # dictionnary : (state, action) → Q-value
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.temp_threshold = temp_threshold

    def encode_state(self, stats, active_ids):
        state = []
        for pid in active_ids:
            temp = int(stats[pid]["avg_temp"] // 10)
            cool = int(get_cooling_time(pid) // 10)
            try:
                layers = fetch_number_of_layer(
                    f"http://localhost/rw/rapid/symbol/data/RAPID/T_ROB1/MainModule/number_of_layer_piece_{pid}?json=1"
                )
            except:
                layers = 0
            state.append((temp, cool, layers))
        return tuple(state)

    def choose_action(self, state, valid_actions):
        if random.random() < self.epsilon:
            return random.choice(valid_actions)
        q_vals = [self.q_table.get((state, a), 0.0) for a in valid_actions]
        return valid_actions[q_vals.index(max(q_vals))]

    def update(self, state, action, reward, next_state, next_valid_actions):
        max_q_next = max([self.q_table.get((next_state, a), 0.0) for a in next_valid_actions], default=0)
        old_q = self.q_table.get((state, action), 0.0)
        new_q = old_q + self.alpha * (reward + self.gamma * max_q_next - old_q)
        self.q_table[(state, action)] = new_q

    def save(self, path="q_table.pkl"):
        with open(path, "wb") as f:
            pickle.dump(self.q_table, f)

    def load(self, path="q_table.pkl"):
        with open(path, "rb") as f:
            self.q_table = pickle.load(f)

    def decay_epsilon(self, min_epsilon=0.05, decay=0.995):
        self.epsilon = max(min_epsilon, self.epsilon * decay)
