import sys
import os

# Mendapatkan path absolut ke folder saat ini
current_dir = os.path.dirname(os.path.abspath(__file__))
# Mendapatkan path parent (folder di atasnya)
parent_dir = os.path.dirname(current_dir)

# Menambahkan parent dir ke sys.path agar Python bisa mengenali 'budget_optimizer' sebagai paket
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# app.py (Part 1 of 7)
# AI Budget Assistant — Chat Mode (clean rebuild)
# Paste this at top of your app.py (overwrite previous top if ada)

import streamlit as st
import json
import re
import time
from typing import Dict, Any, Optional

# === Core internal imports (modules you already have) ===
from budget_optimizer.genai.llm_client import llm_text, llm_json
from budget_optimizer.genai.preference_ai import interpret_preferences
from budget_optimizer.genai.advisor import generate_advice
from budget_optimizer.genai.ai_router import AIRouter
from budget_optimizer.utils import normalize_state
from budget_optimizer.config import MINIMUMS, CATEGORIES

# === Visualization placeholders (implemented later) ===
# from budget_optimizer.genai.visualization import plot_pie, plot_before_after

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="AI Budget Assistant", page_icon="💬", layout="centered")
st.title("💬 Smart Budget Assistant (Chat Mode)")

# ============================================================
# SESSION STATE — single source of truth keys
# ============================================================
# Keys we'll use (consistent):
# - messages: list of chat messages
# - detected_income: int or None
# - detected_prefs: dict or None
# - ai_ready_for_baseline: bool
# - baseline: dict (baseline amounts)
# - run_optimizer: bool
# - solver_output: dict (result from router)
# - target_tabungan: int (optional)
# - delta: int

if "messages" not in st.session_state:
    st.session_state["messages"] = (
        []
    )  # each item: {"role":"user"|"assistant","content":str}

if "detected_income" not in st.session_state:
    st.session_state["detected_income"] = None

if "detected_prefs" not in st.session_state:
    st.session_state["detected_prefs"] = None

if "ai_ready_for_baseline" not in st.session_state:
    st.session_state["ai_ready_for_baseline"] = False

if "baseline" not in st.session_state:
    st.session_state["baseline"] = None

if "run_optimizer" not in st.session_state:
    st.session_state["run_optimizer"] = False

if "solver_output" not in st.session_state:
    st.session_state["solver_output"] = None

if "target_tabungan" not in st.session_state:
    st.session_state["target_tabungan"] = 0

if "delta" not in st.session_state:
    st.session_state["delta"] = 50000

if "final_budget" not in st.session_state:
    st.session_state.final_budget = None

if "solver_trace" not in st.session_state:
    st.session_state.solver_trace = None

if "solver_constraints" not in st.session_state:
    st.session_state.solver_constraints = None


# Small helper to pretty-print Rupiah integers
def rupiah(x: int) -> str:
    try:
        return f"Rp {int(x):,}"
    except Exception:
        return str(x)


# ============================================================
# PART 2 — CHAT UTILITIES & AI DETECTION ENGINE
# ============================================================


# ------------------------------------------------------------
# RENDER CHAT HISTORY
# ------------------------------------------------------------
def render_chat():
    """Render seluruh riwayat chat."""
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])


# ------------------------------------------------------------
# EXTRACT INCOME FROM USER TEXT (REVISED)
# ------------------------------------------------------------
def try_detect_income(text: str) -> Optional[int]:
    """
    Deteksi income yang lebih cerdas (handle teks bebas dan posisi di mana saja).
    """
    import re

    t = text.lower()

    # 1. Cek format "X juta" (misal: "gaji 4 juta", "4.5juta")
    # Gunakan re.search (bukan match) agar bisa deteksi di tengah kalimat
    m_juta = re.search(r"(\d+[.,]?\d*)\s*juta", t)
    if m_juta:
        val_str = m_juta.group(1).replace(",", ".")
        return int(float(val_str) * 1_000_000)

    # 2. Cek format "X ribu", "X rb", "X k"
    m_ribu = re.search(r"(\d+)\s*(ribu|rb|k)\b", t)
    if m_ribu:
        return int(m_ribu.group(1)) * 1000

    # 3. Format angka murni (misal 4000000)
    # Hapus titik/koma ribuan dulu
    clean_text = text.replace(".", "").replace(",", "")
    nums = re.findall(r"\d+", clean_text)

    if not nums:
        return None

    # Ambil angka terbesar
    n = max(int(x) for x in nums)

    # Logika fallback:
    # Jika angka sangat kecil (< 100), kemungkinan user nulis "gaji 5" (maksudnya 5 juta)
    # Logic lama (n * 1000) kita ganti biar lebih aman.
    if n < 1000:
        if n < 100:
            return n * 1_000_000  # Asumsi "gaji 5" = 5 juta
        return n * 1000

    return n


# ------------------------------------------------------------
# CHECK IF READY FOR BASELINE
# ------------------------------------------------------------
def check_if_ready_for_baseline() -> bool:
    """
    Baseline dimulai otomatis jika:
    - income sudah terdeteksi
    - prefs sudah terdeteksi
    """
    income_ok = st.session_state["detected_income"] is not None
    prefs_ok = st.session_state["detected_prefs"] is not None

    return income_ok and prefs_ok


# ------------------------------------------------------------
# RAW AI CHAT (NATURAL TEXT)
# ------------------------------------------------------------
def ai_chat(user_message: str) -> str:
    """
    Mengirim seluruh riwayat percakapan ke Gemini.
    Tidak mengembalikan JSON, hanya natural text.
    """

    # Build conversation text
    conversation = ""
    for m in st.session_state["messages"]:
        role = m["role"].upper()
        content = m["content"]
        conversation += f"{role}: {content}\n"
    conversation += f"USER: {user_message}\nASSISTANT:"

    SYSTEM = """
Kamu adalah AI Financial Assistant yang fun, santai, dan jago membaca konteks.
Tugasmu: ngobrol dengan user sampai semua data keuangan terkumpul.

Objektifmu:
1. Deteksi pendapatan user (income).
2. Deteksi preferensi gaya hidup mereka (hemat/pas/maksimal).
3. Jika info belum lengkap, tanya balik dengan ramah.
4. Jangan membuat budget dulu sebelum income lengkap.
5. Jangan output JSON sekarang — hanya percakapan natural.

Jawaban harus casual, hangat, dan tidak terlalu panjang.
"""

    final_prompt = SYSTEM + "\n\n" + conversation
    response_text = llm_text(final_prompt)
    return response_text.strip()


def ask_ai_until_ready(user_text: str) -> Dict[str, Any]:
    """
    Mengirim pesan user ke AI, lalu mengecek apakah AI merasa data sudah lengkap.
    Baseline baru akan muncul jika AI secara eksplisit bilang "READY".
    """

    # 1. Simpan pesan user ke history (sudah dilakukan di main loop, tapi kita butuh teks lengkap)
    conversation_history = ""
    for m in st.session_state["messages"]:
        role = m["role"].upper()
        content = m["content"]
        conversation_history += f"{role}: {content}\n"

    # Tambahkan pesan user terbaru jika belum masuk history session state
    # (di main loop biasanya sudah di-append, tapi untuk safety kita cek)
    if (
        not st.session_state["messages"]
        or st.session_state["messages"][-1]["content"] != user_text
    ):
        conversation_history += f"USER: {user_text}\n"

    # 2. PROMPT KHUSUS: Minta AI jawab ganda (Reply Chat + Status Ready)
    system_prompt = """
    Kamu adalah AI Budget Assistant. Tugasmu mengumpulkan 2 informasi vital:
    1. INCOME bulanan (nominal angka).
    2. PREFERENSI gaya hidup (hemat/sedang/mewah, prioritas makan/kos, dll).

    Jika informasi BELUM lengkap, tanyakan kekurangannya dengan santai.
    Jika SUDAH lengkap, berikan konfirmasi singkat bahwa kamu siap menghitung.

    OUTPUT HARUS FORMAT JSON SAJA:
    {
      "reply_text": "jawaban ramah ke user...",
      "is_info_complete": true/false
    }
    """

    # Gabungkan prompt dan history
    final_prompt = (
        f"{system_prompt}\n\nRIWAYAT CHAT:\n{conversation_history}\n\nASSISTANT (JSON):"
    )

    # Panggil LLM dengan mode JSON
    response_data = llm_json(final_prompt)

    # Fallback jika error/gagal parse
    if "error" in response_data:
        # Gunakan mode teks biasa sebagai cadangan
        fallback_reply = llm_text(conversation_history + "\nUSER: " + user_text)
        return {
            "reply_text": fallback_reply,
            "ready": False,
            "income": st.session_state["detected_income"],
        }

    # Ambil hasil analisis AI
    reply_text = response_data.get("reply_text", "Maaf, bisa ulangi?")
    is_ready = response_data.get("is_info_complete", False)

    # 3. Update State Income (tetap kita coba detect manual buat jaga-jaga)
    if st.session_state["detected_income"] is None:
        detected_inc = try_detect_income(user_text)  # Fungsi regex lama
        if detected_inc:
            st.session_state["detected_income"] = detected_inc

    # 4. Update Ready State HANYA jika AI bilang True DAN Income terdeteksi
    # (Double check biar ga null pointer exception)
    if is_ready and st.session_state["detected_income"] is not None:
        st.session_state["ai_ready_for_baseline"] = True

        # Sekalian detect preferensi final
        full_text_log = "\n".join([m["content"] for m in st.session_state["messages"]])
        st.session_state["detected_prefs"] = interpret_preferences(full_text_log)

    return {
        "reply_text": reply_text,
        "ready": st.session_state["ai_ready_for_baseline"],
        "income": st.session_state["detected_income"],
    }


# ============================================================
# PART 3 — BASELINE BUILDER & BASELINE MODE
# ============================================================

from budget_optimizer.config import MINIMUMS, CATEGORIES


# ------------------------------------------------------------
# CONVERT PREFERENCES → BASELINE
# ------------------------------------------------------------
def prefs_to_baseline(pref_map: dict, income: int, minimums: dict) -> dict:
    """
    Mengubah preferensi:
        minimal / pas / maksimal
    menjadi baseline angka.

    Rumus:
        baseline = min_value * scaling
    """

    LEVEL = {
        "minimal": 1.0,
        "pas": 1.4,
        "maksimal": 1.9,
    }

    baseline = {}
    total = 0

    for cat in CATEGORIES:
        base = minimums.get(cat, 0)
        pref = pref_map.get(cat, "pas")

        scale = LEVEL.get(pref, 1.4)
        value = int(base * scale)

        baseline[cat] = value
        total += value

    # Overshoot handling — scale down proportional
    if total > income:
        ratio = income / total
        for c in baseline:
            baseline[c] = int(baseline[c] * ratio)

    # Ensure minimums
    for c in baseline:
        baseline[c] = max(baseline[c], minimums.get(c, 0))

    return baseline


# ------------------------------------------------------------
# SCALE DOWN BASELINE (utility)
# ------------------------------------------------------------
def scale_down_to_income(baseline, income):
    total = sum(baseline.values())

    if total <= income:
        return baseline

    factor = income / total
    return {k: int(v * factor) for k, v in baseline.items()}


# ------------------------------------------------------------
# BASELINE MODE UI
# ------------------------------------------------------------
def show_baseline_mode():
    """Menampilkan baseline rekomendasi dari Gen-AI."""
    st.subheader("🎯 Rekomendasi Baseline dari Gen-AI")
    st.info("Gen-AI sudah mengumpulkan semuanya. Ini baseline-mu!")

    income = st.session_state["detected_income"]
    prefs = st.session_state["detected_prefs"]

    # --- Guard Clauses (Income & Prefs Check) ---
    if income is None:
        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": "🙏 Aku belum nemu informasi income kamu. Coba tulis contohnya: `penghasilan 2.5 juta`",
            }
        )
        st.session_state["ai_ready_for_baseline"] = False
        st.rerun()
        return

    if prefs is None or not isinstance(prefs, dict):
        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": "😅 Aku belum paham preferensi gaya hidupmu. Tulis lagi misalnya:\n`gue anak kos, makan mau enak tapi jajan hemat`",
            }
        )
        st.session_state["ai_ready_for_baseline"] = False
        st.rerun()
        return

    # --- Build Baseline ---
    # Kita cek dulu apakah baseline sudah ada di session biar tidak berubah-ubah saat slider digeser
    if st.session_state["baseline"] is None:

        # IMPORT FUNGSI BARU DI SINI
        from budget_optimizer.genai.preference_ai import generate_smart_baseline

        # Ambil teks chat history user untuk dianalisis
        user_history_text = "\n".join(
            [m["content"] for m in st.session_state["messages"] if m["role"] == "user"]
        )

        with st.spinner("Sedang menghitung baseline berdasarkan angkamu..."):
            # Panggil fungsi Smart Baseline yang baru
            baseline = generate_smart_baseline(user_history_text, income)

        st.session_state["baseline"] = baseline

    baseline = st.session_state["baseline"]

    # Tampilkan Baseline Awal
    st.write("### 💵 Baseline Awal (Sebelum Optimasi)")
    st.json(baseline)

    st.markdown("---")

    # ============================================================
    # 🔥 FITUR BARU: SLIDER TARGET TABUNGAN
    # ============================================================
    st.subheader("🎯 Tentukan Target Tabungan")

    # Batas maksimal slider (misal 80% dari income agar logis)
    max_saving_limit = int(income * 0.8)

    # Ambil nilai default dari session state jika ada, atau 0
    default_value = st.session_state.get("target_tabungan", 0)

    # 1. Widget Slider
    target_user = st.slider(
        label="Geser untuk set target tabungan kamu bulan ini:",
        min_value=0,
        max_value=max_saving_limit,
        value=default_value,
        step=50000,  # Kelipatan 50rb biar enak
        format="Rp %d",  # Format tampilan angka
    )

    # 2. Update Session State secara realtime
    st.session_state["target_tabungan"] = target_user

    # 3. Feedback Visual (Persentase)
    pct_saving = (target_user / income) * 100
    st.caption(
        f"Target ini setara dengan **{pct_saving:.1f}%** dari total income kamu."
    )

    if pct_saving > 50:
        st.warning(
            "⚠️ Target di atas 50% mungkin bikin dompet 'sesak'. Pastikan kamu sanggup ya!"
        )

    st.markdown("---")

    # ============================================================
    # TOMBOL RUN SOLVER
    # ============================================================
    if st.button("Run Solver"):
        if st.session_state.get("baseline") is None:
            st.error("⚠️ Data baseline belum lengkap!")
        else:
            from budget_optimizer.genai.ai_router import AIRouter

            # HAPUS baris import MINIMUMS di sini agar tidak konflik scope
            # from budget_optimizer.config import MINIMUMS  <-- INI PENYEBAB ERRORNYA

            router = AIRouter()
            baseline_data = st.session_state["baseline"]

            income_val = st.session_state["detected_income"]
            target_val = st.session_state["target_tabungan"]
            delta_val = st.session_state.get("delta", 50000)

            with st.spinner(
                f"Mencari cara menabung Rp {target_val:,} tanpa menyiksa..."
            ):
                result = router.solve(
                    state=baseline_data,
                    income=income_val,
                    minimums=MINIMUMS,  # Menggunakan global variable
                    target=target_val,
                    delta=delta_val,
                )

            # Simpan hasil
            st.session_state.final_budget = result.get("final_state")
            st.session_state.solver_trace = result.get("trace")
            st.session_state.solver_constraints = MINIMUMS
            st.session_state["solver_output"] = {
                "result": result,
                "final_state": result.get("final_state"),
            }

            st.success("Solver selesai dijalankan!")
            st.rerun()


# Bagian tampilan panel ini tetap di luar "if st.button" agar tetap muncul setelah rerun
# if st.session_state.get("final_budget") is not None:
#     with st.expander("🧮 Solver Panel", expanded=True):

#         st.subheader("Final Budget")
#         st.json(st.session_state.final_budget)

#         st.subheader("Trace")
#         st.json(st.session_state.solver_trace)

#         st.subheader("Constraints")
#         st.json(st.session_state.solver_constraints)

# ================================
# 🔍 VISUALIZER PANEL (NEW PATCH)
# ================================
if st.session_state.get("final_budget") is not None:

    st.markdown("## 📊 Hasil Optimasi Anggaran")

    final_state = st.session_state.final_budget
    trace = st.session_state.get("solver_trace", [])
    constraints = st.session_state.get("solver_constraints", {})

    # -------------------------------
    # 1. Final Budget Table
    # -------------------------------
    st.subheader("💰 Final Budget Result")
    st.dataframe(
        {
            "Kategori": list(final_state.keys()),
            "Jumlah (Rp)": list(final_state.values()),
        }
    )

    # -------------------------------
    # 2. Constraints
    # -------------------------------
    # st.subheader("📏 Constraints yang Digunakan")
    # st.json(constraints)

    # -------------------------------
    # 3. Solver Trace (Jika ada)
    # -------------------------------
    # if trace:
    #     st.subheader("🧮 Solver Trace / Jalur Optimasi")
    #     st.json(trace)

    # -------------------------------
    # 4. Visual Summary (Chart)
    # -------------------------------
# ================================
# 📊 VISUALIZATION PANEL (COMPLETE)
# ================================
if (
    st.session_state.get("final_budget") is not None
    and st.session_state.get("baseline") is not None
):

    st.markdown("## 📊 Visualization Panel")

    baseline_state = st.session_state["baseline"]
    final_state = st.session_state["final_budget"]

    import plotly.express as px
    import pandas as pd

    st.subheader("🥧 Final Budget Distribution (Interactive)")

    # Siapkan data dalam bentuk DataFrame agar lebih rapi
    df_chart = pd.DataFrame(
        {"Kategori": list(final_state.keys()), "Jumlah": list(final_state.values())}
    )

    # Hapus kategori yang nilainya 0 agar chart tidak penuh label kosong
    df_chart = df_chart[df_chart["Jumlah"] > 0]

    # Buat Donut Chart yang modern
    fig_pie = px.pie(
        df_chart,
        values="Jumlah",
        names="Kategori",
        hole=0.4,  # Membuat lubang di tengah (Donut Chart)
        color_discrete_sequence=px.colors.qualitative.Pastel,  # Palet warna pastel yang lembut
        title="Alokasi Anggaran Final",
    )

    # Kustomisasi tampilan: Tampilkan persentase dan label di dalam slice
    fig_pie.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hoverinfo="label+percent+value",  # Tooltip interaktif saat di-hover
    )

    # Rapikan layout
    fig_pie.update_layout(
        showlegend=False,  # Sembunyikan legenda agar lebih bersih
        margin=dict(t=40, b=0, l=0, r=0),  # Kurangi margin kosong
    )

    # Tampilkan chart di Streamlit dengan lebar penuh
    st.plotly_chart(fig_pie, use_container_width=True)

# ================================
# 🤝 ADVISOR PANEL (AI Suggestions) — FULL PACKAGE
# ================================
if (
    st.session_state.get("final_budget") is not None
    and st.session_state.get("baseline") is not None
    and st.session_state.get("detected_prefs") is not None
):
    st.markdown("## 🤝 Advisor Panel — AI Generated Insights")

    baseline = st.session_state["baseline"]
    final_state = st.session_state["final_budget"]
    prefs = st.session_state["detected_prefs"]
    income = st.session_state.get("detected_income", 0)
    target_saving = st.session_state.get("target_tabungan", 0)

    # Gabungkan state untuk AI Advisor
    state_for_ai = {
        "baseline": baseline,
        "final_budget": final_state,
        "income": income,
    }

    from budget_optimizer.genai.advisor import generate_advice

    with st.spinner("AI sedang membaca kondisi finansialmu..."):
        advice = generate_advice(
            state=state_for_ai, prefs=prefs, target_saving=target_saving
        )

    # -----------------------------------------
    # 1. Summary (Natural Text, Fun Tone)
    # -----------------------------------------
    st.subheader("💡 Advice Summary")
    st.write(advice.get("summary", "Tidak ada ringkasan."))

    # -----------------------------------------
    # 2. Priority Suggestions (Clean Bullets)
    # -----------------------------------------
    priorities = advice.get("priority_suggestion", [])
    if priorities:
        st.subheader("🔥 Priority Suggestions")
        for p in priorities:
            st.write(f"- {p}")

    # -----------------------------------------
    # 3. Saving Tips
    # -----------------------------------------
    saving = advice.get("saving_tips", [])
    if saving:
        st.subheader("💰 Saving Tips")
        for s in saving:
            st.write(f"- {s}")

    # -----------------------------------------
    # 4. Risk Notes
    # -----------------------------------------
    risks = advice.get("risk_notes", [])
    if risks:
        st.subheader("⚠️ Potential Risks")
        for r in risks:
            st.write(f"- {r}")

    # ============================================================
    # 🔍 ADVANCED ANALYTICS — Full Financial Insight Layer
    # ============================================================

    st.markdown("---")
    st.markdown("## 📘 Deep Financial Insights")

    # -----------------------------------------
    # DAILY BURN RATE
    # -----------------------------------------
    st.subheader("⏳ Daily Burn Rate (Perkiraan Pengeluaran Harian)")

    if income > 0:
        daily = income / 30
        st.write(f"Perkiraan batas aman pengeluaran harian kamu: **Rp {daily:,.0f}**")
    else:
        st.write("Income tidak terdeteksi, tidak bisa hitung burn rate.")

    # -----------------------------------------
    # CATEGORY-LEVEL INSIGHTS
    # -----------------------------------------
    st.subheader("📊 Category Breakdown Insights")

    total_final = sum(final_state.values())
    percentages = {
        k: (v / total_final * 100 if total_final > 0 else 0)
        for k, v in final_state.items()
    }

    st.write("### Persentase tiap kategori")
    st.json(percentages)

    # --- Detect dangerously high categories ---
    st.write("### Deteksi Pengeluaran Berisiko Tinggi")
    risky = [(k, p) for k, p in percentages.items() if p > 40]

    if risky:
        st.error("⚠️ Ada kategori yang memakan lebih dari 40%!")
        for k, p in risky:
            st.write(f"- **{k}**: {p:.1f}% dari total budget")
    else:
        st.success("Tidak ada kategori yang terlalu mendominasi 🎉")

    # -----------------------------------------
    # SAVING PROJECTION (Monthly → 12 Months)
    # -----------------------------------------
    st.subheader("📈 Saving Projection (12 Bulan)")

    # Gunakan huruf kecil "tabungan" sesuai config.py
    if "tabungan" in final_state:
        monthly = final_state["tabungan"]
        yearly = monthly * 12
        st.write(f"- Tabungan per bulan: **Rp {monthly:,.0f}**")
        st.write(f"- Jika konsisten selama 1 tahun: **Rp {yearly:,.0f}**")
    else:
        st.info("Kategori Tabungan tidak ditemukan.")

    # -----------------------------------------
    # SMART REBALANCING SUGGESTIONS
    # -----------------------------------------
    st.subheader("🔄 Smart Rebalancing (AI Auto-Analysis)")

    improvements = []

    # Makan terlalu besar?
    if percentages.get("Makan", 0) > 35:
        improvements.append(
            "Kategori **Makan** terlalu besar. Pertimbangkan meal-prep atau kombinasikan masak sendiri untuk tekan biaya."
        )

    # Transport terlalu besar?
    if percentages.get("Transport", 0) > 25:
        improvements.append(
            "Transport memakan porsi besar. Bisa coba langganan bulanan, jalan kaki jarak dekat, atau sharing cost."
        )

    # Hiburan check
    if percentages.get("Hiburan", 0) > 20:
        improvements.append(
            "Hiburan agak tinggi. Coba pakai budget cap mingguan atau aktivitas low-cost bareng teman."
        )

    if improvements:
        for x in improvements:
            st.write(f"- {x}")
    else:
        st.success("Struktur anggaranmu sudah optimal banget 🎯")

# ================================
# 🌟 ADVISOR PANEL — PART 2
# Advanced Visuals & Behavioral Insights
# ================================
if (
    st.session_state.get("final_budget") is not None
    and st.session_state.get("baseline") is not None
    and st.session_state.get("detected_prefs") is not None
):
    st.markdown("---")
    st.markdown("## 🌟 Deep Behavioral & Visual Insights")

    baseline = st.session_state["baseline"]
    final_state = st.session_state["final_budget"]
    income = st.session_state.get("detected_income", 0)

    import matplotlib.pyplot as plt
    import numpy as np

    # ============================================================
    # 1. FINANCIAL HEALTH SCORE (0–100)
    # ============================================================
    st.subheader("💚 Financial Health Score")

    total_final = sum(final_state.values())
    tabungan = final_state.get("tabungan", 0)
    makan = final_state.get("makan", 0)
    hiburan = final_state.get("hiburan", 0)

    score = 0
    # Tabungan
    if tabungan >= income * 0.15:
        score += 40
    elif tabungan >= income * 0.10:
        score += 30
    else:
        score += 10

    # Beban makan
    if makan <= income * 0.30:
        score += 30
    else:
        score += 10

    # Hiburan
    if hiburan <= income * 0.15:
        score += 20
    else:
        score += 10

    # Cadangan / keseimbangan
    structure_ok = all(v > 0 for v in final_state.values())
    score += 10 if structure_ok else 0

    st.metric("Skor Kesehatan Finansial", f"{score}/100")

    # ============================================================
    # 2. FINANCIAL RADAR CHART
    # ============================================================
    st.subheader("🕸 Financial Radar Chart (Balanced Structure)")

    # Siapkan data untuk Plotly
    categories = list(final_state.keys())
    values = list(final_state.values())

    df_radar = pd.DataFrame({"Kategori": categories, "Jumlah": values})

    # Buat Radar Chart interaktif
    fig_radar = px.line_polar(
        df_radar,
        r="Jumlah",
        theta="Kategori",
        line_close=True,  # Menutup garis loop (jaring laba-laba)
        title="Peta Keseimbangan Anggaran",
    )

    # Styling: Isi area dalam (fill), warna modern
    fig_radar.update_traces(fill="toself", line_color="#00CC96")

    # Layout cleaning
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=False,  # Sembunyikan angka sumbu agar tidak ruwet
            )
        ),
        margin=dict(t=40, b=20, l=40, r=40),
    )

    st.plotly_chart(fig_radar, use_container_width=True)
    # ============================================================
    # 3. SPENDING CONSISTENCY GAUGE
    # ============================================================
    st.subheader("🎯 Spending Consistency Gauge")

    diffs = []
    for c in final_state:
        before = baseline[c]
        after = final_state[c]
        change = abs(after - before) / max(before, 1)
        diffs.append(change)

    consistency = 100 - min(100, sum(diffs) / len(diffs) * 100)

    st.metric("Konsistensi anggaran sebelum → sesudah", f"{consistency:.1f}%")

    # ============================================================
    # 4. DAILY–WEEKLY–MONTHLY OPTIMAL SPENDING MODEL
    # ============================================================
    st.subheader("📅 Optimal Spending Model (Daily / Weekly / Monthly)")

    daily_limit = income / 30
    weekly_limit = income / 4

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Daily Safe Limit", f"Rp {daily_limit:,.0f}")
    with col2:
        st.metric("Weekly Safe Limit", f"Rp {weekly_limit:,.0f}")
    with col3:
        st.metric("Monthly Income", f"Rp {income:,.0f}")

    # ============================================================
    # 5. MICRO-HABIT SUGGESTIONS (AI-like deterministic)
    # ============================================================
    st.subheader("🌱 Micro Habit Suggestions (Mudah Dilakukan Harian)")

    habits = []

    if tabungan < income * 0.10:
        habits.append("Set auto-transfer tabungan Rp 10.000 setiap pagi.")
    habits.append("Catat 3 pengeluaran terbesar harian, untuk lihat pola boros.")
    if makan > income * 0.30:
        habits.append("Masak 2× seminggu untuk hemat biaya makan.")
    if hiburan > income * 0.15:
        habits.append("Buat 'No Spend Day' sekali seminggu.")
    habits.append(
        "Gunakan dompet terpisah: sehari maksimal Rp 20.000 untuk jajan kecil."
    )

    for h in habits:
        st.write(f"- {h}")

    # ============================================================
    # 6. HIGH-IMPACT IMPROVEMENTS (Prioritization Engine)
    # ============================================================
    st.subheader("🚀 High Impact Improvements")

    impacts = []

    # Jika tabungan kecil
    if tabungan < income * 0.10:
        impacts.append("Tingkatkan tabungan minimal ke 10% income untuk safety net.")

    # Jika makan tinggi
    if makan > income * 0.35:
        impacts.append("Turunkan budget makan 5–10% lewat meal-prep / masak rutin.")

    # Jika hiburan terlalu besar
    if hiburan > income * 0.20:
        impacts.append("Buat batas hiburan mingguan dan pakai aplikasi pengingat.")

    # Jika tidak ada masalah
    if not impacts:
        st.success("Strukturnya sudah optimal! Tinggal dipertahankan 🎉")
    else:
        for x in impacts:
            st.write(f"- {x}")


# =====================================================
# 📘 EVALUATOR PANEL  —  Budget Health & Suggestions
# =====================================================
def show_evaluator_panel():

    if st.session_state.get("final_budget") is None:
        return  # tidak ada hasil, panel tidak muncul

    st.markdown("## 🩺 Evaluasi Kesehatan Anggaran")

    final = st.session_state.final_budget

    total_budget = sum(final.values())

    # ----------------------------------------
    # 1. Persentase tiap kategori
    # ----------------------------------------
    percentages = {
        k: (v / total_budget) * 100 if total_budget > 0 else 0 for k, v in final.items()
    }

    st.subheader("📐 Persentase Setiap Kategori")
    st.json(percentages)

    # ----------------------------------------
    # 2. Deteksi kategori 'boros'
    # ----------------------------------------
    overspend = [
        (k, p)
        for k, p in percentages.items()
        if p > 40  # threshold sederhana → customizable
    ]

    if overspend:
        st.error("⚠️ Kategori Boros Terdeteksi!")
        for k, p in overspend:
            st.write(f"- **{k}** menggunakan **{p:.1f}%** dari total anggaran")
    else:
        st.success("Tidak ada kategori boros 🎉")

    # ----------------------------------------
    # 3. Rekomendasi otomatis
    # ----------------------------------------
    st.subheader("💡 Rekomendasi Optimasi Lanjutan")

    recs = []

    if "Tabungan" in percentages and percentages["Tabungan"] < 10:
        recs.append("Tingkatkan alokasi tabungan minimal 10%.")

    if overspend:
        for k, p in overspend:
            recs.append(f"Kurangi pengeluaran di kategori **{k}** hingga di bawah 35%.")

    if not recs:
        st.success("Anggaran sudah sangat baik dan seimbang! 🎯")
    else:
        for r in recs:
            st.write(f"- {r}")


# ============================================================
# PART 6 — FINAL RESULT PANEL + VALIDATION LAYER
# ============================================================


def show_final_result(result: dict):
    """
    Menampilkan ringkasan solver output:
    - final_state
    - trace fallback chain
    - method used
    - status
    - validation notes
    """

    # ===========================
    # BASIC ERROR HANDLING
    # ===========================
    if result is None or "result" not in result:
        st.error("⚠️ Output solver kosong. Coba ulang ya.")
        return

    result_core = result["result"]

    if "final_state" not in result_core:
        st.error("❗ Solver gagal menghasilkan final_state.")
        return

    final_state = result_core["final_state"]
    method = result_core.get("method", "Unknown")
    status = result_core.get("status", "Unknown")
    trace = result_core.get("trace", [])

    st.subheader("🎯 Final Result")

    # ===========================
    # VALIDATION LAYER
    # ===========================
    from budget_optimizer.config import CATEGORIES

    # 1) Negative numbers
    neg = [k for k, v in final_state.items() if v < 0]
    if neg:
        st.error(f"🚨 Bug terdeteksi: nilai negatif pada kategori {neg}.")
        return

    # 2) Missing categories
    missing = [c for c in CATEGORIES if c not in final_state]
    if missing:
        st.error(f"⚠️ Final state tidak lengkap. Kategori hilang: {missing}.")
        return

    # ===========================
    # DISPLAY HEADER
    # ===========================
    st.markdown(f"**Method Used:** `{method}`")
    st.markdown(f"**Status:** `{status}`")

    # ===========================
    # FINAL STATE
    # ===========================
    st.markdown("### 💵 Final Allocated Budget")
    st.json(final_state)

    # ===========================
    # TRACE (A* / Greedy / SA / LLM)
    # ===========================
    st.markdown("### 🔍 Solver Pipeline Trace")
    if trace:
        for step in trace:
            st.markdown(f"- **{step.get('method')}** → `{step.get('status')}`")
    else:
        st.info("Trace tidak tersedia.")

    # ===========================
    # CONSTRAINT VALIDATION
    # ===========================
    st.markdown("### ✅ Constraint Check")

    notes = []
    income = result_core.get("income", None)
    minimums = result_core.get("minimums", MINIMUMS)

    if income:
        total = sum(final_state.values())
        if total <= income:
            notes.append("🟢 Total spending tidak melebihi income.")
        else:
            notes.append("🔴 Total spending melebihi income.")

    for cat, minv in minimums.items():
        if final_state.get(cat, 0) >= minv:
            notes.append(f"🟢 {cat} memenuhi minimum.")
        else:
            notes.append(f"🔴 {cat} di bawah minimum.")

    for n in notes:
        st.write(n)


# ============================================================
# PART 7 — MAIN CHAT LOOP (Chat Mode)
# ============================================================
st.header("💬 Chat dengan AI Budget Assistant")

# 1) Render chat history
render_chat()

# 2) Chat input
user_input = st.chat_input("Tulis pesan kamu di sini...")

if user_input:
    # Simpan pesan user
    st.session_state["messages"].append({"role": "user", "content": user_input})

    # A. Jika AI belum siap data (Income/Prefs belum lengkap)
    if not st.session_state["ai_ready_for_baseline"]:
        ai_output = ask_ai_until_ready(user_input)

        with st.chat_message("assistant"):
            st.write(ai_output["reply_text"])

        st.session_state["messages"].append(
            {"role": "assistant", "content": ai_output["reply_text"]}
        )

        # Jika baru saja siap, reload agar status berubah
        if ai_output["ready"]:
            st.rerun()

# --- LOGIKA TAMPILAN UTAMA (Di luar blok if user_input agar tetap muncul saat rerun) ---

# 1. Jika belum siap apa-apa -> Jangan lakukan apa-apa (tunggu chat)
if not st.session_state["ai_ready_for_baseline"]:
    pass

# 2. Jika Solver SUDAH ada hasilnya -> Tampilkan Hasil
elif st.session_state.get("solver_output") is not None:
    # Opsional: Pesan transisi
    # with st.chat_message("assistant"):
    #    st.write("Berikut hasil optimasinya 👇")
    show_final_result(st.session_state["solver_output"])

# 3. Jika Baseline SUDAH ada tapi Solver BELUM ada -> Tampilkan Slider & Tombol
#    (Ini perbaikan utamanya: Kita panggil show_baseline_mode, BUKAN auto-run solver)
elif st.session_state.get("ai_ready_for_baseline"):
    show_baseline_mode()
