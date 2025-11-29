# budget_optimizer/genai/simulated_annealing.py
"""
Stable Simulated Annealing (SA) Optimizer
-----------------------------------------
Fallback setelah greedy.

Tujuan:
- Meningkatkan hasil greedy.
- Mengoreksi kategori yang terlalu besar/kecil.
- Menyesuaikan saving agar mendekati target (jika ada).
"""

import math
import random
from copy import deepcopy


def simulated_annealing(
    init_state: dict,
    income: int,
    minimums: dict,
    target: int = None,
    delta: int = 50000,
    T_start: float = 1.0,
    T_end: float = 0.01,
    steps: int = 300,
):
    """
    SA untuk penyesuaian halus.
    Return dict:
      {
        "final_state": dict,
        "method": "simulated_annealing",
        "status": "...",
        "trace": [...],
      }
    """

    state = deepcopy(init_state)
    best = deepcopy(state)

    trace = []

    # utility
    def spend(s):
        return sum(s.values())

    def saving(s):
        return income - spend(s)

    # objective function (minimize error)
    def score(s):
        s_spend = spend(s)
        s_save = saving(s)

        # penalty income overflow
        if s_spend > income:
            return 1e12 + (s_spend - income) * 10

        # target saving adjustment
        if target is not None and target > 0:
            return abs(s_save - target)

        # fallback objective: minimal movement
        return abs(s_spend - income)

    # Initial score
    best_score = score(best)

    # SA Loop
    for step in range(steps):
        T = T_start * ((T_end / T_start) ** (step / steps))

        # pilih kategori acak
        a = random.choice(list(state.keys()))

        # buat state baru (mutasi)
        new_state = deepcopy(state)

        direction = random.choice([-1, 1])
        new_state[a] += direction * delta

        # enforce minimum
        if new_state[a] < minimums.get(a, 0):
            continue

        # enforce no negative
        if new_state[a] < 0:
            continue

        # enforce tidak melebihi income total
        if spend(new_state) > income:
            continue

        # hitung score
        old_score = score(state)
        new_score = score(new_state)

        # acceptance rule
        accept_prob = math.exp(-(new_score - old_score) / (T + 1e-9))

        if new_score < old_score or random.random() < accept_prob:
            state = new_state

            trace.append(
                {
                    "method": "simulated_annealing",
                    "status": f"step={step}, accepted, score={new_score:.2f}, T={T:.4f}",
                }
            )

            if new_score < best_score:
                best = deepcopy(new_state)
                best_score = new_score
        else:
            trace.append(
                {
                    "method": "simulated_annealing",
                    "status": f"step={step}, rejected, score={old_score:.2f}",
                }
            )

    # Final result
    return {
        "final_state": best,
        "method": "simulated_annealing",
        "status": "success",
        "trace": trace,
    }
