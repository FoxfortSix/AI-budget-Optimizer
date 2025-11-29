"""
validator_ai.py
----------------
Modul ini memastikan bahwa hasil AI (final_state) aman dan valid secara finansial.

Validator ini diwajibkan karena:
- Gen-AI kadang memberikan angka tidak realistis (negatif / lebih dari income)
- Solver seperti greedy/SA bisa menghasilkan total yang melebihi income
- Kita harus tetap menjaga minimum kebutuhan dasar (MINIMUMS)

Validator akan memperbaiki error ringan secara otomatis.
Error berat akan tetap ditandai tapi tidak membatalkan hasil.
"""

from typing import Dict, Any

from budget_optimizer.config import CATEGORIES, MINIMUMS


# ------------------------------------------------------------
# Basic Validation Utilities
# ------------------------------------------------------------
def clamp(value: int, min_val: int, max_val: int) -> int:
    """Pastikan value tidak keluar dari range."""
    return max(min_val, min(value, max_val))


def sum_state(state: Dict[str, int]) -> int:
    return sum(state.values())


# ------------------------------------------------------------
# MAIN VALIDATION FUNCTION
# ------------------------------------------------------------
def validate_final_state(
    final_state: Dict[str, int],
    minimums: Dict[str, int] = MINIMUMS,
    income: int = None,
    allow_fix: bool = True,
) -> Dict[str, Any]:
    """
    Validasi akhir hasil AI/solver.

    Return format:
    {
        "status": "success" | "warning" | "error",
        "final_state": { ...state... },
        "notes": [ ...list of warnings... ]
    }
    """

    notes = []
    state = final_state.copy()

    if income is None:
        # fallback safety: gunakan sum state sebagai batas
        income = sum(state.values())

    # --------------------------------------------------------
    # 1. Fix negative values
    # --------------------------------------------------------
    for cat in CATEGORIES:
        if state[cat] < 0:
            notes.append(f"Nilai negatif ditemukan pada '{cat}', diperbaiki menjadi 0.")
            if allow_fix:
                state[cat] = 0

    # --------------------------------------------------------
    # 2. Enforce minimum requirement
    # --------------------------------------------------------
    for cat in CATEGORIES:
        if state[cat] < minimums[cat]:
            notes.append(
                f"Kategori '{cat}' di bawah minimum ({state[cat]} < {minimums[cat]}), diperbaiki."
            )
            if allow_fix:
                state[cat] = minimums[cat]

    # --------------------------------------------------------
    # 3. Check if sum exceeds income
    # --------------------------------------------------------
    total = sum_state(state)
    if total > income:
        diff = total - income
        notes.append(
            f"Total melebihi income sebesar {diff}, melakukan normalisasi downward."
        )

        if allow_fix:
            # Kurangi kategori yang tidak esensial terlebih dahulu
            adjustable_order = [
                "hiburan",
                "jajan",
                "internet",
                "transport",
                "makan",
                "kos",
            ]

            for cat in adjustable_order:
                if diff <= 0:
                    break
                available = state[cat] - minimums[cat]
                if available > 0:
                    take = min(available, diff)
                    state[cat] -= take
                    diff -= take

            # Jika masih ada sisa diff (hampir mustahil), clamp total brute force
            if diff > 0:
                notes.append("Total masih berlebih, dilakukan brute clamp.")
                factor = income / sum_state(state)
                for cat in CATEGORIES:
                    state[cat] = int(state[cat] * factor)

    # --------------------------------------------------------
    # 4. Final safety clamp
    # --------------------------------------------------------
    for cat in CATEGORIES:
        state[cat] = clamp(state[cat], 0, income)

    # --------------------------------------------------------
    # 5. Format response
    # --------------------------------------------------------
    if len(notes) == 0:
        return {
            "status": "success",
            "final_state": state,
            "notes": ["Valid. Tidak ada masalah."],
        }

    return {
        "status": "warning",
        "final_state": state,
        "notes": notes,
    }
