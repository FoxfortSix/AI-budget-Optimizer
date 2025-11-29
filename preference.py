# budget_optimizer/preference.py
"""
Preference Engine for Budget Optimizer
--------------------------------------

Setiap kategori memiliki 3 mode preferensi:
- "minimal"  : seminim mungkin, cukup bertahan hidup
- "pas"      : kebutuhan normal / standar
- "maksimal" : kebutuhan nyaman, tidak terlalu menekan diri

Module ini hanya menghasilkan "preference profile",
belum menghitung angka real — itu dilakukan di scaler.py.
"""

from typing import Dict
from dataclasses import dataclass


# ============================================================
# 1. Preference Modes (global constants)
# ============================================================

PREFERENCE_MODES = ["minimal", "pas", "maksimal"]

# kategori yang dikenali
CATEGORIES = [
    "kos",
    "makan",
    "transport",
    "internet",
    "jajan",
    "hiburan",
    "tabungan",
]


# ============================================================
# 2. PreferenceProfile (hasil pilihan user)
# ============================================================


@dataclass(frozen=True)
class PreferenceProfile:
    """
    Contoh:
    PreferenceProfile({
        "kos": "minimal",
        "makan": "pas",
        "jajan": "maksimal",
        ...
    })
    """

    mapping: Dict[str, str]

    def get_mode(self, category: str) -> str:
        """Return chosen mode for a category."""
        return self.mapping.get(category, "pas")  # default: pas


# ============================================================
# 3. Helper untuk membuat profile dari UI input
# ============================================================


def create_preference_profile(user_input: Dict[str, str]) -> PreferenceProfile:
    """
    user_input contoh:
    {
       "kos": "maksimal",
       "makan": "pas",
       "jajan": "minimal",
       ...
    }
    """
    validated = {}
    for cat in CATEGORIES:
        mode = user_input.get(cat, "pas").lower()

        if mode not in PREFERENCE_MODES:
            mode = "pas"

        validated[cat] = mode

    return PreferenceProfile(validated)


# ============================================================
# 4. Default profile (kalau user tidak memilih apa-apa)
# ============================================================


def default_preference_profile() -> PreferenceProfile:
    """
    Default semua kategori 'pas'.
    """
    return PreferenceProfile({cat: "pas" for cat in CATEGORIES})
