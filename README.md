# 💰 AI Budget Optimizer

**Asisten Keuangan Cerdas untuk Mahasiswa berbasis Constraint Satisfaction Problem (CSP) dan Pencarian Heuristik.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)
![AI](https://img.shields.io/badge/Gemini-Generative%20AI-orange)

## 📖 Deskripsi Proyek

**AI Budget Optimizer** adalah aplikasi manajemen keuangan cerdas yang dirancang khusus untuk membantu mahasiswa mengelola anggaran bulanan. Tidak seperti aplikasi pencatat keuangan biasa, sistem ini bertindak sebagai **agen rasional** yang mampu:

1.  **Memahami Bahasa Manusia:** Menerima input curhatan (misal: *"Gaji 3 juta, pengen makan enak tapi hemat transport"*) dan mengubahnya menjadi data numerik.
2.  **Memvalidasi Anggaran:** Menggunakan **Constraint Satisfaction Problem (CSP)** untuk memastikan rencana keuangan realistis dan memenuhi kebutuhan dasar.
3.  **Mencari Solusi Optimal:** Menggunakan algoritma pencarian **A* (A-Star)**, **Greedy**, dan **Simulated Annealing** untuk menyusun rencana penyesuaian anggaran otomatis.
4.  **Memberikan Saran Personal:** Menggunakan **Generative AI (Google Gemini)** untuk memberikan saran finansial yang santai, suportif, dan mudah dipahami.

Proyek ini dikembangkan untuk memenuhi Tugas Besar mata kuliah **Kecerdasan Buatan (Artificial Intelligence)** di Universitas Pendidikan Indonesia.

---

## 🚀 Fitur Utama

* **💬 Natural Language Input:** Input data cukup lewat *chat* santai, tidak perlu isi form angka yang rumit.
* **🤖 Hybrid AI Solver:**
    * **CSP:** Menjaga agar anggaran tidak melanggar batas minimum hidup.
    * **A* Search:** Mencari jalur optimal untuk mencapai target tabungan dengan "friksi psikologis" terkecil.
    * **Fallback Mechanism:** Otomatis beralih ke Greedy atau Simulated Annealing jika solusi A* tidak ditemukan.
* **📊 Visualisasi Data:** Grafik *Pie Chart* dan *Bar Chart* untuk membandingkan anggaran "Before vs After".
* **💡 AI Advisor:** Memberikan tips taktis dan strategis untuk berhemat tanpa menghakimi.

---

## 🛠️ Teknologi & Algoritma

* **Bahasa Pemrograman:** Python
* **Framework UI:** Streamlit
* **Generative AI:** Google Gemini API (via `google-generativeai`)
* **Algoritma Inti:**
    * Constraint Satisfaction Problem (CSP)
    * A* Search (Heuristic Search)
    * Greedy Best-First Search
    * Simulated Annealing (Local Search)

---

## 📂 Struktur Direktori

```
budget_optimizer/
│
├── app.py                   # Main entry point aplikasi Streamlit
├── config.py                # Konfigurasi konstanta (Minimums, Categories)
├── budget_solver.py         # Wrapper untuk Linear Programming (Opsional)
├── budget_visualizer.py     # Modul visualisasi (Matplotlib)
├── generator.py             # Generator target state
├── greedy.py                # Implementasi Algoritma Greedy
├── astar.py                 # Implementasi Algoritma A*
├── simulated_annealing.py   # Implementasi Algoritma Simulated Annealing
├── csp.py                   # Implementasi Constraint Satisfaction Problem
├── models.py                # Definisi dataclass (State, Action, Node)
├── preference.py            # Logika profil preferensi user
├── scaler.py                # Konversi preferensi ke angka
├── utils.py                 # Fungsi utilitas umum
├── __init__.py              # Penanda package Python
│
├── genai/                   # Modul integrasi Generative AI
│   ├── advisor.py           # Generate saran naratif
│   ├── ai_router.py         # Pengatur jalur solver (A* -> Greedy -> SA)
│   ├── fallback_solver.py   # Chain untuk fallback mechanism
│   ├── llm_client.py        # Client wrapper untuk Gemini API
│   ├── preference_ai.py     # NLP untuk ekstraksi preferensi
│   ├── rebalancer.py        # Logika penyeimbang target
│   └── validator.py         # Safety net & sanitasi hasil output
│
└── tests/                   # Unit testing
    └── test_csp.py
```
## ⚙️ Instalasi & Cara Menjalankan
1. Clone Repository
```
git clone [https://github.com/foxfortsix/ai-budget-optimizer.git](https://github.com/foxfortsix/ai-budget-optimizer.git)
cd ai-budget-optimizer
```
2. Buat Virtual Environment (Optional)
```
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```
3. Install Depedensi
```
pip install streamlit numpy scipy matplotlib requests
```
4. Konfigurasi API Key
```
GEMINI_API_KEY = "MASUKKAN_API_KEY_DISINI"
```
(Catatan: Anda bisa mendapatkan API Key di Google AI Studio)

5. Jalankan Aplikasi
```
python -m streamlit run app.py
```

## 🧪 Cara Penggunaan
1. Buka browser di alamat yang muncul (biasanya http://localhost:8501).
2. Pada kolom Chat, ceritakan kondisi keuangan Anda.
   Contoh: "Gaji saya 3 juta. Saya anak kos, pengen makan enak tapi jajan dikurangin biar bisa nabung."
3. AI akan memproses dan menampilkan Tabel Baseline (anggaran awal).
4. Jika data sudah benar, klik tombol "🚀 Jalankan Optimasi".
5. Tunggu sistem berpikir (menjalankan A*/Greedy/SA).
6. Lihat hasil Final Budget, Visualisasi, dan Saran AI.

