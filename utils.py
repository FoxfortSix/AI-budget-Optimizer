# budget_optimizer/utils.py

from .models import State


def normalize_state(state: State, income: int) -> State:
    """
    Make sure total <= income by reducing soft categories first.
    """
    d = state.to_dict()
    total = sum(d.values())

    excess = total - income

    if excess <= 0:
        return state

    # Categories allowed to be reduced (order matters)
    adjustable = ["jajan", "hiburan", "transport", "internet"]

    for cat in adjustable:
        if excess <= 0:
            break
        available = d[cat]
        deduction = min(available, excess)
        d[cat] -= deduction
        excess -= deduction

    return State.from_dict(d)
