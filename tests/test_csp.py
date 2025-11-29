# budget_optimizer/tests/test_csp.py

from budget_optimizer.models import State
from budget_optimizer.csp import feasibility_early_check, is_partial_valid, is_goal
from budget_optimizer.config import MINIMUMS


def test_feasibility():
    ok, msg = feasibility_early_check(2000000, MINIMUMS)
    assert ok

    bad, msg = feasibility_early_check(100000, MINIMUMS)
    assert not bad


def test_partial_valid():
    s = State(800000, 650000, 10000, 5000, 0, 0, 30000)
    assert is_partial_valid(s, 2000000)


def test_goal_fail_tabungan():
    s = State(800000, 650000, 10000, 5000, 0, 0, 30000)
    ok, reason = is_goal(s, 2000000, MINIMUMS, 300000)
    assert not ok
