import time

# We only need to remember, for each piece, the timestamp when it last finished.
_last_end_times = {}

def start_print(piece_id):
    """
    Call this exactly once when you begin printing piece_id.
    Returns the idle time (since it last finished) that you should use.
    """
    now = time.perf_counter()
    # Measure how long it’s been since the last end_print
    last_end = _last_end_times.get(piece_id, now)
    idle     = now - last_end
    # Reset the “last end” to now, so future calls use this as their zero point.
    _last_end_times[piece_id] = now
    return idle

def end_print(piece_id):
    """
    Call this once when you finish printing piece_id.
    It updates the “last end” timestamp so the next start_print can measure idle.
    """
    _last_end_times[piece_id] = time.perf_counter()

def get_cooling_time(piece_id, reset: bool = False):
    """
    Return the time elapsed since you last called end_print(piece_id).
    If reset=True, zero it out (i.e. treat “now” as the new last_end).
    """
    now = time.perf_counter()
    last_end = _last_end_times.get(piece_id)
    if last_end is None:
        # never printed this piece yet
        return 0.0
    elapsed = now - last_end
    if reset:
        _last_end_times[piece_id] = now
    return elapsed