def run_fetch_loop(path):
    global current_piece

    deposition_points = []

    # ——— 1) Un-pause the printer ———
    set_pause_printing(False)
    print()                 # blank line for clarity

    # ——— 2) Immediately read the piece ID ———
    current_piece = fetch_pieces_being_print()
    seen_pieces.add(current_piece)
    print(f"→ Now printing piece {current_piece}")
    print(f"Piece {current_piece} cooled for {cooling_times[current_piece]:.2f}s")
    cooling_times[current_piece] = 0.0
    print()                 # blank line

    # ——— 3) Start your print timer ———
    start = time.perf_counter()

    try:
        while True:
            # a) Fetch XYZ & weld
            x, y, z = fetch_xyz()
            weld    = fetch_welding()

            # b) Check if the printer switched to another piece mid-layer
            pid = fetch_pieces_being_print()
            if pid != current_piece:
                current_piece = pid
                seen_pieces.add(current_piece)
                print(f"→ Switched to printing piece {current_piece}")
                print(f"Piece {current_piece} cooled for {cooling_times[current_piece]:.2f}s")
                cooling_times[current_piece] = 0.0
                print()     # blank line

            # c) Collect points
            if x is not None and y is not None and weld:
                deposition_points.append((x, y, z))

            # d) Detect layer completion
            if fetch_layer():
                print("Layer finished! Pausing printing...")
                set_pause_printing(True)
                print()   # blank line
                break

            time.sleep(0.001)

        # … your JSON save logic …

        if os.path.exists(path):
                with open(path, "r") as f:
                    try:
                        all_points = json.load(f)
                    except json.JSONDecodeError:
                        all_points = []  # file is empty or broken
        else:
                all_points = []

        # Append new points
        all_points.extend(deposition_points)

        # Save updated points
        with open(path, "w") as f:
            json.dump(all_points, f)

        print(f"Saved {len(deposition_points)} new points. Total points now: {len(all_points)}")

    except KeyboardInterrupt:
        print("Loop stopped by user.")
    finally:
        duration = time.perf_counter() - start

    print(f"Printed piece {current_piece} in {duration:.2f}s")
    print()

    # Accumulate cooling for everyone else
    for pid in seen_pieces:
        if pid != current_piece:
            cooling_times[pid] += duration