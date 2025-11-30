# budget_optimizer/config.py

CATEGORIES = [
    "kos",
    "makan",
    "transport",
    "internet",
    "jajan",
    "hiburan",
    "tabungan",
]

# Hard minimums (digunakan CSP + preference minimal)
MINIMUMS = {
    "kos": 0,
    "makan": 0,
    "transport": 10000,
    "internet": 5000,
    "tabungan": 0,
    "jajan": 0,
    "hiburan": 0,
}

# Psychological effort weight when moving money from category
BOBOT = {
    "kos": 3.0,
    "makan": 2.0,
    "transport": 1.5,
    "internet": 1.5,
    "jajan": 1.0,
    "hiburan": 1.2,
    "tabungan": 0.5,
}

# Reasonable maximum (for preference layer)
REASONABLE_MAX = {
    "kos": 1000000,
    "makan": 800000,
    "transport": 200000,
    "internet": 100000,
    "jajan": 400000,
    "hiburan": 300000,
    "tabungan": 500000,
}
