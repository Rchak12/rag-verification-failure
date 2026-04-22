import matplotlib.pyplot as plt
import numpy as np

# Data from experiment
systems = ['RAG Baseline', 'Verified RAG']
unsupported_rates = [0.3333, 0.0]
accuracies = [0.45, 0.45]
avg_claims = [3.0, 2.0]

x = np.arange(len(systems))  # the label locations
width = 0.25  # the width of the bars

fig, ax = plt.subplots(figsize=(10, 6))

# Bars for each metric
bars1 = ax.bar(x - width, unsupported_rates, width, label='Unsupported Claim Rate', color='skyblue')
bars2 = ax.bar(x, accuracies, width, label='Accuracy', color='lightgreen')
bars3 = ax.bar(x + width, avg_claims, width, label='Avg Claims per Answer', color='lightcoral')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_ylabel('Values')
ax.set_title('Comparison of RAG Baseline and Verified RAG Performance')
ax.set_xticks(x)
ax.set_xticklabels(systems)
ax.legend()

# Add value labels on bars
def add_labels(bars):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')

add_labels(bars1)
add_labels(bars2)
add_labels(bars3)

plt.tight_layout()
plt.savefig('results_comparison.png', dpi=300)
plt.show()