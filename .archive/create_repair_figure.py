"""
Generate Figure 8: Controlled Repair Test Results

Shows that repair mechanism removes hedging keywords but replaces them with
epistemic disclaimers, barely improving accuracy.
"""

import matplotlib.pyplot as plt
import numpy as np

# Set publication style
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.linewidth'] = 1.2

# Data
categories = ['Accuracy', '"Maybe"\nAnswers', 'Explicit\nHedging', 'Epistemic\nDisclaimers']
original = [0, 100, 100, 0]
after_repair = [5, 95, 0, 95]

# Create figure
fig, ax = plt.subplots(figsize=(10, 6))

# Bar positions
x = np.arange(len(categories))
width = 0.35

# Colors
COLOR_ORIGINAL = '#e74c3c'  # Red (problem)
COLOR_REPAIR = '#3498db'    # Blue (attempted fix)

# Create bars
bars1 = ax.bar(x - width/2, original, width, label='Original (False Positives)',
               color=COLOR_ORIGINAL, alpha=0.8, edgecolor='black', linewidth=1.2)
bars2 = ax.bar(x + width/2, after_repair, width, label='After Forced Repair',
               color=COLOR_REPAIR, alpha=0.8, edgecolor='black', linewidth=1.2)

# Add value labels on bars
def add_value_labels(bars):
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}%',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

add_value_labels(bars1)
add_value_labels(bars2)

# Styling
ax.set_ylabel('Percentage (%)', fontsize=12, fontweight='bold')
ax.set_xlabel('Metric', fontsize=12, fontweight='bold')
ax.set_title('Controlled Repair Test: Hedging Keywords → Epistemic Disclaimers',
             fontsize=14, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=11)
ax.set_ylim(0, 110)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.legend(loc='upper right', fontsize=10, framealpha=0.95, edgecolor='black')

# Add key insight annotations
# Arrow 1: Accuracy barely changes
ax.annotate('Barely\nimproves',
            xy=(0 + width/2, 5), xytext=(0.5, 25),
            arrowprops=dict(arrowstyle='->', lw=2, color='darkred'),
            fontsize=9, fontweight='bold', color='darkred',
            ha='center')

# Arrow 2: Hedging removed
ax.annotate('Hedging\nremoved ✓',
            xy=(2 + width/2, 0), xytext=(2, 60),
            arrowprops=dict(arrowstyle='->', lw=2, color='green'),
            fontsize=9, fontweight='bold', color='darkgreen',
            ha='center')

# Arrow 3: But replaced with disclaimers
ax.annotate('...but replaced\nwith disclaimers ✗',
            xy=(3 + width/2, 95), xytext=(3, 60),
            arrowprops=dict(arrowstyle='->', lw=2, color='darkred'),
            fontsize=9, fontweight='bold', color='darkred',
            ha='center')

# Add text box with key finding
textstr = 'Key Finding: Repair mechanism swaps explicit hedging ("may", "might")\nfor epistemic disclaimers ("remains less studied", "not detailed"),\nleaving answer evasion nearly unchanged (0% → 5% accuracy).'
props = dict(boxstyle='round', facecolor='wheat', alpha=0.8, edgecolor='black', linewidth=2)
ax.text(0.5, 0.97, textstr, transform=ax.transAxes, fontsize=9,
        verticalalignment='top', horizontalalignment='center', bbox=props)

plt.tight_layout()

# Save in both formats
plt.savefig('figure8_repair_test.pdf', dpi=300, bbox_inches='tight')
plt.savefig('figure8_repair_test.png', dpi=300, bbox_inches='tight')

print("✓ Figure 8 created: figure8_repair_test.pdf and .png")
print("\nThis figure shows:")
print("  - Accuracy: 0% → 5% (tiny improvement)")
print("  - 'Maybe' answers: 100% → 95% (barely changes)")
print("  - Explicit hedging: 100% → 0% (successfully removed)")
print("  - Epistemic disclaimers: 0% → 95% (replaces hedging)")
print("\n→ The story: Repair just swaps one evasion strategy for another")
