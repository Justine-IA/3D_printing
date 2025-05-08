from save_heat_stats import save_heat_stats, piece_ids 
import time
TEMP_MAX = 200
WAIT_SEC  = 10

from stable_baselines3 import DQN
model = DQN.load("print_agent")

def choose_next_piece(stats):
    obs = np.array([[stats[pid]["avg_temp"], layers_left[pid]] for pid in piece_ids])
    action, _ = model.predict(obs, deterministic=True)
    return piece_ids[action]

def choose_next_piece(stats):
    return min(stats, key=lambda pid: stats[pid]["avg_temp"])

def choose_safe_piece(stats):
    """
    stats: freshly computed stats,
    save_stats_fn: your save_heat_stats function,
    piece_ids/nx/ny: so we can refresh inside the loop
    """
    while True:
        pid = choose_next_piece(stats)
        t   = stats[pid]["avg_temp"]
        if t < TEMP_MAX:
            return pid
        print(f"[policy] piece {pid} is too hot ({t:.1f}°C), waiting {WAIT_SEC}s")
        time.sleep(WAIT_SEC)
