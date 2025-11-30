# budget_optimizer/astar.py

import heapq
from copy import deepcopy
import itertools


def heuristic(state, income, minimums, target):
    """
    Heuristic utama (REVISI):
      - Penalti jika spending > income
      - Penalti jika kategori < minimum
      - Penalti jika kategori 'tabungan' menjauh dari target
    """

    spending = sum(state.values())
    h = 0

    # 1. Penalti jika total spending melebihi income (Hard constraint)
    if spending > income:
        h += (spending - income) * 10  # Bobot diperbesar agar solver takut overspending

    # 2. Penalti minimum violations
    for cat, minv in minimums.items():
        val = state.get(cat, 0)
        if val < minv:
            h += (minv - val) * 5

    # 3. Penalti target tabungan (REVISI LOGIC)
    # Target dikejar pada KATEGORI 'tabungan', bukan pada sisa uang.
    if target is not None and target > 0:
        actual_saving = state.get("tabungan", 0)
        diff = abs(target - actual_saving)
        h += diff

    return h


def neighbors(state, delta, minimums):
    """
    Menghasilkan tetangga (neighbors) dari state:
    - Naikkan kategori +delta
    - Turunkan kategori -delta (tidak boleh < minimum)
    """
    neigh = []

    for cat in state.keys():
        # Up
        up = deepcopy(state)
        up[cat] += delta
        neigh.append(up)

        # Down
        if state[cat] - delta >= minimums.get(cat, 0):
            down = deepcopy(state)
            down[cat] -= delta
            neigh.append(down)

    return neigh


def astar_search(init_state, income, minimums, target=None, delta=50000, max_iter=1000):
    """
    A* Hybrid — versi ringan.
    """

    start_h = heuristic(init_state, income, minimums, target)

    # Counter unik untuk tie-breaker
    counter = itertools.count()

    # Priority queue: (score, count, state)
    pq = []
    heapq.heappush(pq, (start_h, next(counter), init_state))

    visited = set()
    trace = []
    best = init_state
    best_h = start_h

    # Tambahkan key 'tabungan' ke init_state jika belum ada, biar aman
    if "tabungan" not in init_state:
        init_state["tabungan"] = 0

    for _ in range(max_iter):
        if not pq:
            break

        # Unpack
        h, _, state = heapq.heappop(pq)

        # Simpan trace untuk debugging (opsional, bisa dikurangi biar ringan)
        # trace.append({"method": "astar", "status": f"h={h}"})

        # Update best state
        if h < best_h:
            best = state
            best_h = h

        # Stop condition (heuristic 0 artinya sempurna)
        if h == 0:
            return {
                "final_state": state,
                "method": "astar",
                "status": "success",
                "trace": trace,
            }

        # Avoid revisiting
        key = tuple(sorted(state.items()))
        if key in visited:
            continue
        visited.add(key)

        # Expand neighbors
        for nb in neighbors(state, delta, minimums):
            nh = heuristic(nb, income, minimums, target)
            heapq.heappush(pq, (nh, next(counter), nb))

    # End loop → return best found
    return {
        "final_state": best,
        "method": "astar",
        "status": "partial" if best_h > 0 else "success",
        "trace": trace,
    }
