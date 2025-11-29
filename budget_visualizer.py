# budget_visualizer.py
# Visualization module for Baseline Pie, Final Pie, and Before-After Comparison

import matplotlib.pyplot as plt
from typing import Dict, Any


class BudgetVisualizer:
    """
    Generates:
    |— Visualization Panel
    |     |— Baseline Pie
    |     |— Final Pie
    |     |— Before-After Comparison (Bar Chart)

    Output: Matplotlib figures (can be rendered inside Streamlit or saved)
    """

    def __init__(self, solver_output: Dict[str, Any]):
        self.data = solver_output
        self.baseline = solver_output["solver_panel"]["trace"]["baseline"]
        self.final = solver_output["solver_panel"]["final_budget"]

    # ---------------------------------------------------------
    # Baseline Pie Chart
    # ---------------------------------------------------------
    def plot_baseline_pie(self):
        labels = list(self.baseline.keys())
        amounts = list(self.baseline.values())

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.pie(amounts, labels=labels, autopct="%1.1f%%")
        ax.set_title("Baseline Budget Distribution")
        return fig

    # ---------------------------------------------------------
    # Final Pie Chart
    # ---------------------------------------------------------
    def plot_final_pie(self):
        labels = list(self.final.keys())
        amounts = list(self.final.values())

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.pie(amounts, labels=labels, autopct="%1.1f%%")
        ax.set_title("Final Optimized Budget Distribution")
        return fig

    # ---------------------------------------------------------
    # Before/After Comparison (Bar Chart)
    # ---------------------------------------------------------
    def plot_before_after(self):
        categories = list(self.baseline.keys())
        before = list(self.baseline.values())
        after = [self.final[c] for c in categories]

        x = range(len(categories))

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(x, before, width=0.4, label="Baseline")
        ax.bar([i + 0.4 for i in x], after, width=0.4, label="Final")

        ax.set_xticks([i + 0.2 for i in x])
        ax.set_xticklabels(categories, rotation=45)
        ax.set_title("Before vs After Budget Comparison")
        ax.legend()

        return fig


# End of file
