# budget_optimizer/genai/advisor_ai.py
"""
Advisor AI
----------
Menghasilkan saran finansial dari:
- kondisi anggaran user
- preferensi user
- target tabungan

Tone: fun, friendly, anak muda.
Output: JSON structured untuk UI.
"""

from typing import Dict
from .llm_client import llm_json


def generate_advice(state: Dict, prefs: Dict, target_saving: int) -> Dict:
    """
    Beri saran keuangan dengan tone fun tetapi output tetap JSON structured.
    """

    prompt = f"""
Kamu adalah financial advisor muda yang fun dan relate dengan anak kuliahan/anak kos.

User punya kondisi finansial berikut (state):
{state}

Preferensi user:
{prefs}

Target tabungan minimum: Rp {target_saving}

Tugasmu:
1. Analisis kondisi user dan preferensi mereka.
2. Berikan rekomendasi pengeluaran secara high-level.
3. Berikan tips yang ringan dan tidak menghakimi.
4. Tone harus fun, santai, kayak teman nongkrong yang jago ngatur duit.
5. Output hanya berupa JSON dengan struktur:

{{
  "summary": "ringkasan kondisi user (fun tone)",
  "priority_suggestion": [
    "saran 1",
    "saran 2",
    "saran 3"
  ],
  "saving_tips": [
    "tips tabungan 1",
    "tips tabungan 2"
  ],
  "risk_notes": [
    "resiko 1",
    "resiko 2"
  ]
}}

Jangan beri penjelasan tambahan di luar JSON.
Gunakan bahasa Indonesia dengan gaya anak muda.
"""

    result = llm_json(prompt)

    # Fallback jika error
    if "error" in result:
        return {
            "summary": "Gue agak bingung baca datanya, tapi tenang aja, semangat terus atur duitnya ya!",
            "priority_suggestion": [],
            "saving_tips": [],
            "risk_notes": [],
        }

    # Normalisasi field agar aman
    cleaned = {
        "summary": result.get("summary", ""),
        "priority_suggestion": result.get("priority_suggestion", []),
        "saving_tips": result.get("saving_tips", []),
        "risk_notes": result.get("risk_notes", []),
    }

    return cleaned
