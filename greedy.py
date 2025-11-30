# budget_optimizer/greedy.py

from copy import deepcopy


def greedy_optimize(
    init_state, income, minimums, target=None, delta=50000, max_iter=300
):
    """
    Greedy local adjustment (REVISI).
    """

    state = deepcopy(init_state)
    trace = []

    if "tabungan" not in state:
        state["tabungan"] = 0

    def total_spend(s):
        return sum(s.values())

    # Main Loop
    for i in range(max_iter):
        spend = total_spend(state)
        current_tabungan = state["tabungan"]

        # Trace dikit aja biar gak berat
        # trace.append({"method": "greedy", "status": f"iter={i}, tab={current_tabungan}"})

        improved = False

        # --------------------------------------------------------------
        # PRIORITY 1: Kebutuhan Dasar (Jika di bawah minimum)
        # --------------------------------------------------------------
        violation_found = False
        for cat, minv in minimums.items():
            if state.get(cat, 0) < minv:
                state[cat] += delta
                improved = True
                violation_found = True
                break  # Fix satu per satu

        if violation_found:
            continue

        # --------------------------------------------------------------
        # PRIORITY 2: Overspending (Jika Total > Income)
        # --------------------------------------------------------------
        if spend > income:
            # Kurangi kategori terbesar selain tabungan (jika mungkin)
            # atau kurangi tabungan jika terpaksa
            candidates = {k: v for k, v in state.items() if v > minimums.get(k, 0)}

            if candidates:
                # Prioritaskan mengurangi selain tabungan dulu jika tabungan belum over target
                # Tapi kalau simpelnya: kurangi yang paling besar
                biggest = max(candidates, key=candidates.get)
                state[biggest] -= delta
                improved = True
            else:
                # Stuck (sudah mentok minimum semua), break to avoid infinite loop
                break

        # --------------------------------------------------------------
        # PRIORITY 3: Target Tabungan (Kejar Target)
        # --------------------------------------------------------------
        elif target is not None and target > 0:
            diff = target - current_tabungan

            # Jika tabungan kurang dari target, dan masih ada sisa income
            if diff > 0:
                # Cek apakah budget masih cukup untuk nambah
                if spend + delta <= income:
                    state["tabungan"] += delta
                    improved = True
                else:
                    # Budget penuh, harus korbankan kategori lain demi tabungan?
                    # Cari kategori non-esensial untuk dikurangi
                    others = {
                        k: v
                        for k, v in state.items()
                        if k != "tabungan" and v > minimums.get(k, 0)
                    }
                    if others:
                        victim = max(others, key=others.get)
                        state[victim] -= delta
                        state["tabungan"] += delta
                        improved = True

            # Jika tabungan kebanyakan (jarang terjadi, tapi just in case)
            elif diff < 0:  # tabungan > target
                if state["tabungan"] - delta >= minimums.get("tabungan", 0):
                    state["tabungan"] -= delta
                    improved = True

        if not improved:
            break

    return {
        "final_state": state,
        "method": "greedy",
        "status": "success" if total_spend(state) <= income else "partial",
        "trace": trace,
    }
