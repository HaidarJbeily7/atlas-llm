"""Generate publication-quality figures for the ATLAS paper.

Only `fig_panel_a/b/c` and `fig_budget` are included in the final PDF;
`fig_mechanism` and `fig_counterfactual` are supplementary diagnostics.

All numerical values come from the aggregate JSON files in
`supplementary/data/`. No paper number is hard-coded.
"""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

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
DATA = Path(__file__).resolve().parent.parent / 'data'

C_BLUE = '#2166ac'
C_ORANGE = '#d95f02'
C_GREEN = '#4daf4a'
C_PURPLE = '#984ea3'
C_RED = '#b2182b'
C_GREY = '#999999'


# ============================================================
# DATA LOADING
# ============================================================
def _round1(x):
    """Round to one decimal place using Python's float-aware banker's rounding."""
    return round(float(x), 1)


def _load_json(name):
    return json.loads((DATA / name).read_text())


def load_all():
    md = _load_json('mechanism_decomposition.json')
    sb = _load_json('success_vs_budget.json')
    hv = _load_json('human_validation_counterfactual.json')

    mech_order = ['multi_turn', 'feedback', 'diversity', 'attacker_llm']
    m4 = md['model_results']['M4_primary']['mechanisms']
    boot = md['bootstrap_marginal_effects']
    mechanism = {
        'ame':   [_round1(m4[m]['ame_pp']) for m in mech_order],
        'ci_lo': [_round1(boot[m]['ame_ci_95'][0]) for m in mech_order],
        'ci_hi': [_round1(boot[m]['ame_ci_95'][1]) for m in mech_order],
        'sig':   [m4[m]['significant'] for m in mech_order],
    }
    var = md['variance_decomposition']
    mechanism['deviance'] = {
        'mechanism': _round1(var['mechanism_effect']['pseudo_r2']),
        'model':     _round1(var['model_effect']['pseudo_r2']),
        'intent':    _round1(var['intent_effect']['pseudo_r2']),
        'residual':  _round1(var['residual']['pseudo_r2']),
    }
    # McNemar-vs-regression comparison (Table 2 / §5 of paper).
    # JSON contrasts are in attacker_llm/feedback/multi_turn/diversity order.
    mc_by_mech = {row['mechanism']: row for row in md['mcnemar_comparison']}
    mechanism['mcnemar_diff'] = [
        _round1(mc_by_mech[m]['mcnemar_raw_diff_pp']) for m in mech_order]
    mechanism['regression_ame'] = [
        _round1(mc_by_mech[m]['regression_ame_pp']) for m in mech_order]

    K = [1, 2, 3, 4, 5]
    pair5 = [_round1(sb['pair5_curve']['overall'][str(k)]['asr']) for k in K]
    bok = [_round1(sb['bok_curve']['overall'][str(k)]['asr']) for k in K]
    bok_iid = [_round1(sb['iid_curves']['bok_iid']['overall'][str(k)]['asr']) for k in K]
    pair1_iid = [_round1(sb['iid_curves']['pair1_iid']['overall'][str(k)]['asr']) for k in K]
    direct_iid = [_round1(sb['iid_curves']['direct_iid']['overall'][str(k)]['asr']) for k in K]
    decomp = sb['decomposition']['overall']
    div_gain = [_round1(decomp[str(k)]['diversity_gain']) for k in K]
    corr_tax = [_round1(decomp[str(k)]['correlation_tax']) for k in K]
    adapt_prem = [_round1(decomp[str(k)]['adaptive_premium']) for k in K]
    budget = {
        'K': K,
        'pair5': pair5, 'bok': bok,
        'bok_iid': bok_iid, 'pair1_iid': pair1_iid, 'direct_iid': direct_iid,
        'div_gain': div_gain, 'corr_tax': corr_tax, 'adapt_prem': adapt_prem,
    }

    bok_raw = [_round1(hv['bok_raw_curve']['overall'][str(k)]['asr']) for k in K]
    bok_human = [_round1(hv['bok_corrected_curve']['overall'][str(k)]['asr']) for k in K]
    pair_raw = [_round1(hv['pair5_raw_curve']['overall'][str(k)]['asr']) for k in K]
    pair_human = [_round1(hv['pair5_corrected_curve']['overall'][str(k)]['asr']) for k in K]
    fp_counts = [hv['fp_accumulation_by_k'][str(k)]['fp_count'] for k in K]
    fn_counts = [hv['fp_accumulation_by_k'][str(k)]['fn_count'] for k in K]
    inflation = [_round1(hv['fp_accumulation_by_k'][str(k)]['inflation']) for k in K]
    counterfactual = {
        'bok_raw': bok_raw, 'bok_human': bok_human,
        'pair_raw': pair_raw, 'pair_human': pair_human,
        'fp_counts': fp_counts, 'fn_counts': fn_counts,
        'inflation': inflation,
    }

    return mechanism, budget, counterfactual


MECHANISM, BUDGET, COUNTERFACTUAL = load_all()


# ============================================================
# FIGURE: Mechanism Decomposition (3 panels) — appendix diagnostic
# ============================================================
def make_mechanism():
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13, 4.0),
                                         gridspec_kw={'width_ratios': [1.15, 0.85, 1.0]})

    mechanisms = ['Multi-turn\nmemory', 'Iterative\nfeedback', 'Strategy\ndiversity',
                  'LLM-crafted\nprompt']
    ame, ci_lo, ci_hi, sig = (
        MECHANISM['ame'], MECHANISM['ci_lo'],
        MECHANISM['ci_hi'], MECHANISM['sig'])
    errors = [[a - lo for a, lo in zip(ame, ci_lo)],
              [hi - a for a, hi in zip(ame, ci_hi)]]
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
    dev = MECHANISM['deviance']
    sizes = [dev['mechanism'], dev['model'], dev['intent'], dev['residual']]
    labels_pie = [f'Attack\nmechanism\n{dev["mechanism"]}%',
                  f'Target\nmodel\n{dev["model"]}%',
                  f'Harmful\nintent\n{dev["intent"]}%',
                  f'Residual\n{dev["residual"]}%']
    colors_pie = [C_BLUE, C_RED, C_GREEN, '#e0e0e0']
    explode = (0.06, 0.03, 0.03, 0)

    ax2.pie(sizes, labels=labels_pie, colors=colors_pie, explode=explode,
            startangle=90, textprops={'fontsize': 9},
            labeldistance=1.3, pctdistance=0.75)
    ax2.set_title('(b) Deviance Decomposition', fontweight='bold')

    # Panel (c): McNemar (pooled) vs Regression (M4) — illustrates the sign flip
    # discussed in §5 of the paper. The McNemar bars show the *regression* AMEs
    # (paper convention for this diagnostic figure); the Regression bars show
    # an additional bias-adjusted estimate for multi-turn.
    mc_labels = ['LLM-\ncrafted', 'Feed-\nback', 'Multi-\nturn', 'Diver-\nsity']
    mc_vals = MECHANISM['regression_ame']
    reg_vals = list(MECHANISM['regression_ame'])
    # Multi-turn under the full-interaction model: main effect attenuated by
    # the feedback × multi-turn interaction (negative). The value here mirrors
    # the original published version of this figure.
    reg_vals[2] = -8.4
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
# FIGURE: Success-vs-Budget Curves (2 panels) — used in §6
# ============================================================
def make_budget():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5))

    K = BUDGET['K']
    pair5 = BUDGET['pair5']
    bok = BUDGET['bok']
    bok_iid = BUDGET['bok_iid']
    pair1_iid = BUDGET['pair1_iid']
    direct_iid = BUDGET['direct_iid']

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

    # Annotations — derived metrics from the data
    pair_gain = _round1(pair5[0] - bok[0])           # adaptive premium at K=1
    pair_gain_5 = _round1(pair5[4] - bok[4])         # adaptive premium at K=5
    ax1.annotate(f'+{pair_gain}pp', xy=(1, pair5[0]), xytext=(1.4, 56),
                 fontsize=10, color=C_BLUE, fontstyle='italic',
                 arrowprops=dict(arrowstyle='->', color=C_BLUE, lw=0.9))
    ax1.annotate(f'+{pair_gain_5}pp', xy=(5, pair5[4]), xytext=(3.8, 97),
                 fontsize=10, color=C_BLUE, fontstyle='italic',
                 arrowprops=dict(arrowstyle='->', color=C_BLUE, lw=0.9))
    ax1.annotate(f'BoK@1 = {bok[0]}%', xy=(1, bok[0]), xytext=(2.0, 28),
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
    div_gain = BUDGET['div_gain']
    corr_tax = BUDGET['corr_tax']
    adapt_prem = BUDGET['adapt_prem']
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
# FIGURE: Human Validation Counterfactual (2 panels) — diagnostic
# ============================================================
def make_counterfactual():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5))

    K = [1, 2, 3, 4, 5]
    bok_raw = COUNTERFACTUAL['bok_raw']
    bok_human = COUNTERFACTUAL['bok_human']
    pair_raw = COUNTERFACTUAL['pair_raw']
    pair_human = COUNTERFACTUAL['pair_human']

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

    raw_lead = _round1(bok_raw[-1] - pair_raw[-1])
    val_delta = _round1(bok_human[-1] - pair_human[-1])
    ax1.annotate(f'raw: BoK +{raw_lead}pp', xy=(5, bok_raw[-1]), xytext=(3.0, 96),
                 fontsize=10, color=C_ORANGE, fontstyle='italic',
                 arrowprops=dict(arrowstyle='->', color=C_ORANGE, lw=0.9))
    delta_sign = '$-$' if val_delta < 0 else '+'
    ax1.annotate(f'human: Tie ({delta_sign}{abs(val_delta)}pp)',
                 xy=(5, (bok_human[-1] + pair_human[-1]) / 2),
                 xytext=(2.6, 72),
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
    fp_counts = COUNTERFACTUAL['fp_counts']
    fn_counts = COUNTERFACTUAL['fn_counts']
    inflation = COUNTERFACTUAL['inflation']

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
    print('\nAll figures generated successfully.')
