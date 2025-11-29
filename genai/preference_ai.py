# budget_optimizer/genai/preference_ai.py
"""
Preference AI
-------------
Mengubah curhatan user (natural language)
→ menjadi kategori preferensi anggaran.

Contoh input user:
    "Gue anak kos, pengen makan tetep enak,
     tapi jajan dikurangin, tabungan dipush."

Output:
{
  "kos": "minimal",
  "makan": "maksimal",
  "transport": "pas",
  "internet": "pas",
  "jajan": "minimal",
  "hiburan": "minimal",
  "tabungan": "maksimal"
}

Kategori preferensi:
- "minimal"
- "pas"
- "maksimal"
"""

from typing import Dict
from .llm_client import llm_json


# Semua kategori yang bisa diberi preferensi
CATEGORIES = ["kos", "makan", "transport", "internet", "jajan", "hiburan", "tabungan"]


# ======================================================
# MAIN FUNCTION
# ======================================================


def interpret_preferences(user_text: str) -> Dict:
    """
    Meminta Gemini mengekstraksi preferensi budget
    dari curhatan user.
    """

    prompt = f"""
User akan memberikan deskripsi gaya hidup dan preferensi pengeluaran.
Tugasmu adalah memetakannya ke dalam 3 kategori preferensi:
- "minimal"
- "pas"
- "maksimal"

Berikan JSON EXACTLY dengan struktur:
{{
  "kos": "...",
  "makan": "...",
  "transport": "...",
  "internet": "...",
  "jajan": "...",
  "hiburan": "...",
  "tabungan": "..."
}}

Aturan pemetaan:
- "minimal" = user ingin hemat atau memotong bagian tersebut.
- "pas" = user nyaman, normal, tidak ingin berubah banyak.
- "maksimal" = user ingin memprioritaskan bagian tersebut.

Jika user tidak menyebut kategori tertentu,
isi saja dengan "pas".

Gunakan bahasa ringan dan vibe anak muda saat berpikir,
tapi output akhir tetap harus JSON bersih.

Berikut input user:
\"\"\"{user_text}\"\"\"
"""

    result = llm_json(prompt)

    # Jika parsing gagal, fallback
    if "error" in result:
        return {cat: "pas" for cat in CATEGORIES}

    # Bersihkan hasil: pastikan semua kategori ada
    cleaned = {}
    for cat in CATEGORIES:
        val = result.get(cat, "pas")
        if val not in ["minimal", "pas", "maksimal"]:
            val = "pas"
        cleaned[cat] = val

    return cleaned
