# budget_solver.py
# Linear Programming-based Budget Optimizer (Option B: Output matches Solver Panel)

from typing import Dict, Any
import numpy as np
from scipy.optimize import linprog


class BudgetSolver:
    """
    Linear Programming Budget Solver
    Output fully conforms to the UTS Solver Panel structure:

    |— Solver Panel
    |     |— Final Budget
    |     |— Trace
    |     |— Constraints
    """

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.categories = list(data["baseline"].keys())
        self.n = len(self.categories)

    # ---------------------------------------------------------
    # Build Constraints
    # ---------------------------------------------------------
    def _build_constraints(self):
        base = self.data["baseline"]
        cons = self.data.get("constraints", {})

        mins = np.array(
            [cons.get(cat, {}).get("min", 0) for cat in self.categories], dtype=float
        )

        maxs = np.array(
            [cons.get(cat, {}).get("max", 1e12) for cat in self.categories], dtype=float
        )

        income = self.data.get("income", sum(base.values()))

        A_eq = np.ones((1, self.n))
        b_eq = np.array([income])

        bounds = [(mins[i], maxs[i]) for i in range(self.n)]

        return A_eq, b_eq, bounds

    # ---------------------------------------------------------
    # Objective Function
    # ---------------------------------------------------------
    def _objective(self):
        base = self.data["baseline"]
        base_arr = np.array([base[c] for c in self.categories], dtype=float)

        # LP cannot handle quadratic directly → approximate by linear bias
        c = -2 * base_arr

        return c

    # ---------------------------------------------------------
    # Solve LP
    # ---------------------------------------------------------
    def solve(self) -> Dict[str, Any]:
        A_eq, b_eq, bounds = self._build_constraints()
        c = self._objective()

        result = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

        if not result.success:
            return {
                "success": False,
                "solver_panel": {
                    "final_budget": {},
                    "trace": {"status": result.message, "raw": str(result)},
                    "constraints": self.data.get("constraints", {}),
                },
            }

        final_budget = {
            cat: float(result.x[i]) for i, cat in enumerate(self.categories)
        }

        trace = {
            "baseline": self.data["baseline"],
            "final": final_budget,
            "status": result.message,
            "raw": str(result),
        }

        constraints = self.data.get("constraints", {})

        return {
            "success": True,
            "solver_panel": {
                "final_budget": final_budget,
                "trace": trace,
                "constraints": constraints,
            },
        }


# End of file
