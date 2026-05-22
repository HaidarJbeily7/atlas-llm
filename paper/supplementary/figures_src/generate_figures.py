"""Generate publication-quality figures for the ATLAS paper appendix."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,
})

OUTDIR = 'figures'
C_BLUE = '#2166ac'
C_ORANGE = '#d95f02'
C_GREEN = '#4daf4a'
C_PURPLE = '#984ea3'
C_RED = '#b2182b'
C_GREY = '#999999'

# ============================================================
# FIGURE: Mechanism Decomposition (3 panels)
# ============================================================
def make_mechanism():
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13, 4.0),
                                         gridspec_kw={'width_ratios': [1.15, 0.85, 1.0]})

    # Panel (a): AME bar chart
    mechanisms = ['Multi-turn\nmemory', 'Iterative\nfeedback', 'Strategy\ndiversity',
                  'LLM-crafted\nprompt']
    ame = [0.3, 10.2, 22.4, 36.6]
    ci_lo = [-6.0, 3.0, 16.9, 28.2]
    ci_hi = [7.5, 17.4, 27.8, 44.1]
    errors = [[a - lo for a, lo in zip(ame, ci_lo)],
              [hi - a for a, hi in zip(ame, ci_hi)]]
    sig = [False, True, True, True]
    colors_bar = [C_GREY if not s else C_BLUE for s in sig]

    ax1.barh(range(4), ame, xerr=errors, color=colors_bar, edgecolor='black',
             linewidth=0.5, capsize=4, height=0.55, error_kw={'linewidth': 1.2})
    ax1.axvline(x=0, color='black', linewidth=0.8)
    ax1.set_yticks(range(4))
    ax1.set_yticklabels(mechanisms, fontsize=10)
    ax1.set_xlabel('Average Marginal Effect (pp)')
    ax1.set_title('(a) Mechanism Effects', fontweight='bold')

    for i, (a, s) in enumerate(zip(ame, sig)):
        label = '***' if s else 'ns'
        ax1.text(max(a, 0) + errors[1][i] + 1.2, i, label,
                 va='center', fontsize=9, fontstyle='italic',
                 color='black' if s else '#666666')

    ax1.set_xlim(-10, 50)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # Panel (b): Deviance decomposition pie
    sizes = [22.2, 5.0, 6.7, 66.1]
    labels_pie = ['Attack\nmechanism\n22.2%', 'Target\nmodel\n5.0%',
                  'Harmful\nintent\n6.7%', 'Residual\n66.1%']
    colors_pie = [C_BLUE, C_RED, C_GREEN, '#e0e0e0']
    explode = (0.06, 0.03, 0.03, 0)

    ax2.pie(sizes, labels=labels_pie, colors=colors_pie, explode=explode,
            startangle=90, textprops={'fontsize': 9},
            labeldistance=1.3, pctdistance=0.75)
    ax2.set_title('(b) Deviance Decomposition', fontweight='bold')

    # Panel (c): McNemar vs Regression comparison
    mc_labels = ['LLM-\ncrafted', 'Feed-\nback', 'Multi-\nturn', 'Diver-\nsity']
    mc_vals = [36.6, 10.2, 0.3, 22.4]
    reg_vals = [36.6, 10.2, -8.4, 22.4]
    x_pos = np.arange(len(mc_labels))
    w = 0.32

    ax3.bar(x_pos - w / 2, mc_vals, w, label='McNemar (pooled)',
            color=C_ORANGE, edgecolor='black', linewidth=0.5, hatch='///')
    ax3.bar(x_pos + w / 2, reg_vals, w, label='Regression (M4)',
            color=C_BLUE, edgecolor='black', linewidth=0.5)
    ax3.axhline(y=0, color='black', linewidth=0.8)
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(mc_labels, fontsize=9)
    ax3.set_ylabel('Effect size (pp)')
    ax3.set_title('(c) McNemar vs Regression', fontweight='bold')
    ax3.legend(loc='upper right', framealpha=0.9, fontsize=8)
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    ax3.set_ylim(-18, 45)
    ax3.annotate('Sign flip!', xy=(2, -8.4), xytext=(1.1, -15),
                 fontsize=9, color=C_RED, fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color=C_RED, lw=1.0))

    plt.tight_layout(w_pad=2.5)
    plt.savefig(f'{OUTDIR}/fig_mechanism.pdf')
    plt.savefig(f'{OUTDIR}/fig_mechanism.png')
    plt.close()
    print('Mechanism decomposition saved.')


# ============================================================
# FIGURE: Success-vs-Budget Curves (2 panels)
# ============================================================
def make_budget():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5))

    K = [1, 2, 3, 4, 5]
    pair5 = [68.1, 84.7, 90.3, 92.5, 93.8]
    bok = [56.2, 77.5, 84.1, 88.1, 91.2]
    bok_iid = [65.8, 88.3, 96.0, 98.6, 99.5]
    pair1_iid = [64.1, 87.1, 95.4, 98.3, 99.4]
    direct_iid = [15.9, 29.3, 40.6, 50.1, 58.0]

    ax1.plot(K, pair5, 'o-', color=C_BLUE, lw=2.5, ms=7,
             label='PAIR-5 (adaptive)', zorder=5)
    ax1.fill_between(K, [p - 4 for p in pair5],
                     [min(p + 4, 100) for p in pair5],
                     alpha=0.12, color=C_BLUE)
    ax1.plot(K, bok, 's-', color=C_ORANGE, lw=2.5, ms=7,
             label='BoK (diverse)', zorder=5)
    ax1.fill_between(K, [b - 4 for b in bok],
                     [min(b + 4, 100) for b in bok],
                     alpha=0.12, color=C_ORANGE)
    ax1.plot(K, bok_iid, '^--', color=C_GREEN, lw=1.8, ms=6,
             label='BoK i.i.d. ceiling', alpha=0.7)
    ax1.plot(K, pair1_iid, 'v--', color=C_PURPLE, lw=1.8, ms=6,
             label='PAIR-1 x K (i.i.d.)', alpha=0.7)
    ax1.plot(K, direct_iid, 'D--', color=C_GREY, lw=1.8, ms=5,
             label='Direct x K (i.i.d.)', alpha=0.7)

    ax1.annotate('+11.9pp', xy=(1, 68.1), xytext=(1.4, 56),
                 fontsize=10, color=C_BLUE, fontstyle='italic',
                 arrowprops=dict(arrowstyle='->', color=C_BLUE, lw=0.9))
    ax1.annotate('+2.5pp', xy=(5, 93.8), xytext=(3.8, 97),
                 fontsize=10, color=C_BLUE, fontstyle='italic',
                 arrowprops=dict(arrowstyle='->', color=C_BLUE, lw=0.9))
    ax1.annotate('BoK@1 = 56.2%', xy=(1, 56.2), xytext=(2.0, 28),
                 fontsize=9, color=C_ORANGE,
                 arrowprops=dict(arrowstyle='->', color=C_ORANGE, lw=0.7))

    ax1.set_xlabel('Target-call budget (K)')
    ax1.set_ylabel('Attack Success Rate (%)')
    ax1.set_title('(a) Success vs. Budget', fontweight='bold')
    ax1.set_xticks(K)
    ax1.set_ylim(10, 102)
    ax1.legend(loc='lower right', framealpha=0.9, fontsize=8.5)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.grid(axis='y', alpha=0.25)

    # Panel (b): Stacked decomposition
    div_gain = [0.0, 21.2, 27.8, 31.9, 35.0]
    corr_tax = [9.6, 10.8, 11.9, 10.5, 8.3]
    adapt_prem = [11.9, 7.2, 6.2, 4.4, 2.5]
    x = np.arange(len(K))
    w = 0.55

    ax2.bar(x, div_gain, w, label='Diversity gain',
            color=C_ORANGE, edgecolor='black', lw=0.5)
    ax2.bar(x, corr_tax, w, bottom=div_gain,
            label='Correlation tax (unrealized)',
            color=C_GREEN, edgecolor='black', lw=0.5, hatch='///', alpha=0.7)
    ax2.bar(x, adapt_prem, w,
            bottom=[d + c for d, c in zip(div_gain, corr_tax)],
            label='Adaptive premium (PAIR)',
            color=C_BLUE, edgecolor='black', lw=0.5)

    for i in range(1, len(K)):
        total = div_gain[i] + corr_tax[i] + adapt_prem[i]
        ax2.text(x[i], total + 0.6, f'{total:.0f}', ha='center',
                 va='bottom', fontsize=9, fontweight='bold')

    ax2.set_xlabel('Target-call budget (K)')
    ax2.set_ylabel('Percentage points above BoK@1')
    ax2.set_title('(b) Scaling Decomposition', fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(K)
    ax2.legend(loc='upper left', framealpha=0.9, fontsize=8.5)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout(w_pad=3)
    plt.savefig(f'{OUTDIR}/fig_budget.pdf')
    plt.savefig(f'{OUTDIR}/fig_budget.png')
    plt.close()
    print('Budget curves saved.')


# ============================================================
# FIGURE: Human Validation Counterfactual (2 panels)
# ============================================================
def make_counterfactual():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5))

    K = [1, 2, 3, 4, 5]
    bok_raw = [56.2, 77.5, 84.1, 88.1, 91.2]
    bok_human = [54.1, 73.8, 79.4, 82.2, 85.6]
    pair_raw = [62.8, 77.2, 81.9, 83.8, 85.0]
    pair_human = [64.1, 78.1, 83.1, 84.7, 85.9]

    ax1.plot(K, bok_raw, 's--', color=C_ORANGE, lw=1.8, ms=6,
             label='BoK (raw detector)', alpha=0.5)
    ax1.plot(K, bok_human, 's-', color=C_ORANGE, lw=2.5, ms=7,
             label='BoK (human-validated)')
    ax1.plot(K, pair_raw, 'o--', color=C_BLUE, lw=1.8, ms=6,
             label='PAIR-5 (raw detector)', alpha=0.5)
    ax1.plot(K, pair_human, 'o-', color=C_BLUE, lw=2.5, ms=7,
             label='PAIR-5 (human-validated)')
    ax1.fill_between(K, bok_human, bok_raw, alpha=0.15, color=C_ORANGE,
                     label='BoK FP inflation')

    ax1.annotate('raw: BoK +6.2pp', xy=(5, 91.2), xytext=(3.0, 96),
                 fontsize=10, color=C_ORANGE, fontstyle='italic',
                 arrowprops=dict(arrowstyle='->', color=C_ORANGE, lw=0.9))
    ax1.annotate('human: Tie ($-$0.3pp)', xy=(5, 85.75), xytext=(2.6, 72),
                 fontsize=10, color='black', fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color='black', lw=0.9))

    ax1.set_xlabel('Target-call budget (K)')
    ax1.set_ylabel('Attack Success Rate (%)')
    ax1.set_title('(a) Raw Detector vs Human-Validated Curves',
                  fontweight='bold')
    ax1.set_xticks(K)
    ax1.set_ylim(48, 100)
    ax1.legend(loc='lower right', framealpha=0.9, fontsize=8.5)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.grid(axis='y', alpha=0.25)

    # Panel (b): FP accumulation
    fp_counts = [7, 12, 15, 19, 23]
    fn_counts = [0, 0, 0, 0, 5]
    inflation = [2.2, 3.8, 4.7, 5.9, 5.6]

    ax2b = ax2.twinx()
    ax2.bar([k - 0.18 for k in K], fp_counts, 0.35,
            label='False positives (BoK)',
            color=C_ORANGE, edgecolor='black', lw=0.5, alpha=0.7)
    ax2.bar([k + 0.18 for k in K], fn_counts, 0.35,
            label='False negatives (BoK)',
            color=C_GREEN, edgecolor='black', lw=0.5, alpha=0.7)
    ax2b.plot(K, inflation, 'D-', color='black', lw=2.5, ms=6,
              label='ASR inflation (pp)')

    for k_val, fp in zip(K, fp_counts):
        ax2.text(k_val - 0.18, fp + 0.4, str(fp), ha='center',
                 va='bottom', fontsize=9, fontweight='bold')

    ax2.set_xlabel('Target-call budget (K)')
    ax2.set_ylabel('Count of misclassified findings')
    ax2b.set_ylabel('ASR inflation (pp)')
    ax2.set_title('(b) BoK: Any-of-K FP Accumulation', fontweight='bold')
    ax2.set_xticks(K)
    ax2.set_ylim(0, 30)
    ax2b.set_ylim(0, 7.5)

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2b.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
               framealpha=0.9, fontsize=8.5)
    ax2.spines['top'].set_visible(False)
    ax2b.spines['top'].set_visible(False)

    plt.tight_layout(w_pad=3)
    plt.savefig(f'{OUTDIR}/fig_counterfactual.pdf')
    plt.savefig(f'{OUTDIR}/fig_counterfactual.png')
    plt.close()
    print('Counterfactual saved.')


if __name__ == '__main__':
    make_mechanism()
    make_budget()
    make_counterfactual()
    print('\nAll appendix figures generated successfully.')
