# budget_optimizer/genai/astar.py
"""
A* Hybrid Optimizer
-------------------
A lightweight A* variant optimized for numeric budget allocation.

Goal:
    Cari konfigurasi final_state yang:
        - memenuhi minimum
        - <= income
        - mendekati target tabungan jika diberikan
"""

import heapq
from copy import deepcopy
import itertools


def heuristic(state, income, minimums, target):
    """
    Heuristic utama:
      - Penalti jika spending > income
      - Penalti jika kategori < minimum
      - Penalti jarak ke target saving (income - spending)
    """

    spending = sum(state.values())
    h = 0

    # 1. Penalti jika total spending melebihi income
    if spending > income:
        h += (spending - income) * 2

    # 2. Penalti minimum violations
    for cat, minv in minimums.items():
        if state.get(cat, 0) < minv:
            h += (minv - state.get(cat, 0)) * 3

    # 3. Penalti saving difference (jika target diberikan)
    if target is not None and target > 0:
        saving_now = income - spending
        h += abs(target - saving_now)

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


def astar_search(init_state, income, minimums, target=None, delta=50000, max_iter=500):
    """
    A* Hybrid — versi ringan.
    - init_state: dict
    - return: { "final_state": dict, "method": "astar", "status": .., "trace": [...] }
    """

    start_h = heuristic(init_state, income, minimums, target)

    # Counter unik untuk tie-breaker saat nilai h sama
    counter = itertools.count()

    # Priority queue: (score, count, state)
    # count memastikan kita tidak pernah membandingkan dict vs dict
    pq = []
    heapq.heappush(pq, (start_h, next(counter), init_state))

    visited = set()
    trace = []
    best = init_state
    best_h = start_h

    for _ in range(max_iter):
        if not pq:
            break

        # Unpack 3 value: heuristic, count (diabaikan), state
        h, _, state = heapq.heappop(pq)

        # Simpan trace
        trace.append({"method": "astar", "status": f"h={h}"})

        # Update best state
        if h < best_h:
            best = state
            best_h = h

        # Stop condition (heuristic cukup kecil)
        if h == 0 or h < 2:
            return {
                "final_state": state,
                "method": "astar",
                "status": "success",
                "trace": trace,
            }

        # Avoid revisiting
        key = tuple(sorted(state.items()))  # Pakai sorted agar urutan key konsisten
        if key in visited:
            continue
        visited.add(key)

        # Expand neighbors
        for nb in neighbors(state, delta, minimums):
            nh = heuristic(nb, income, minimums, target)
            # Push dengan counter baru
            heapq.heappush(pq, (nh, next(counter), nb))

    # End loop → return best found
    return {
        "final_state": best,
        "method": "astar",
        "status": "partial",
        "trace": trace,
    }
