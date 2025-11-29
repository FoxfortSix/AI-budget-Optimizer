# budget_optimizer/scaler.py
"""
Dynamic Budget Scaling
----------------------

Modul ini mengubah preferensi user (minimal/pas/maksimal)
menjadi angka budget real berdasarkan income.

Prosesnya:
1. Untuk setiap kategori:
      - ambil MINIMUM
      - ambil REASONABLE_MAX
2. Berdasarkan preferensi:
      minimal  -> mendekati MINIMUM
      pas      -> nilai tengah antara MINIMUM dan MAX
      maksimal -> mendekati MAX
3. Hasilkan soft target untuk setiap kategori,
   tapi masih dalam bentuk "proporsi", bukan angka.
4. convert_preferences_to_targets(income, profile)
   mengubah semua proporsi menjadi angka riil.

Output akhirnya dipakai oleh:
- target_generator.py
- Gen-AI advisor
- fallback logic
"""

from typing import Dict
from .config import MINIMUMS, REASONABLE_MAX
from .preference import PreferenceProfile, CATEGORIES


# ============================================================
# 1. Preference → scalar weight
# ============================================================


def preference_to_weight(mode: str) -> float:
    """
    Mengubah mode preferensi menjadi bobot 0..1.
    0.0 = minimal (dekat minimum)
    0.5 = pas (tengah)
    1.0 = maksimal (dekat max)
    """
    if mode == "minimal":
        return 0.0
    if mode == "maksimal":
        return 1.0
    return 0.5  # "pas"


# ============================================================
# 2. Hitung target budget kasar per kategori (belum skala income)
# ============================================================


def compute_raw_target_range(profile: PreferenceProfile) -> Dict[str, float]:
    """
    Mengembalikan nilai target *kasar* sebelum disesuaikan income.
    Ini adalah nilai antara MINIMUM dan REASONABLE_MAX.
    """
    raw = {}

    for cat in CATEGORIES:
        minv = MINIMUMS.get(cat, 0)
        maxv = REASONABLE_MAX.get(cat, minv * 2)

        weight = preference_to_weight(profile.get_mode(cat))

        # interpolasi linear
        # raw_target = minv + w * (maxv - minv)
        raw[cat] = minv + weight * (maxv - minv)

    return raw


# ============================================================
# 3. Normalisasi raw targets supaya cocok dengan income user
# ============================================================


def scale_targets_to_income(
    raw_targets: Dict[str, float], income: int, emergency_mode: bool = False
) -> Dict[str, int]:
    """
    Mengubah target kasar menjadi budget aktual yang sesuai income.
    Langkah:
      1. Hitung sum raw
      2. Jika sum <= income → langsung bulatkan
      3. Jika sum > income → scale down secara proporsional

    emergency_mode:
      Jika True → scaling lebih agresif (misal income terlalu kecil)
    """

    total_raw = sum(raw_targets.values())

    # Jika tidak butuh scaling
    if total_raw <= income:
        return {cat: int(val) for cat, val in raw_targets.items()}

    # Perlu scaling proporsional
    ratio = income / total_raw

    # Emergency mode = scaling + sedikit penalty hiburan/jajan
    # untuk memberikan lebih banyak ruang
    if emergency_mode:
        ratio *= 0.95

    scaled = {}
    for cat, raw_val in raw_targets.items():
        scaled[cat] = int(raw_val * ratio)

    return scaled


# ============================================================
# 4. Fungsi utama: preference profile → budget target final
# ============================================================


def convert_preferences_to_targets(
    income: int, profile: PreferenceProfile, emergency_mode: bool = False
) -> Dict[str, int]:
    """
    Fungsi paling penting:
      preference (minimal/pas/maksimal)
      → raw target
      → scaled target (sesuai income)
    """
    raw = compute_raw_target_range(profile)
    targets = scale_targets_to_income(raw, income, emergency_mode)
    return targets
