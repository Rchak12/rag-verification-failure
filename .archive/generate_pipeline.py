import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(figsize=(10, 8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 12)
ax.axis('off')

# Define positions
steps = [
    (5, 11, "User Question"),
    (5, 9.5, "Retriever"),
    (5, 8, "Top-k Retrieved Passages"),
    (5, 6.5, "Rule-based Generation"),
    (5, 5, "Draft Answer"),
    (5, 3.5, "Claim Extraction"),
    (5, 2, "Verification Layer"),
    (5, 0.5, "Unsupported Claims Removed"),
    (5, -0.5, "Final Verified Answer")
]

# Draw boxes and text
for x, y, text in steps:
    rect = patches.FancyBboxPatch((x-2, y-0.3), 4, 0.6, boxstyle="round,pad=0.1", edgecolor='black', facecolor='lightblue')
    ax.add_patch(rect)
    ax.text(x, y, text, ha='center', va='center', fontsize=10)

# Draw arrows
for i in range(len(steps)-1):
    x1, y1, _ = steps[i]
    x2, y2, _ = steps[i+1]
    ax.arrow(x1, y1-0.4, 0, y2-y1+0.8, head_width=0.1, head_length=0.1, fc='black', ec='black')

plt.title("Figure 1: Overview of the Verified RAG Architecture")
plt.savefig('pipeline_diagram.png', dpi=300, bbox_inches='tight')
plt.show()