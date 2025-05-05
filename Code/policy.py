# policy.py

import numpy as np

# safety threshold (°C)
TEMP_MAX = 200

def choose_next_piece(stats):
    """
    Given stats={pid: {"avg_temp":…, "heatmap_file":…}, …},
    return a pid (int) to print next.
    """
    # naive baseline: pick the coolest piece
    pid, info = min(stats.items(), key=lambda kv: kv[1]["avg_temp"])
    return pid

def choose_safe_piece(stats, model=None, max_wait=10):
    """
    Loop until we find a piece whose avg_temp < TEMP_MAX.
    If you pass a `model`, you can call model.predict(state) here
    instead of choose_next_piece().
    """
    while True:
        # 1) ask the policy or fallback to the naive chooser
        if model:
            state = build_state_tensor(stats)  # e.g. load heatmaps & scalars
            pid = model.predict(state)
        else:
            pid = choose_next_piece(stats)

        # 2) check safety
        if stats[pid]["avg_temp"] < TEMP_MAX:
            return pid

        # 3) otherwise, wait a bit and re-sample stats
        print(f"Piece {pid} is too hot ({stats[pid]['avg_temp']:.1f}°C), waiting…")
        time.sleep(max_wait)
        stats = recompute_stats()  # you’ll fill this in below
