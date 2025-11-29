# budget_optimizer/genai/fallback_solver.py
"""
Fallback Solver Chain
---------------------
Greedy → Simulated Annealing → Gen-AI.

Router utama akan memanggil modul ini.
Format output dibuat konsisten dan siap dipakai UI.
"""

from typing import Dict, Any

from budget_optimizer.greedy import greedy_optimize
from budget_optimizer.simulated_annealing import simulated_annealing
from .validator import validate_final_state
from .llm_client import llm_json  # LLM dipanggil langsung dari client


# ---------------------------------------------------------
# Utility: uniform packagestate
# ---------------------------------------------------------
def _pkg(method, status, final_state=None, detail=None):
    return {
        "method": method,
        "status": status,
        "final_state": final_state,
        "detail": detail,
    }


# ---------------------------------------------------------
# Gen-AI fallback (arah rekomendasi, bukan angka final)
# ---------------------------------------------------------
def _llm_recommendation(state_dict, income, target):
    """
    Menghasilkan rekomendasi high-level (preferensi alokasi)
    dari Gemini LLM saat semua solver gagal.
    LLM tidak memproduksi angka final — hanya arah/narah.
    """

    prompt = f"""
User punya kondisi budget berikut:
{state_dict}

Income: {income}
Target tabungan minimum: {target}

Berikan rekomendasi arah alokasi secara HIGH LEVEL.
JANGAN rekomendasikan angka.
Hanya arah seperti "tingkatkan tabungan", "kurangi jajan", dll.

Output JSON EXACT:
{{
  "direction": [
    "arah_saran_1",
    "arah_saran_2",
    "arah_saran_3"
  ],
  "note": "penjelasan fun dan ringan"
}}
"""

    res = llm_json(prompt)

    if "error" in res:
        return {
            "direction": [],
            "note": "LLM gagal memahami input, tapi tetap semangat ya!",
        }

    # Normalisasi
    return {
        "direction": res.get("direction", []),
        "note": res.get("note", ""),
    }


# ---------------------------------------------------------
# MAIN FALLBACK CHAIN
# ---------------------------------------------------------
def run_fallback_chain(
    state,
    income: int,
    minimums: dict,
    target: int,
    delta: int,
) -> Dict[str, Any]:

    trace = []

    # =====================================================
    # 1. GREEDY
    # =====================================================
    g = greedy_optimize(state, income, minimums, target, delta)

    if g["status"] == "success":
        fs = validate_final_state(g["final_state"], minimums)
        entry = _pkg("Greedy Optimization", "success", final_state=g["final_state"])
        trace.append(entry)
        return fs | {"trace": trace}

    trace.append(_pkg("Greedy Optimization", "failed"))

    # =====================================================
    # 2. SIMULATED ANNEALING
    # =====================================================
    sa = simulated_annealing(state, income, minimums, target, delta)

    if sa["status"] == "success":
        fs = validate_final_state(sa["final_state"], minimums)
        entry = _pkg("Simulated Annealing", "success", final_state=sa["final_state"])
        trace.append(entry)
        return fs | {"trace": trace}

    trace.append(_pkg("Simulated Annealing", "failed"))

    # =====================================================
    # 3. GEN-AI (last resort — arah, bukan angka)
    # =====================================================
    ai = _llm_recommendation(state, income, target)

    entry = {
        "method": "Generative AI (Gemini)",
        "status": "success",
        "final_state": None,
        "detail": ai,
    }
    trace.append(entry)

    # Kembalikan rekomendasi arah, bukan angka final
    return {
        "status": "ai_recommendation",
        "final_state": None,
        "direction": ai.get("direction", []),
        "note": ai.get("note", ""),
        "trace": trace,
    }
