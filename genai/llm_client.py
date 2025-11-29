"""
llm_client.py
-------------
Client wrapper untuk memanggil Google Gemini API secara aman & konsisten.

FITUR:
- Mendukung Gemini Flash / Pro
- Retry logic otomatis
- Output JSON-safe (AI dipaksa menghasilkan JSON valid)
- Tone anak muda (fun & friendly)
- Error normalization
- Abstraksi sederhana: llm_json(prompt) dan llm_text(prompt)
"""

import json
import time
import requests
from typing import Dict, Any, Optional


# ============================================================
# KONFIGURASI GEMINI API
# ============================================================
GEMINI_API_KEY = "AIzaSyDsDRVObmlcM5YcJnqcba_ToG_vNu1C_HY"  # API 
GEMINI_MODEL = "gemini-2.0-flash"  # Update ke model yang lebih baru/stabil
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


# ============================================================
# Utility: JSON-safe extraction
# ============================================================
def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Mengambil JSON dari output AI. Kadang AI memberi text + JSON campur.
    Fungsi ini mencari blok { ... } pertama yang valid.
    """
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        raw = text[start:end]
        return json.loads(raw)
    except Exception:
        return {"error": "AI tidak memberikan JSON valid", "raw_output": text}


# ============================================================
# CORE REQUEST FUNCTION
# ============================================================
def _make_request(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Wrapper request dgn error handling & retry 3x."""

    url = f"{GEMINI_ENDPOINT}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    for attempt in range(3):
        try:
            res = requests.post(url, json=payload, timeout=8)

            if res.status_code == 200:
                return res.json()

            time.sleep(1)  # retry delay

        except Exception:
            time.sleep(1)
            continue

    return None


# ============================================================
# HIGH LEVEL API — TEXT OUTPUT
# ============================================================
def llm_text(prompt: str, temperature: float = 0.4) -> str:
    """
    Mendapatkan output TEXT dari Gemini.
    Cocok untuk penjelasan, reasoning, atau rekomendasi fun.
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "topK": 40,
            "topP": 0.9,
            "maxOutputTokens": 512,
        },
    }

    res = _make_request(payload)

    if res is None:
        return "[LLM ERROR] Gagal menghubungi Gemini API."

    try:
        return res["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return str(res)


# ============================================================
# HIGH LEVEL API — JSON OUTPUT
# ============================================================
def llm_json(
    prompt: str, temperature: float = 0.2, schema_hint: str = ""
) -> Dict[str, Any]:
    """
    Mendapatkan output JSON dari Gemini.
    prompt: instruksi text
    schema_hint: contoh JSON yang diharapkan (optional)
    """

    # Prompt yang memaksa AI output JSON *strict*
    full_prompt = f"""
Kamu adalah AI financial assistant dengan tone anak muda (fun, santai, tapi tetap logis).
HASILKAN **HANYA JSON VALID** tanpa teks tambahan.

JANGAN memberi code block markdown (```json).
JANGAN memberi komentar.
HANYA JSON bersih.

Schema contoh yang benar:
{schema_hint}

Prompt user:
{prompt}
"""

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "topK": 20,
            "topP": 0.9,
            "maxOutputTokens": 512,
        },
    }

    res = _make_request(payload)

    if res is None:
        return {"status": "error", "reason": "Tidak dapat menghubungi Gemini API"}

    try:
        raw_text = res["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return {"status": "error", "raw": res}

    return extract_json_from_text(raw_text)
