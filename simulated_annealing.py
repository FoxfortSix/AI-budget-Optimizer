# budget_optimizer/simulated_annealing.py

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
    steps: int = 500,
):
    """
    SA untuk penyesuaian halus (REVISI).
    """

    state = deepcopy(init_state)
    if "tabungan" not in state:
        state["tabungan"] = 0

    best = deepcopy(state)
    trace = []

    def spend(s):
        return sum(s.values())

    # Objective function (minimize error)
    def score(s):
        s_spend = spend(s)
        current_tabungan = s.get("tabungan", 0)

        err = 0

        # 1. Penalty income overflow (Sangat Mahal)
        if s_spend > income:
            err += (s_spend - income) * 100

        # 2. Penalty minimum violations (Mahal)
        for cat, minv in minimums.items():
            val = s.get(cat, 0)
            if val < minv:
                err += (minv - val) * 50

        # 3. Penalty target saving miss
        if target is not None and target > 0:
            err += abs(target - current_tabungan)

        return err

    best_score = score(best)

    for step in range(steps):
        T = T_start * ((T_end / T_start) ** (step / steps))

        # Mutasi
        cat = random.choice(list(state.keys()))
        new_state = deepcopy(state)

        direction = random.choice([-1, 1])
        new_state[cat] += direction * delta

        # Hard constraints check (biar gak buang waktu)
        if new_state[cat] < minimums.get(cat, 0):
            continue
        if new_state[cat] < 0:
            continue

        # Optimization: Jangan biarkan total spend jauh di atas income
        # Biar SA gak 'jalan-jalan' ke area yang gak valid
        if spend(new_state) > income + delta:
            continue

        old_score = score(state)
        new_score = score(new_state)

        # Acceptance probability
        delta_score = new_score - old_score
        if delta_score < 0:
            accept_prob = 1.0
        else:
            accept_prob = math.exp(-delta_score / (T + 1e-9))

        if random.random() < accept_prob:
            state = new_state
            if new_score < best_score:
                best = deepcopy(new_state)
                best_score = new_score

    return {
        "final_state": best,
        "method": "simulated_annealing",
        "status": "success",
        "trace": trace,
    }
