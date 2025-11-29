# budget_optimizer/rebalancer.py
"""
Rebalancer
----------
Menghasilkan target distribusi budget berdasarkan:
- preferensi user (minimal / pas / maksimal)
- target tabungan (angka)
- skala normalisasi per kategori
- total income

Rebalancer menghasilkan "ideal target state" yang akan dikejar oleh solver.
"""

from typing import Dict


def build_target_state(
    income: int,
    prefs: Dict[str, str],
    min_scale: Dict[str, int],
    mid_scale: Dict[str, int],
    max_scale: Dict[str, int],
    target_saving: int,
) -> Dict[str, int]:
    """
    Menghasilkan target state sebagai acuan solver.

    prefs:
        kategori -> "minimal" | "pas" | "maksimal"

    min_scale / mid_scale / max_scale:
        kategori -> persentase (dari income)

    target_saving:
        berapa tabungan minimum yang harus dicapai

    Output:
        dict kategori -> nominal uang (integer)
    """

    target = {}

    # 1. Tabungan dipatok dulu
    target["tabungan"] = target_saving

    # 2. Kategori lain menyesuaikan preferensi
    for cat in prefs:
        if cat == "tabungan":
            continue

        pref = prefs[cat]

        if pref == "minimal":
            scale = min_scale.get(cat, 5)
        elif pref == "maksimal":
            scale = max_scale.get(cat, 20)
        else:
            scale = mid_scale.get(cat, 10)  # default "pas"

        target[cat] = int(income * (scale / 100.0))

    # 3. Normalisasi: jangan sampai lebih besar dari income
    total = sum(target.values())

    if total > income:
        # scale down everything except tabungan
        excess = total - income

        for cat in target:
            if cat == "tabungan":  # tabungan wajib dipertahankan
                continue

            reduce_amount = min(target[cat], excess)
            target[cat] -= reduce_amount
            excess -= reduce_amount

            if excess <= 0:
                break

    return target


def pretty_target_report(target: Dict[str, int]) -> str:
    """
    Biarkan modul UI menampilkan ke user dalam format user friendly.
    """
    lines = ["🎯 *Target distribusi anggaran berdasarkan preferensi Anda:*", ""]
    for cat, amount in target.items():
        lines.append(f"- **{cat.capitalize()}**: Rp {amount:,}")
    return "\n".join(lines)
