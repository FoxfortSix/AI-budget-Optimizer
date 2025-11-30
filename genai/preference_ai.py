# budget_optimizer/genai/preference_ai.py
"""
Preference AI & Smart Baseline
------------------------------
1. interpret_preferences: Mengubah teks jadi kategori (minimal/pas/maksimal).
2. generate_smart_baseline: Mengubah teks jadi angka baseline awal (smart extraction).
"""

from typing import Dict
from .llm_client import llm_json
from budget_optimizer.config import CATEGORIES, MINIMUMS


# ======================================================
# 1. PREFERENCE EXTRACTOR (Tetap Ada)
# ======================================================
def interpret_preferences(user_text: str) -> Dict:
    """Mengubah curhatan user jadi kategori preferensi (minimal/pas/maksimal)."""
    prompt = f"""
    Analisis teks user dan tentukan preferensi budget (minimal/pas/maksimal).
    Output JSON only.
    Input: \"\"\"{user_text}\"\"\"
    Schema: {{ "kos": "...", "makan": "...", ... }}
    """
    result = llm_json(prompt)

    if "error" in result:
        return {cat: "pas" for cat in CATEGORIES}

    cleaned = {}
    for cat in CATEGORIES:
        val = result.get(cat, "pas")
        if val not in ["minimal", "pas", "maksimal"]:
            val = "pas"
        cleaned[cat] = val
    return cleaned


# ======================================================
# 2. SMART BASELINE GENERATOR (BARU! 🔥)
# ======================================================
def generate_smart_baseline(user_text: str, income: int) -> Dict[str, int]:
    """
    Mengekstrak angka spesifik dari chat user.
    Jika user bilang 'internet 30 ribu', masukkan 30000.
    Jika user bilang 'transport 30 ribu per minggu', kalikan 4 jadi 120000.
    Jika tidak ada angka, gunakan estimasi wajar tapi hemat.
    """

    prompt = f"""
    Kamu adalah Smart Budget Extractor. 
    Tugas: Buat baseline anggaran awal (JSON) berdasarkan cerita user.
    
    Data User:
    - Income Total: Rp {income}
    - Cerita User: \"\"\"{user_text}\"\"\"

    Aturan Penting:
    1. **EKSTRAKSI ANGKA**: Jika user menyebut angka spesifik, GUNAKAN ANGKA ITU.
       - Contoh: "Internet 30 ribu" -> "internet": 30000
       - Contoh: "Ongkos 30 ribu seminggu" -> "transport": 120000 (30k x 4)
       - Contoh: "Makan ditanggung ortu" -> "makan": 0
    
    2. **ESTIMASI**: Jika angka tidak disebut, berikan estimasi WAJAR (jangan terlalu kecil/pelit).
       - Jangan gunakan angka default yang tidak masuk akal (misal internet 5000 itu mustahil).
    
    3. **FEASIBILITY**: Pastikan total semua kategori TIDAK melebihi Income ({income}).
    
    Output JSON (Hanya angka integer):
    {{
      "kos": 0,
      "makan": 0,
      "transport": 0,
      "internet": 0,
      "jajan": 0,
      "hiburan": 0,
      "tabungan": 0
    }}
    """

    # Panggil AI
    result = llm_json(prompt)

    # Fallback & Sanitasi (Agar tidak error program)
    final_baseline = {}
    total_val = 0

    if "error" in result:
        # Jika AI gagal, pakai logika minimum default (fallback darurat)
        return {k: MINIMUMS.get(k, 0) for k in CATEGORIES}

    for cat in CATEGORIES:
        # Ambil nilai dari AI, pastikan integer
        val = result.get(cat, MINIMUMS.get(cat, 0))
        try:
            val = int(val)
        except:
            val = 0
        final_baseline[cat] = val
        total_val += val

    # Safety Check: Jika total hasil AI > Income, lakukan scaling down otomatis
    if total_val > income and income > 0:
        factor = income / total_val
        for cat in final_baseline:
            final_baseline[cat] = int(final_baseline[cat] * factor)

    return final_baseline
