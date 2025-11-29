# budget_optimizer/genai/ai_router.py
"""
AI Router
---------
Mengatur jalur solver:
A* → Greedy → SA → Gen-AI Fallback
"""

from typing import Dict, Any

from budget_optimizer.astar import astar_search
from budget_optimizer.greedy import greedy_optimize
from budget_optimizer.simulated_annealing import simulated_annealing
from .fallback_solver import run_fallback_chain
from .validator import validate_final_state


class AIRouter:
    def __init__(self, *, timeout_ms=4000, max_nodes=60000):
        self.timeout_ms = timeout_ms
        self.max_nodes = max_nodes

    # ---------------------------------------------------------
    # uniform packaging
    # ---------------------------------------------------------
    def _pkg(self, *, method, status, final_state=None, plan=None, detail=None):
        return {
            "method": method,
            "status": status,
            "final_state": final_state,
            "plan": plan,
            "detail": detail,
        }

    # ---------------------------------------------------------
    # TRY A*
    # ---------------------------------------------------------
    def try_astar(self, state, income, minimums, target, delta):
        # Sesuaikan parameter dengan definisi di astar.py
        res = astar_search(
            init_state=state,
            income=income,
            minimums=minimums,
            target=target,
            delta=delta,
            max_iter=self.max_nodes,
        )

        # FIX: Hapus akses ke res["plan"] dan res["metrics"]
        # Ganti dengan res.get("trace") atau None

        if res["status"] == "success":
            return self._pkg(
                method="A* Search",
                status="success",
                final_state=res["final_state"],
                plan=None,  # astar.py tidak return 'plan'
                detail=res.get("trace"),  # Gunakan 'trace' sebagai detail
            )

        return self._pkg(
            method="A* Search",
            status=res["status"],
            final_state=None,
            plan=None,
            detail=res.get("trace"),  # Gunakan 'trace' sebagai detail
        )

    # ---------------------------------------------------------
    # TRY GREEDY
    # ---------------------------------------------------------
    def try_greedy(self, state, income, minimums, target, delta):  # Tambah minimums
        # Urutan argumen HARUS: state, income, minimums, target, delta
        g = greedy_optimize(state, income, minimums, target, delta)

        if g["status"] == "success":
            return self._pkg(
                method="Greedy",
                status="success",
                final_state=g["final_state"],
                plan=None,
            )

        return self._pkg(
            method="Greedy",
            status="failed",
            final_state=None,
            plan=None,
        )

    # ---------------------------------------------------------
    # TRY SA
    # ---------------------------------------------------------
    def try_sa(self, state, income, minimums, target, delta):  # Tambah minimums
        # Urutan argumen HARUS: state, income, minimums, target, delta
        sa = simulated_annealing(state, income, minimums, target, delta)

        if sa["status"] == "success":
            return self._pkg(
                method="Simulated Annealing",
                status="success",
                final_state=sa["final_state"],
                plan=None,
            )

        return self._pkg(
            method="Simulated Annealing",
            status="failed",
            final_state=None,
            plan=None,
        )

    # ---------------------------------------------------------
    # MAIN: RUN CHAIN
    # ---------------------------------------------------------
    def solve(self, state, income, minimums, target, delta):
        trace = []

        # ==============================
        # 1. A*
        # ==============================
        a_star = self.try_astar(state, income, minimums, target, delta)
        trace.append(a_star)

        if a_star["status"] == "success":
            validated = validate_final_state(a_star["final_state"], minimums)
            return validated | {"trace": trace}

        # ==============================
        # 2. GREEDY
        # ==============================
        # FIX: Pass minimums ke try_greedy
        greedy = self.try_greedy(state, income, minimums, target, delta)
        trace.append(greedy)

        if greedy["status"] == "success":
            validated = validate_final_state(greedy["final_state"], minimums)
            return validated | {"trace": trace}

        # ==============================
        # 3. SA
        # ==============================
        # FIX: Pass minimums ke try_sa
        sa = self.try_sa(state, income, minimums, target, delta)
        trace.append(sa)

        if sa["status"] == "success":
            validated = validate_final_state(sa["final_state"], minimums)
            return validated | {"trace": trace}

        # ==============================
        # 4. Fallback
        # ==============================
        fb = run_fallback_chain(state, income, minimums, target, delta)
        trace.append(fb)

        return fb | {"trace": trace}
