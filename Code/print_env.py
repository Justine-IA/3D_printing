import gym
from gym import spaces
import numpy as np

# You’ll need to import or implement these yourself:
#   - get_cooling_time(pid)
#   - simulate_print_time(pid)
#   - save_heat_stats(piece_ids, nx, ny)
#   - INITIAL_LAYERS (dict mapping pid -> number of layers)

TEMP_MAX = 200.0
ALPHA = 10.0
INITIAL_LAYERS = {
    1: 6,
    2: 6,
    3: 6,
    4: 6,
}

class PrintEnv(gym.Env):
    metadata = {"render.modes": []}

    def __init__(self, piece_ids, nx=20, ny=20):
        super().__init__()
        self.piece_ids = piece_ids
        self.n = len(piece_ids)
        # obs: for each piece, [avg_temp, layers_remaining]
        low = np.zeros((self.n, 2), dtype=np.float32)
        high = np.array([[np.inf, np.inf]] * self.n, dtype=np.float32)
        self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)

        # action: choose one of the pieces
        self.action_space = spaces.Discrete(self.n)

        # caching sim params
        self.nx = nx
        self.ny = ny

    def reset(self):
        # layers_left tracks how many layers remain per pid
        self.layers_left = {pid: INITIAL_LAYERS[pid] for pid in self.piece_ids}
        # initialize all temps to 0
        self.state = np.zeros((self.n, 2), dtype=np.float32)
        return self.state

    def step(self, action):
        pid = self.piece_ids[action]

        # --- simulate printing layer & cooling time ---
        print_time = simulate_print_time(pid)
        idle_time = get_cooling_time(pid)

        # (if desired you can advance your sim clock here by print_time + idle_time)

        # --- simulate heat diffusion & measure avg temp ---
        stats = save_heat_stats(self.piece_ids, self.nx, self.ny)
        avg_temp = stats[pid]["avg_temp"]

        # --- compute reward: minimize time + penalize overheating ---
        penalty = max(0.0, avg_temp - TEMP_MAX)
        reward = -(print_time + ALPHA * penalty)

        # --- update your internal state ---
        self.layers_left[pid] -= 1
        self.state[action, 0] = avg_temp
        self.state[action, 1] = self.layers_left[pid]

        # --- check termination ---
        done = all(remaining <= 0 for remaining in self.layers_left.values())

        return self.state.copy(), reward, done, {}

    def render(self, mode="human"):
        pass
