import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(figsize=(12, 6))
ax.set_xlim(0, 12)
ax.set_ylim(0, 6)
ax.axis('off')

# Retrieved Passages box
rect1 = patches.FancyBboxPatch((1, 4.5), 4, 1, boxstyle="round,pad=0.1", edgecolor='black', facecolor='lightblue')
ax.add_patch(rect1)
ax.text(3, 5, "Retrieved Passages\n(Rule-based extraction)", ha='center', va='center', fontsize=9)

# Arrow
ax.arrow(5.5, 5, 1, 0, head_width=0.1, head_length=0.1, fc='black', ec='black')

# Extracted Claims box
rect2 = patches.FancyBboxPatch((7, 4.5), 4, 1, boxstyle="round,pad=0.1", edgecolor='black', facecolor='lightgreen')
ax.add_patch(rect2)
ax.text(9, 5, "Extracted Claims:\n\"Programmed cell death\nis regulated death\nof cells.\"", ha='center', va='center', fontsize=9)

# Down arrow
ax.arrow(9, 4, 0, -1, head_width=0.1, head_length=0.1, fc='black', ec='black')

# Verification box
rect3 = patches.FancyBboxPatch((7, 2.5), 4, 1, boxstyle="round,pad=0.1", edgecolor='black', facecolor='lightyellow')
ax.add_patch(rect3)
ax.text(9, 3, "Verify Against\nRetrieved Evidence\n(Cosine Similarity)", ha='center', va='center', fontsize=9)

# Down arrow
ax.arrow(9, 2, 0, -1, head_width=0.1, head_length=0.1, fc='black', ec='black')

# Result box
rect4 = patches.FancyBboxPatch((7, 0.5), 4, 1, boxstyle="round,pad=0.1", edgecolor='black', facecolor='lightcoral')
ax.add_patch(rect4)
ax.text(9, 1, "Result: Supported\n(Score: 1.0 ≥ 0.55)", ha='center', va='center', fontsize=9)

plt.title("Figure 3: Claim Extraction and Verification Process")
plt.savefig('verification_example.png', dpi=300, bbox_inches='tight')
plt.show()