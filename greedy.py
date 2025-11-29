# budget_optimizer/genai/greedy.py
"""
Greedy Optimizer (Local Search)
------------------------------
Fallback cepat ketika A* gagal atau lambat.

Prinsip:
- Jika spending terlalu besar → kurangi kategori terbesar dulu.
- Jika spending terlalu kecil → naikkan kategori yang paling dekat minimum.
- Jika target saving diberikan → arahkan ke income - spending mendekati target.

"""

from copy import deepcopy


def greedy_optimize(
    init_state, income, minimums, target=None, delta=50000, max_iter=300
):
    """
    Greedy local adjustment:
      - init_state : dict
      - return dict:
            {
                "final_state": dict,
                "method": "greedy",
                "status": "...",
                "trace": [...],
            }
    """

    state = deepcopy(init_state)
    trace = []

    def total_spend(s):
        return sum(s.values())

    def saving(s):
        return income - total_spend(s)

    # Loop terbatas (local improvement)
    for i in range(max_iter):
        spend = total_spend(state)
        save = income - spend

        trace.append(
            {"method": "greedy", "status": f"iter={i}, spend={spend}, saving={save}"}
        )

        improved = False

        # --------------------------------------------------------------
        # CASE 1 — Spending melebihi income → kurangi kategori terbesar
        # --------------------------------------------------------------
        if spend > income:
            biggest = max(state, key=lambda k: state[k])
            new_val = state[biggest] - delta

            # Pastikan tidak turun di bawah minimum
            if new_val >= minimums.get(biggest, 0):
                state[biggest] = new_val
                improved = True

        # --------------------------------------------------------------
        # CASE 2 — Target saving diberikan → dorong agar saving mendekati target
        # --------------------------------------------------------------
        elif target is not None and target > 0:
            current_saving = save

            # Jika saving kurang dari target → kecilkan kategori terbesar
            if current_saving < target:
                biggest = max(state, key=lambda k: state[k])
                new_val = state[biggest] - delta
                if new_val >= minimums.get(biggest, 0):
                    state[biggest] = new_val
                    improved = True

            # Jika saving lebih dari target → naikkan kategori yang paling dekat minimum
            elif current_saving > target:
                smallest = min(state, key=lambda k: state[k] - minimums.get(k, 0))
                state[smallest] += delta
                improved = True

        # --------------------------------------------------------------
        # CASE 3 — Tidak ada target → sesuaikan ke minimal edge case
        # --------------------------------------------------------------
        else:
            # Jika masih ada ruang (income - spend >= delta) → naikkan kategori terendah
            if save >= delta:
                smallest = min(state, key=lambda k: state[k])
                state[smallest] += delta
                improved = True

        if not improved:
            break

    # --------------------------------------------------------------
    # Return
    # --------------------------------------------------------------
    return {
        "final_state": state,
        "method": "greedy",
        "status": "success" if total_spend(state) <= income else "partial",
        "trace": trace,
    }
