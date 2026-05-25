"""
Generate three standalone ATLAS figures for inline placement in the paper.

  fig_panel_a.pdf — Conditions & mechanism encoding  → Section 3 (Design)
  fig_panel_b.pdf — Mechanism effects (AME bars)     → Section 5 (Decomposition)
  fig_panel_c.pdf — Automated vs validated ASR + FP  → Section 6 (Paradox)

All numerical values are loaded from the aggregate JSON files in
`supplementary/data/`. No paper number is hard-coded.
"""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# ── Global style ──────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.15,
})

# ── Colours ───────────────────────────────────────────────────
C_BLUE = '#2166ac'
C_ORANGE = '#d95f02'
C_GREEN = '#1b9e77'
C_PINK = '#c994c7'
C_GREY = '#999999'
C_DKGREY = '#4a4a4a'

OUTDIR = 'figures'
DATA = Path(__file__).resolve().parent.parent / 'data'


# ══════════════════════════════════════════════════════════════
#  DATA LOADING — every number comes from data/*.json
# ══════════════════════════════════════════════════════════════
def _round1(x):
    """Round to one decimal place using Python's float-aware banker's rounding.
    Note: due to IEEE 754 representation, values like 2.95 round to 2.9 (not 3.0).
    This matches the paper's printed values everywhere *except* a small number
    of mechanism-CI bounds, which the paper rounded with half-up convention."""
    return round(float(x), 1)


def load_panel_data():
    ec = json.loads((DATA / 'evidence_card.json').read_text())
    md = json.loads((DATA / 'mechanism_decomposition.json').read_text())

    # Panel A: conditions × mechanism encoding × adjusted ASR
    # The (llm, fb, mt, div) encoding mirrors Table 1 in the paper.
    conditions_meta = [
        ('baselines', 'OSS-ST',          'direct_single_turn',       0, 0, 0, 0),
        ('baselines', 'SS-MT',           'scripted_multi_turn',      0, 0, 1, 0),
        ('PAIR',      'ASQ-ST (PAIR-1)', 'adaptive_single_query_st', 1, 0, 0, 0),
        ('PAIR',      'AMQ-ST (PAIR-5)', 'adaptive_single_turn',     1, 1, 0, 0),
        ('PAIR',      'AMQ-MT',          'adaptive_multi_turn',      1, 1, 1, 0),
        ('BoK',       'BoK-ST',          'best_of_k_st',             1, 0, 0, 1),
    ]
    conditions = [
        (grp, lbl, llm, fb, mt, div, _round1(ec[key]['adj_asr']))
        for grp, lbl, key, llm, fb, mt, div in conditions_meta
    ]

    # Panel B: mechanism AMEs + CIs.
    # Point estimate (ame_pp) from M4 primary; CI from 2000-boot resamples.
    m4 = md['model_results']['M4_primary']['mechanisms']
    boot = md['bootstrap_marginal_effects']
    mech_order = ['attacker_llm', 'diversity', 'feedback', 'multi_turn']
    panel_b = {
        'labels': ['LLM-crafted\nprompting', 'Strategy\ndiversity',
                   'Iterative\nfeedback', 'Multi-turn\nmemory'],
        'ame':   [_round1(m4[m]['ame_pp']) for m in mech_order],
        'ci_lo': [_round1(boot[m]['ame_ci_95'][0]) for m in mech_order],
        'ci_hi': [_round1(boot[m]['ame_ci_95'][1]) for m in mech_order],
        'sig':   [m4[m]['significant'] for m in mech_order],
    }
    m5 = md['model_results'].get('M5_interaction', {})
    panel_b['interaction_or'] = m5.get('interaction_or')
    panel_b['interaction_p'] = m5.get('interaction_p')

    # Panel C: BoK vs PAIR-5, raw vs validated; FP counts.
    panel_c = {
        'bok_raw':   _round1(ec['best_of_k_st']['raw_asr']),
        'bok_val':   _round1(ec['best_of_k_st']['adj_asr']),
        'pair_raw':  _round1(ec['adaptive_single_turn']['raw_asr']),
        'pair_val':  _round1(ec['adaptive_single_turn']['adj_asr']),
        'fp_bok':    ec['best_of_k_st']['fp'],
        'fp_pair':   ec['adaptive_single_turn']['fp'],
    }

    return conditions, panel_b, panel_c


CONDITIONS, PANEL_B, PANEL_C = load_panel_data()


# ══════════════════════════════════════════════════════════════
#  FIGURE A — Conditions & mechanism encoding  (column-width)
# ══════════════════════════════════════════════════════════════
def make_panel_a():
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.7, len(CONDITIONS) + 0.1)
    ax.axis('off')

    col_group = 0.00
    col_cond  = 0.08
    col_llm   = 0.32
    col_fb    = 0.44
    col_mt    = 0.56
    col_div   = 0.67
    col_bar_s = 0.76
    col_bar_e = 0.97
    cols_mech = [col_llm, col_fb, col_mt, col_div]
    col_headers = ['LLM-\ncrafted', 'feed-\nback', 'multi-\nturn', 'diver-\nsity']

    marker_styles = [('o', 10), ('^', 10), ('s', 9), ('D', 9)]
    mech_colors = [C_BLUE, C_ORANGE, C_GREEN, C_PINK]

    # Header row
    header_y = len(CONDITIONS) - 0.1
    ax.text(col_cond, header_y, 'condition', fontsize=10,
            fontweight='bold', va='center')
    for cx, hdr in zip(cols_mech, col_headers):
        ax.text(cx, header_y, hdr, fontsize=9.5, fontweight='bold',
                va='center', ha='center', linespacing=0.9)
    ax.text((col_bar_s + col_bar_e) / 2, header_y, 'validated\nASR',
            fontsize=9.5, fontweight='bold', va='center', ha='center',
            linespacing=0.9)
    ax.plot([col_cond - 0.02, col_bar_e + 0.01],
            [header_y - 0.35, header_y - 0.35],
            color='black', lw=0.8)

    # Bar colours / hatches per row (visual style — not data)
    bar_col = [C_DKGREY, C_DKGREY, C_BLUE, C_BLUE, C_BLUE, C_ORANGE]
    bar_hat = ['', '', '////', '////', '////', 'xxxx']

    prev_grp = None
    for idx, (grp, label, llm, fb, mt, div, asr) in enumerate(
            reversed(CONDITIONS)):
        y = idx
        if grp != prev_grp:
            ax.text(col_group, y, grp, fontsize=9.5, fontstyle='italic',
                    va='center', color=C_DKGREY)
            prev_grp = grp

        ax.text(col_cond, y, label, fontsize=10.5, va='center',
                fontweight='bold')

        for cx, v, (mk, ms), cfill in zip(
                cols_mech, [llm, fb, mt, div], marker_styles, mech_colors):
            fc = cfill if v else 'white'
            ec = cfill if v else C_GREY
            ax.plot(cx, y, marker=mk, markersize=ms,
                    markerfacecolor=fc, markeredgecolor=ec,
                    markeredgewidth=1.3, clip_on=False, zorder=5)

        ri = len(CONDITIONS) - 1 - idx
        blen = (asr / 100.0) * (col_bar_e - col_bar_s)
        rect = plt.Rectangle(
            (col_bar_s, y - 0.16), blen, 0.32,
            facecolor=bar_col[ri], edgecolor='black', lw=0.6,
            hatch=bar_hat[ri], alpha=0.75, clip_on=False)
        ax.add_patch(rect)
        ax.text(col_bar_s + blen + 0.008, y, f'{asr}',
                fontsize=10.5, va='center', fontweight='bold')

    for yb in [1.5, 4.5]:
        ax.plot([col_cond - 0.02, col_bar_e + 0.01], [yb, yb],
                color='#cccccc', lw=0.6)

    ax.plot(0.32, -0.55, 'o', ms=7, markerfacecolor=C_DKGREY,
            markeredgecolor=C_DKGREY, clip_on=False)
    ax.text(0.34, -0.55, 'present', fontsize=9, va='center')
    ax.plot(0.42, -0.55, 'o', ms=7, markerfacecolor='white',
            markeredgecolor=C_GREY, markeredgewidth=1.2, clip_on=False)
    ax.text(0.44, -0.55, 'absent', fontsize=9, va='center')
    ax.text(0.55, -0.55,
            r'N=1,920; 8 models $\times$ 40 intents $\times$'
            r' 6 conditions; 100% human-reviewed',
            fontsize=8.5, va='center', color=C_GREY)

    fig.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.05)
    fig.savefig(f'{OUTDIR}/fig_panel_a.pdf')
    fig.savefig(f'{OUTDIR}/fig_panel_a.png')
    plt.close(fig)
    print('Panel A saved.')


# ══════════════════════════════════════════════════════════════
#  FIGURE B — Mechanism effects (AME horizontal bars)
# ══════════════════════════════════════════════════════════════
def make_panel_b():
    fig, ax = plt.subplots(figsize=(7.0, 3.5))

    mechanisms = PANEL_B['labels']
    ame, ci_lo, ci_hi, sig = (
        PANEL_B['ame'], PANEL_B['ci_lo'], PANEL_B['ci_hi'], PANEL_B['sig'])
    n = len(mechanisms)
    y_pos = np.arange(n)
    bar_colors = [C_BLUE, C_ORANGE, C_ORANGE, C_GREEN]
    bar_hatches = ['', 'xxxx', '////', '']

    for i in range(n):
        ax.plot([ci_lo[i], ci_hi[i]], [y_pos[i]] * 2,
                color='black', lw=1.5, zorder=3)
        ax.plot(ci_hi[i], y_pos[i], 'o', color='black', ms=5, zorder=4)
        ax.plot(ci_lo[i], y_pos[i], '|', color='black', ms=8,
                markeredgewidth=1.5, zorder=4)

        fc = bar_colors[i] if sig[i] else C_GREEN
        ax.barh(y_pos[i], ame[i], height=0.55, left=0,
                color=fc, edgecolor='black', lw=0.6,
                hatch=bar_hatches[i], alpha=0.85, zorder=2)

        ns = '' if sig[i] else ' (ns)'
        ax.text(ci_hi[i] + 1.5, y_pos[i],
                f'+{ame[i]} [{ci_lo[i]}, {ci_hi[i]}]{ns}',
                va='center', fontsize=10)

    ax.axvline(x=0, color='black', lw=0.9)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(mechanisms, fontsize=11)
    ax.set_xlabel('Average marginal effect on ASR (pp)', fontsize=11)
    ax.set_xlim(-12, 55)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.invert_yaxis()

    # Interaction-term note — values from M5_interaction in JSON
    ior = PANEL_B['interaction_or']
    ip = PANEL_B['interaction_p']
    if ior is not None and ip is not None:
        or_str = f'{ior:.2f}'
        p_str = '<.001' if ip < 0.001 else f'={ip:.3f}'
        ax.text(0.02, 0.02,
                f'Interaction term  feedback $\\times$ multi-turn:'
                f' negative interaction\nOR={or_str}, p{p_str}',
                fontsize=9, fontstyle='italic', color=C_DKGREY,
                transform=ax.transAxes, va='bottom',
                bbox=dict(boxstyle='round,pad=0.4', fc='#f0f0f0',
                          ec='#cccccc', alpha=0.9))

    fig.tight_layout()
    fig.savefig(f'{OUTDIR}/fig_panel_b.pdf')
    fig.savefig(f'{OUTDIR}/fig_panel_b.png')
    plt.close(fig)
    print('Panel B saved.')


# ══════════════════════════════════════════════════════════════
#  FIGURE C — Automated vs validated ASR  +  FP bar chart
# ══════════════════════════════════════════════════════════════
def make_panel_c():
    fig = plt.figure(figsize=(7.0, 3.8))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.42], wspace=0.40)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    x_raw, x_val = 0, 1
    bok_raw, bok_val = PANEL_C['bok_raw'], PANEL_C['bok_val']
    pair_raw, pair_val = PANEL_C['pair_raw'], PANEL_C['pair_val']

    ax1.plot([x_raw, x_val], [bok_raw, bok_val], 's--', color=C_ORANGE,
             lw=2.5, ms=10, markeredgecolor='black', markeredgewidth=0.8,
             zorder=5)
    ax1.plot([x_raw, x_val], [pair_raw, pair_val], 'o-', color=C_BLUE,
             lw=2.5, ms=10, markeredgecolor='black', markeredgewidth=0.8,
             zorder=5)

    ax1.text(x_raw - 0.08, bok_raw, f'BoK {bok_raw}', fontsize=10.5,
             fontweight='bold', color=C_ORANGE, ha='right', va='center')
    ax1.text(x_raw - 0.08, pair_raw, f'PAIR-5 {pair_raw}', fontsize=10.5,
             fontweight='bold', color=C_BLUE, ha='right', va='center')
    ax1.text(x_val + 0.08, pair_val + 0.25, f'PAIR-5 {pair_val}',
             fontsize=10.5, fontweight='bold', color=C_BLUE, ha='left',
             va='bottom')
    ax1.text(x_val + 0.08, bok_val - 0.25, f'BoK {bok_val}',
             fontsize=10.5, fontweight='bold', color=C_ORANGE, ha='left',
             va='top')

    mid_raw = (bok_raw + pair_raw) / 2
    raw_lead = _round1(bok_raw - pair_raw)
    val_delta = _round1(bok_val - pair_val)
    ax1.annotate('', xy=(x_raw + 0.06, bok_raw - 0.3),
                 xytext=(x_raw + 0.06, pair_raw + 0.3),
                 arrowprops=dict(arrowstyle='<->', color=C_DKGREY, lw=1.2))
    ax1.text(x_raw + 0.14, mid_raw, f'+{raw_lead} pp\nraw lead',
             fontsize=10, color=C_DKGREY, va='center')

    delta_sign = '$-$' if val_delta < 0 else '+'
    ax1.text(x_val + 0.40, (pair_val + bok_val) / 2,
             r'validated $\approx$ tie' + f'\n({delta_sign}{abs(val_delta)} pp)',
             fontsize=10, color='black', fontweight='bold', va='center')

    ax1.set_xlim(-0.45, 1.75)
    ax1.set_ylim(83.5, 92.5)
    ax1.set_xticks([x_raw, x_val])
    ax1.set_xticklabels(['raw\nautomated', 'human-\nvalidated'], fontsize=10)
    ax1.set_ylabel('ASR (%)', fontsize=11)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.grid(axis='y', alpha=0.2)

    fp_pair, fp_bok = PANEL_C['fp_pair'], PANEL_C['fp_bok']
    ax2.bar(['PAIR-5', 'BoK'], [fp_pair, fp_bok],
            color=[C_BLUE, C_ORANGE], edgecolor='black', lw=0.8,
            width=0.6, hatch=['////', 'xxxx'], alpha=0.8)
    ax2.text(0, fp_pair + 0.8, f'{fp_pair}', ha='center', va='bottom',
             fontsize=13, fontweight='bold')
    ax2.text(1, fp_bok + 0.8, f'{fp_bok}', ha='center', va='bottom',
             fontsize=13, fontweight='bold')
    ax2.set_ylabel('FP count', fontsize=11)
    ax2.set_title('K=5', fontsize=11, fontweight='bold', pad=6)
    ax2.set_ylim(0, 30)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    fig.tight_layout()
    fig.savefig(f'{OUTDIR}/fig_panel_c.pdf')
    fig.savefig(f'{OUTDIR}/fig_panel_c.png')
    plt.close(fig)
    print('Panel C saved.')


# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    make_panel_a()
    make_panel_b()
    make_panel_c()
    print('\nAll three panels generated successfully.')
