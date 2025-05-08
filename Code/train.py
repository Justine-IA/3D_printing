# train.py
import numpy as np
from stable_baselines3 import DQN
from print_env import PrintEnv    # wherever you defined your Gym wrapper

def main():
    # 1) instantiate the env
    env = PrintEnv(piece_ids=[1,2,3,4])

    # 2) create the agent
    model = DQN(
        policy="MlpPolicy",
        env=env,
        verbose=1,
        learning_rate=1e-4,
        buffer_size=50_000,
        learning_starts=1_000,
        batch_size=64,
        gamma=0.99,
        target_update_interval=1_000,
        exploration_fraction=0.1,
        exploration_final_eps=0.02,
    )

    # 3) train
    model.learn(total_timesteps=200_000)

    # 4) save
    model.save("print_agent")

if __name__ == "__main__":
    main()
