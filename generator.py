# budget_optimizer/target_generator.py
"""
Target Generator
----------------

Menghasilkan "target state" final berdasarkan:

1. Income user
2. Preference profile (minimal / pas / maksimal)
3. Hasil budget scaling dari scaler.py
4. Kondisi riil user (current state)
5. Validasi minimum constraints
6. Fallback ringan jika target tidak tercapai

Output:
- target_state (dict)
- feasibility status
- optional reasoning (for Gen-AI layer)
"""

from typing import Dict, Tuple

from .models import State
from .config import MINIMUMS, CATEGORIES
from .preference import PreferenceProfile
from .scaler import convert_preferences_to_targets
from .csp import feasibility_early_check


# ============================================================
# 1. Hard clamp to minimum constraints
# ============================================================


def clamp_to_minimums(targets: Dict[str, int]) -> Dict[str, int]:
    """Pastikan setiap kategori tidak kurang dari MINIMUMS."""
    fixed = {}

    for cat in CATEGORIES:
        minv = MINIMUMS.get(cat, 0)
        fixed[cat] = max(targets.get(cat, 0), minv)

    return fixed


# ============================================================
# 2. Smooth merge current state with target
# ============================================================


def blend_current_with_target(
    current: Dict[str, int], target: Dict[str, int], factor: float = 0.4
) -> Dict[str, int]:
    """
    Smooth blending antara kondisi riil dan target.
    factor = 0.0 → full current
    factor = 1.0 → full target
    default = 0.4 (bergerak 40% menuju target)

    Ini membuat solusi lebih manusiawi dan tidak terlalu ekstrem.
    """
    blended = {}
    for cat in CATEGORIES:
        c = current[cat]
        t = target[cat]
        blended[cat] = int(c + factor * (t - c))
    return blended


# ============================================================
# 3. Fallback: Kurangi kategori soft jika total > income
# ============================================================


def soft_reduce_until_fit(state_dict: Dict[str, int], income: int) -> Dict[str, int]:
    """
    Jika total masih melebihi income, kurangi kategori soft secara bertahap.
    Prioritas: hiburan > jajan > transport > internet
    """
    order = ["hiburan", "jajan", "transport", "internet"]

    d = state_dict.copy()

    while sum(d.values()) > income:
        excess = sum(d.values()) - income
        if excess <= 0:
            break

        changed = False
        for cat in order:
            if d[cat] > MINIMUMS.get(cat, 0):
                deduction = min(20000, excess)  # step kecil
                d[cat] -= deduction
                excess -= deduction
                changed = True
                if excess <= 0:
                    break

        # jika sudah tidak bisa dikurangi lagi
        if not changed:
            break

    return d


# ============================================================
# 4. Fungsi utama untuk menghasilkan target budgeting final
# ============================================================


def generate_target_state(
    income: int,
    current_state: State,
    profile: PreferenceProfile,
    emergency_mode: bool = False,
) -> Tuple[Dict[str, int], Dict[str, str]]:
    """
    Menghasilkan target budgeting final + reasoning dictionary.

    Return:
      target_state (dict)
      reasoning (dict)
    """

    reasoning = {}

    # ------------------------------------------------------------------
    # 1. Early feasibility check (cek apakah minimum saja sudah cukup)
    # ------------------------------------------------------------------
    ok_feas, msg_feas = feasibility_early_check(income)
    reasoning["feasibility"] = msg_feas

    if not ok_feas:
        # Tidak mungkin memenuhi minimum → fallback ke pure minimum profile
        fail_target = MINIMUMS.copy()
        return fail_target, {"error": msg_feas}

    # ------------------------------------------------------------------
    # 2. Hitung target awal dari preferensi
    # ------------------------------------------------------------------
    raw_target = convert_preferences_to_targets(
        income=income, profile=profile, emergency_mode=emergency_mode
    )
    reasoning["raw_target"] = raw_target

    # ------------------------------------------------------------------
    # 3. Clamp ke minimum constraints
    # ------------------------------------------------------------------
    clamped = clamp_to_minimums(raw_target)
    reasoning["clamped"] = clamped

    # ------------------------------------------------------------------
    # 4. Smooth merge dengan kondisi real
    # ------------------------------------------------------------------
    blended = blend_current_with_target(
        current=current_state.to_dict(), target=clamped, factor=0.4
    )
    reasoning["blended"] = blended

    # ------------------------------------------------------------------
    # 5. Fallback jika masih melebihi income
    # ------------------------------------------------------------------
    fixed = soft_reduce_until_fit(blended, income)
    reasoning["final"] = fixed

    return fixed, reasoning
