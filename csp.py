# budget_optimizer/csp.py

from typing import Dict, Tuple
from .models import State
from .config import MINIMUMS, CATEGORIES


def feasibility_early_check(
    income: int, minimums: Dict[str, int] = MINIMUMS
) -> Tuple[bool, str]:
    total_min = sum(minimums.values())
    if total_min > income:
        return (
            False,
            f"Total minimum requirement ({total_min}) exceeds income ({income})",
        )
    return True, "OK"


def is_partial_valid(
    state: State, income: int, minimums: Dict[str, int] = MINIMUMS
) -> bool:
    d = state.to_dict()

    # All non-negative
    if any(v < 0 for v in d.values()):
        return False

    # Hard minimums
    for cat, minv in minimums.items():
        if d[cat] < minv:
            return False

    # Sum constraint
    if sum(d.values()) > income:
        return False

    return True


def is_goal(
    state: State,
    income: int,
    minimums: Dict[str, int] = MINIMUMS,
    target_tabungan: int = 300000,
) -> Tuple[bool, str]:
    d = state.to_dict()

    # Minimums check
    for cat, minv in minimums.items():
        if d[cat] < minv:
            return False, f"{cat} below minimum"

    # Tabungan target
    if d["tabungan"] < target_tabungan:
        return False, "Tabungan below target"

    # Sum constraint
    if sum(d.values()) > income:
        return False, "Total allocation exceeds income"

    return True, "Goal reached"
