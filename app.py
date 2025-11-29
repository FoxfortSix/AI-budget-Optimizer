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
    st.session_state["target_tabungan"] = 300000

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
            return n * 1_000_000 # Asumsi "gaji 5" = 5 juta
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


# ------------------------------------------------------------
# ASK_AI_UNTIL_READY — bagian terpenting S3 Chat Engine
# ------------------------------------------------------------
def ask_ai_until_ready(user_text: str) -> Dict[str, Any]:
    reply = ai_chat(user_text)

    # Step 1 — Detect income if not yet
    if st.session_state["detected_income"] is None:
        detected = try_detect_income(user_text)
        if detected:
            st.session_state["detected_income"] = detected

    # Step 2 — Detect preferences
    if st.session_state["detected_prefs"] is None:
        full_text = "\n".join(
            m["content"] for m in st.session_state["messages"] if m["role"] == "user"
        )
        st.session_state["detected_prefs"] = interpret_preferences(full_text)

    # 🔥 Step 3 — NEW: Ready condition
    if (
        st.session_state["detected_income"] is not None
        and st.session_state["detected_prefs"] is not None
    ):
        st.session_state["ai_ready_for_baseline"] = True

    # Output
    return {
        "reply_text": reply,
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

    # -------------------------------------------
    # Guard 1 — income missing
    # -------------------------------------------
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

    # -------------------------------------------
    # Guard 2 — prefs missing
    # -------------------------------------------
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

    # -------------------------------------------
    # Build baseline
    # -------------------------------------------
    baseline = prefs_to_baseline(prefs, income, MINIMUMS)

    st.write("### 💵 Baseline Awal")
    st.json(baseline)

    if sum(baseline.values()) > income:
        st.warning("⚠️ Baseline melebihi income. Aku auto-scale agar feasible.")
        baseline = scale_down_to_income(baseline, income)

    # Save baseline to session
    st.session_state["baseline"] = baseline

    st.write("### 💵 Baseline (Sudah di-scale)")
    st.json(baseline)


# Button → go to solver
if st.button("Run Solver"):
    # --- PERBAIKAN DI SINI: Cek dulu apakah baseline sudah ada ---
    if st.session_state.get("baseline") is None:
        st.error("⚠️ Data baseline belum lengkap! Silakan chat dengan AI dulu sampai tabel baseline muncul.")
    else:
        # Jika baseline sudah ada, baru jalankan logika solver
        
        # 1. Import dari path yang benar
        from budget_optimizer.genai.ai_router import AIRouter
        from budget_optimizer.config import MINIMUMS

        router = AIRouter()

        # 2. Siapkan data
        baseline_data = st.session_state["baseline"]
        income_val = st.session_state["detected_income"]
        target_val = st.session_state.get("target_tabungan", 0)
        delta_val = st.session_state.get("delta", 50000)

        with st.spinner("Sedang mencari solusi anggaran terbaik..."):
            result = router.solve(
                state=baseline_data,
                income=income_val,
                minimums=MINIMUMS,
                target=target_val,
                delta=delta_val,
            )

        # 3. Simpan hasil ke session state
        st.session_state.final_budget = result.get("final_state")
        st.session_state.solver_trace = result.get("trace")
        st.session_state.solver_constraints = MINIMUMS

        # Simpan juga ke solver_output agar kompatibel dengan logika main loop
        st.session_state["solver_output"] = {
            "result": result,
            "final_state": result.get("final_state"),
        }

        st.success("Solver selesai dijalankan!")
        st.rerun()  # Refresh agar UI berpindah ke tampilan hasil

# Bagian tampilan panel ini tetap di luar "if st.button" agar tetap muncul setelah rerun
if st.session_state.get("final_budget") is not None:
    with st.expander("🧮 Solver Panel", expanded=True):

        st.subheader("Final Budget")
        st.json(st.session_state.final_budget)

        st.subheader("Trace")
        st.json(st.session_state.solver_trace)

        st.subheader("Constraints")
        st.json(st.session_state.solver_constraints)

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
    st.subheader("📏 Constraints yang Digunakan")
    st.json(constraints)

    # -------------------------------
    # 3. Solver Trace (Jika ada)
    # -------------------------------
    if trace:
        st.subheader("🧮 Solver Trace / Jalur Optimasi")
        st.json(trace)

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

    import matplotlib.pyplot as plt

    # -------------------------------
    # 1. BASELINE PIE CHART
    # -------------------------------
    st.subheader("🥧 Baseline Pie Chart")

    fig1, ax1 = plt.subplots(figsize=(6, 6))
    ax1.pie(baseline_state.values(), labels=baseline_state.keys(), autopct="%1.1f%%")
    ax1.set_title("Baseline Budget Distribution")
    st.pyplot(fig1)

    # -------------------------------
    # 2. FINAL PIE CHART
    # -------------------------------
    st.subheader("🥧 Final Budget Pie Chart")

    fig2, ax2 = plt.subplots(figsize=(6, 6))
    ax2.pie(final_state.values(), labels=final_state.keys(), autopct="%1.1f%%")
    ax2.set_title("Optimized Final Budget Distribution")
    st.pyplot(fig2)

    # -------------------------------
    # 3. BEFORE-AFTER COMPARISON BAR CHART
    # -------------------------------
    st.subheader("📈 Before vs After Budget Comparison")

    categories = list(baseline_state.keys())
    before = [baseline_state[c] for c in categories]
    after = [final_state[c] for c in categories]

    x = range(len(categories))

    fig3, ax3 = plt.subplots(figsize=(10, 5))
    ax3.bar(x, before, width=0.4, label="Baseline")
    ax3.bar([i + 0.4 for i in x], after, width=0.4, label="Final")

    ax3.set_xticks([i + 0.2 for i in x])
    ax3.set_xticklabels(categories, rotation=45)
    ax3.set_ylabel("Amount (Rp)")
    ax3.set_title("Before vs After — Budget Comparison")
    ax3.legend()

    st.pyplot(fig3)

# ================================
# 🤝 ADVISOR PANEL (AI Suggestions)
# ================================
if (
    st.session_state.get("final_budget") is not None
    and st.session_state.get("baseline") is not None
    and st.session_state.get("detected_prefs") is not None
):

    st.markdown("## 🤝 Advisor Panel — AI Generated Suggestions")

    from budget_optimizer.genai.advisor import generate_advice

    baseline = st.session_state["baseline"]
    final_state = st.session_state["final_budget"]
    prefs = st.session_state["detected_prefs"]
    target_saving = st.session_state.get("target_tabungan", 0)

    # Gabungkan state untuk diberikan ke AI Advisor
    state_for_ai = {
        "baseline": baseline,
        "final_budget": final_state,
        "income": st.session_state.get("detected_income", 0),
    }

    with st.spinner("AI sedang menganalisis kondisi keuanganmu..."):
        advice = generate_advice(
            state=state_for_ai, prefs=prefs, target_saving=target_saving
        )

    # -------------------------------
    # Tampilkan Advice Summary
    # -------------------------------
    st.subheader("💡 Advice Summary")
    st.write(advice.get("summary", ""))

    # -------------------------------
    # Priority Suggestions (bullet)
    # -------------------------------
    priorities = advice.get("priority_suggestion", [])
    if priorities:
        st.subheader("🔥 Priority Suggestions")
        for item in priorities:
            st.write(f"- {item}")

    # -------------------------------
    # Saving Tips (bullet)
    # -------------------------------
    saving = advice.get("saving_tips", [])
    if saving:
        st.subheader("💰 Saving Tips")
        for tip in saving:
            st.write(f"- {tip}")

    # -------------------------------
    # Risk Notes (bullet)
    # -------------------------------
    risks = advice.get("risk_notes", [])
    if risks:
        st.subheader("⚠️ Potential Risks")
        for r in risks:
            st.write(f"- {r}")


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
# PART 4 — SOLVER PIPELINE CONNECTOR
# ============================================================


def run_solver_pipeline(baseline_dict, income, minimums, target_tabungan, delta):
    """
    Proses lengkap dari baseline → normalized → AI Router → final state.
    """
    from budget_optimizer.models import State
    from budget_optimizer.utils import normalize_state
    from budget_optimizer.genai.ai_router import AIRouter

    # ---------------------------------------
    # 1. Baseline → State object
    # ---------------------------------------
    state = State(**baseline_dict)

    # ---------------------------------------
    # 2. Normalize (urang memastikan sum <= income)
    # ---------------------------------------
    normalized = normalize_state(state, income)

    # ---------------------------------------
    # 3. Run solver chain through AIRouter
    # ---------------------------------------
    router = AIRouter()
    result = router.solve(
        state=normalized.to_dict(),
        income=income,
        minimums=minimums,
        target=target_tabungan,
        delta=delta,
    )

    # Return dict for display layer
    return {
        "normalized": normalized.to_dict(),
        "result": result,
        "income": income,
        "minimums": minimums,
    }


# ============================================================
# PART 5 — APPLY BASELINE → RUN SOLVER
# ============================================================

st.subheader("⚙️ Terapkan Baseline ke Optimization Engine")

# Tombol untuk menjalankan solver setelah baseline dibuat
if st.button("🚀 Jalankan Optimasi"):
    # --- PERBAIKAN: Cek apakah nilainya None, bukan cuma cek key-nya ---
    if st.session_state.get("baseline") is None:
        st.warning("❗ Baseline AI belum tersedia. Lanjut chat dulu sampai tabel baseline muncul ya!")
    elif st.session_state.get("detected_income") is None:
        st.warning("❗ Income belum terdeteksi. Pastikan Anda menyebutkan penghasilan saat chat.")
    else:
        with st.spinner("Menjalankan solver..."):
            # Pastikan mengambil nilai default jika target/delta belum ada
            tgt = st.session_state.get("target_tabungan", 0)
            dlt = st.session_state.get("delta", 50000)
            
            pipe = run_solver_pipeline(
                baseline_dict=st.session_state["baseline"],
                income=st.session_state["detected_income"],
                minimums=MINIMUMS,
                target_tabungan=tgt,
                delta=dlt,
            )
            
        st.session_state["solver_output"] = pipe
        st.success("🎉 Optimasi selesai!")
        
        # Tampilkan hasil JSON pipeline
        st.json(pipe)

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

    # Jika kita belum siap baseline, terus tanya AI
    if not st.session_state["ai_ready_for_baseline"]:
        ai_output = ask_ai_until_ready(user_input)

        # Tampilkan balasan AI
        with st.chat_message("assistant"):
            st.write(ai_output["reply_text"])

        st.session_state["messages"].append(
            {"role": "assistant", "content": ai_output["reply_text"]}
        )

        # Jika setelah pesan ini kita siap baseline → render baseline mode
        if ai_output["ready"]:
            st.session_state["detected_prefs"] = interpret_preferences(
                "\n".join(
                    m["content"]
                    for m in st.session_state["messages"]
                    if m["role"] == "user"
                )
            )
            st.rerun()  # reload halaman dengan mode baseline aktif

    if (
        st.session_state["ai_ready_for_baseline"]
        and st.session_state["baseline"] is None
    ):
        show_baseline_mode()
        st.stop()

    # Jika siap baseline tapi baseline belum dibangun → masuk baseline mode
    elif st.session_state["baseline"] is None:
        show_baseline_mode()
        st.stop()

    if (
        st.session_state["ai_ready_for_baseline"]
        and st.session_state["baseline"] is None
    ):
        show_baseline_mode()
        st.stop()

    # Jika baseline sudah ada tapi solver belum jalan
    elif st.session_state["solver_output"] is None:
        with st.spinner("Menjalankan solver..."):
            out = run_solver_pipeline(
                baseline_dict=st.session_state["baseline"],
                income=st.session_state["detected_income"],
                minimums=MINIMUMS,
                target_tabungan=st.session_state["target_tabungan"],
                delta=st.session_state["delta"],
            )
        st.session_state["solver_output"] = out

        with st.chat_message("assistant"):
            st.write("Oke! Solver selesai. Mau lihat hasilnya?")

    # Jika solver sudah ada → tampilkan
    else:
        with st.chat_message("assistant"):
            st.write("Berikut hasil optimasinya 👇")
        show_final_result(st.session_state["solver_output"])
