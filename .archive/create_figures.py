"""
create_figures.py - Generate all figures for the final report

Generates 7 publication-quality figures for the LaTeX report:
1. Pipeline/methodology diagram
2. Main results (accuracy vs unsupported vs false positive)
3. Clean vs adversarial retrieval
4. Threshold ablation
5. Retrieval size ablation
6. Failure mode distribution
7. False positive breakdown

Usage:
    python create_figures.py
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Set publication-quality style
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.titlesize'] = 14

# Color palette
COLOR_BASELINE = '#3498db'  # Blue
COLOR_REMOVE = '#e74c3c'    # Red
COLOR_REWRITE = '#2ecc71'   # Green
COLOR_ACCURACY = '#3498db'
COLOR_UNSUPPORTED = '#e74c3c'
COLOR_FP = '#f39c12'  # Orange
COLOR_HEDGING = '#9b59b6'  # Purple


# ============================================================================
# Figure 1: Pipeline/Methodology Diagram
# ============================================================================

def create_pipeline_diagram():
    """Create the three-system architecture diagram."""
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.axis('off')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)

    # Helper function to draw boxes
    def draw_box(x, y, width, height, text, color='lightblue', textcolor='black'):
        box = FancyBboxPatch((x, y), width, height,
                            boxstyle="round,pad=0.1",
                            edgecolor='black',
                            facecolor=color,
                            linewidth=1.5)
        ax.add_patch(box)
        ax.text(x + width/2, y + height/2, text,
               ha='center', va='center',
               fontsize=10, weight='bold',
               color=textcolor)

    # Helper function to draw arrows
    def draw_arrow(x1, y1, x2, y2):
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                               arrowstyle='->',
                               mutation_scale=20,
                               linewidth=2,
                               color='black')
        ax.add_patch(arrow)

    y = 13

    # Input
    draw_box(3, y, 4, 0.6, 'User Question', '#e8f4f8')
    draw_arrow(5, y, 5, y-0.8)
    y -= 1.5

    # Retrieval
    draw_box(3, y, 4, 0.6, 'Dense Retrieval (FAISS)', '#d1ecf1')
    draw_arrow(5, y, 5, y-0.8)
    y -= 1.5

    # Retrieved passages
    draw_box(3, y, 4, 0.6, 'Top-k Passages (k=3)', '#d1ecf1')
    draw_arrow(5, y, 5, y-0.8)
    y -= 1.5

    # Generation
    draw_box(3, y, 4, 0.6, 'GPT-4o Generation', '#fff3cd')
    draw_arrow(5, y, 5, y-0.8)
    y -= 1.5

    # Draft answer
    draw_box(3, y, 4, 0.6, 'Draft Answer', '#fff3cd')
    draw_arrow(5, y, 5, y-0.8)
    y -= 1.5

    # Claim extraction
    draw_box(3, y, 4, 0.6, 'Claim Extraction', '#f8d7da')
    draw_arrow(5, y, 5, y-0.8)
    y -= 1.5

    # NLI Verification
    draw_box(3, y, 4, 0.6, 'NLI Verification (τ=0.5)', '#f8d7da')
    y -= 1.5

    # Three-way split
    draw_arrow(5, y+1.5, 2, y+0.5)
    draw_arrow(5, y+1.5, 5, y+0.5)
    draw_arrow(5, y+1.5, 8, y+0.5)

    # System A: Baseline
    draw_box(0.5, y, 2.5, 0.6, 'System A:\nBaseline RAG', COLOR_BASELINE, 'white')
    ax.text(1.75, y-0.4, '(No repair)', ha='center', fontsize=8, style='italic')
    draw_arrow(1.75, y, 1.75, y-1.2)

    # System B: REMOVE
    draw_box(3.5, y, 2.5, 0.6, 'System B:\nREMOVE', COLOR_REMOVE, 'white')
    ax.text(4.75, y-0.4, '(Delete unsupported)', ha='center', fontsize=8, style='italic')
    draw_arrow(4.75, y, 4.75, y-1.2)

    # System C: REWRITE
    draw_box(6.5, y, 2.5, 0.6, 'System C:\nREWRITE', COLOR_REWRITE, 'white')
    ax.text(7.75, y-0.4, '(Rewrite unsupported)', ha='center', fontsize=8, style='italic')
    draw_arrow(7.75, y, 7.75, y-1.2)

    y -= 2

    # Final answers
    draw_box(0.5, y, 2.5, 0.6, 'Final Answer A', COLOR_BASELINE, 'white')
    draw_box(3.5, y, 2.5, 0.6, 'Final Answer B', COLOR_REMOVE, 'white')
    draw_box(6.5, y, 2.5, 0.6, 'Final Answer C', COLOR_REWRITE, 'white')

    # Arrows to evaluation
    draw_arrow(1.75, y, 1.75, y-0.8)
    draw_arrow(4.75, y, 4.75, y-0.8)
    draw_arrow(7.75, y, 7.75, y-0.8)

    y -= 1.5

    # Evaluation
    draw_box(2, y, 6, 0.6, 'Evaluation (Accuracy, Unsupported Rate)', '#d4edda')

    # Add note
    ax.text(5, 0.5, 'Note: All systems share identical retrieval and generation.\nDifference is only in post-verification repair strategy.',
           ha='center', fontsize=9, style='italic', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()
    plt.savefig('figure1_pipeline.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('figure1_pipeline.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 1: Pipeline diagram saved")
    plt.close()


# ============================================================================
# Figure 2: Main Results - The False Positive Problem
# ============================================================================

def create_main_results_figure():
    """Bar chart showing accuracy, unsupported rate, and false positive rate."""
    fig, ax = plt.subplots(figsize=(8, 5))

    systems = ['RAG\nBaseline', 'REMOVE', 'REWRITE']
    x = np.arange(len(systems))
    width = 0.25

    accuracy = [0.18, 0.18, 0.18]
    unsupported = [0.00, 0.00, 0.00]
    false_positive = [0.82, 0.82, 0.82]

    bars1 = ax.bar(x - width, accuracy, width, label='Accuracy', color=COLOR_ACCURACY, alpha=0.8)
    bars2 = ax.bar(x, unsupported, width, label='Unsupported Rate', color=COLOR_UNSUPPORTED, alpha=0.8)
    bars3 = ax.bar(x + width, false_positive, width, label='False Positive Rate', color=COLOR_FP, alpha=0.8)

    ax.set_ylabel('Rate', fontsize=12)
    ax.set_title('The 82% False Positive Problem: Perfect Verification, Poor Accuracy',
                fontsize=13, weight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(systems)
    ax.legend(loc='upper right')
    ax.set_ylim(0, 1.0)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Add value labels on bars
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}',
                   ha='center', va='bottom', fontsize=9)

    # Add annotation
    ax.annotate('All claims pass verification\nbut 82% of answers are wrong',
               xy=(1, 0.82), xytext=(1.5, 0.65),
               arrowprops=dict(arrowstyle='->', lw=1.5, color='red'),
               fontsize=10, color='red', weight='bold',
               bbox=dict(boxstyle='round', facecolor='white', edgecolor='red'))

    plt.tight_layout()
    plt.savefig('figure2_main_results.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('figure2_main_results.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 2: Main results saved")
    plt.close()


# ============================================================================
# Figure 3: Clean vs Adversarial Retrieval
# ============================================================================

def create_retrieval_comparison():
    """Compare clean vs adversarial retrieval conditions."""
    fig, ax = plt.subplots(figsize=(8, 5))

    conditions = ['Clean\nRetrieval', '50% Conflicting\nRetrieval']
    x = np.arange(len(conditions))
    width = 0.25

    accuracy = [0.23, 0.19]
    unsupported = [0.00, 0.00]
    avg_claims = [1.4, 1.3]

    bars1 = ax.bar(x - width, accuracy, width, label='Accuracy', color=COLOR_ACCURACY, alpha=0.8)
    bars2 = ax.bar(x, unsupported, width, label='Unsupported Rate', color=COLOR_UNSUPPORTED, alpha=0.8)
    bars3 = ax.bar(x + width, [c/10 for c in avg_claims], width, label='Avg Claims (÷10)',
                  color='#95a5a6', alpha=0.8)

    ax.set_ylabel('Rate / Scaled Value', fontsize=12)
    ax.set_title('Adversarial Retrieval Hurts Accuracy but Not Unsupported Rate',
                fontsize=13, weight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(conditions)
    ax.legend(loc='upper right')
    ax.set_ylim(0, 0.3)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.2f}',
               ha='center', va='bottom', fontsize=9)

    for bar in bars2:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
               f'{height:.2f}',
               ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig('figure3_retrieval_comparison.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('figure3_retrieval_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 3: Retrieval comparison saved")
    plt.close()


# ============================================================================
# Figure 4: Threshold Ablation
# ============================================================================

def create_threshold_ablation():
    """Show effect of varying NLI threshold."""
    fig, ax = plt.subplots(figsize=(8, 5))

    thresholds = [0.3, 0.5, 0.7, 0.9]
    accuracy = [0.18, 0.18, 0.19, 0.22]
    unsupported = [0.00, 0.00, 0.02, 0.15]

    ax.plot(thresholds, accuracy, 'o-', linewidth=2, markersize=8,
           label='Accuracy', color=COLOR_ACCURACY)
    ax.plot(thresholds, unsupported, 's-', linewidth=2, markersize=8,
           label='Unsupported Rate', color=COLOR_UNSUPPORTED)

    ax.set_xlabel('NLI Threshold (τ)', fontsize=12)
    ax.set_ylabel('Rate', fontsize=12)
    ax.set_title('Threshold Tuning Provides Minimal Improvement',
                fontsize=13, weight='bold', pad=15)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_ylim(-0.02, 0.35)

    # Add annotations
    ax.annotate('τ=0.5 (current)',
               xy=(0.5, 0.18), xytext=(0.6, 0.10),
               arrowprops=dict(arrowstyle='->', lw=1.5),
               fontsize=10, weight='bold')

    ax.annotate('Higher τ rejects\nsome valid claims',
               xy=(0.9, 0.15), xytext=(0.75, 0.25),
               arrowprops=dict(arrowstyle='->', lw=1.5, color='red'),
               fontsize=9, color='red')

    plt.tight_layout()
    plt.savefig('figure4_threshold_ablation.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('figure4_threshold_ablation.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 4: Threshold ablation saved")
    plt.close()


# ============================================================================
# Figure 5: Retrieval Size Ablation
# ============================================================================

def create_retrieval_size_ablation():
    """Show effect of varying top-k retrieval."""
    fig, ax = plt.subplots(figsize=(8, 5))

    k_values = [1, 3, 5, 10]
    accuracy = [0.14, 0.18, 0.20, 0.22]
    unsupported = [0.00, 0.00, 0.00, 0.00]
    avg_claims = [1.1, 1.3, 1.4, 1.5]

    ax.plot(k_values, accuracy, 'o-', linewidth=2, markersize=8,
           label='Accuracy', color=COLOR_ACCURACY)
    ax.plot(k_values, unsupported, 's-', linewidth=2, markersize=8,
           label='Unsupported Rate', color=COLOR_UNSUPPORTED)
    ax.plot(k_values, [c/10 for c in avg_claims], '^-', linewidth=2, markersize=8,
           label='Avg Claims (÷10)', color='#95a5a6')

    ax.set_xlabel('Number of Retrieved Passages (k)', fontsize=12)
    ax.set_ylabel('Rate / Scaled Value', fontsize=12)
    ax.set_title('More Passages Improve Accuracy Slightly, Unsupported Rate Stays Zero',
                fontsize=13, weight='bold', pad=15)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xticks(k_values)
    ax.set_ylim(-0.02, 0.30)

    # Highlight k=3 (used in experiments)
    ax.axvline(x=3, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)
    ax.text(3, 0.25, 'k=3\n(used in experiments)',
           ha='center', fontsize=9, weight='bold',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig('figure5_retrieval_size_ablation.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('figure5_retrieval_size_ablation.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 5: Retrieval size ablation saved")
    plt.close()


# ============================================================================
# Figure 6: Failure Mode Distribution
# ============================================================================

def create_failure_mode_distribution():
    """Pie chart showing distribution of failure modes."""
    fig, ax = plt.subplots(figsize=(8, 6))

    categories = ['Strategic\nHedging', 'Over-\ngeneralization', 'Other/\nUncategorized']
    counts = [29, 1, 11]
    percentages = [70.7, 2.4, 26.8]
    colors = [COLOR_HEDGING, '#e67e22', '#95a5a6']
    explode = (0.1, 0, 0)  # Explode the hedging slice

    wedges, texts, autotexts = ax.pie(counts, labels=categories, autopct='%1.1f%%',
                                       colors=colors, explode=explode,
                                       startangle=90, textprops={'fontsize': 11, 'weight': 'bold'})

    # Make percentage text more visible
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(12)
        autotext.set_weight('bold')

    ax.set_title('Dominant Failure Mode: Strategic Hedging (71% of False Positives)',
                fontsize=13, weight='bold', pad=20)

    # Add legend with counts
    legend_labels = [f'{cat.replace(chr(10), " ")}: {count} cases'
                    for cat, count in zip(categories, counts)]
    ax.legend(legend_labels, loc='upper left', bbox_to_anchor=(1, 1))

    plt.tight_layout()
    plt.savefig('figure6_failure_modes.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('figure6_failure_modes.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 6: Failure mode distribution saved")
    plt.close()


# ============================================================================
# Figure 7: False Positive Breakdown
# ============================================================================

def create_false_positive_breakdown():
    """Stacked bar showing correct vs incorrect vs unsupported."""
    fig, ax = plt.subplots(figsize=(8, 5))

    categories = ['Correct &\nVerified', 'Incorrect &\nVerified\n(False Positives)', 'Unsupported']
    counts = [9, 41, 0]
    colors = ['#2ecc71', '#e74c3c', '#95a5a6']

    # Create horizontal stacked bar
    y_pos = [0]
    left = 0
    for i, (count, color) in enumerate(zip(counts, colors)):
        ax.barh(y_pos, count, left=left, color=color, edgecolor='black', linewidth=1.5)
        # Add label in the middle of each segment
        if count > 0:
            ax.text(left + count/2, 0, f'{count}\n({count/50*100:.0f}%)',
                   ha='center', va='center', fontsize=12, weight='bold', color='white')
        left += count

    ax.set_xlim(0, 50)
    ax.set_ylim(-0.5, 0.5)
    ax.set_xlabel('Number of Examples (N=50)', fontsize=12)
    ax.set_title('82% of Examples Are False Positives: Verified but Wrong',
                fontsize=13, weight='bold', pad=15)
    ax.set_yticks([])
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    # Add legend
    legend_elements = [mpatches.Patch(color=color, label=cat.replace('\n', ' '))
                      for cat, color in zip(categories, colors)]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

    plt.tight_layout()
    plt.savefig('figure7_false_positive_breakdown.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('figure7_false_positive_breakdown.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 7: False positive breakdown saved")
    plt.close()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("Creating all figures for the final report...\n")

    create_pipeline_diagram()
    create_main_results_figure()
    create_retrieval_comparison()
    create_threshold_ablation()
    create_retrieval_size_ablation()
    create_failure_mode_distribution()
    create_false_positive_breakdown()

    print("\n✅ All figures created successfully!")
    print("\nGenerated files:")
    print("  - figure1_pipeline.pdf/png")
    print("  - figure2_main_results.pdf/png")
    print("  - figure3_retrieval_comparison.pdf/png")
    print("  - figure4_threshold_ablation.pdf/png")
    print("  - figure5_retrieval_size_ablation.pdf/png")
    print("  - figure6_failure_modes.pdf/png")
    print("  - figure7_false_positive_breakdown.pdf/png")
    print("\n📄 Use the PDF files in your LaTeX document.")
