"""
Generate three standalone ATLAS figures for inline placement in the paper.

  fig_panel_a.pdf — Conditions & mechanism encoding  → Section 3 (Design)
  fig_panel_b.pdf — Mechanism effects (AME bars)     → Section 5 (Decomposition)
  fig_panel_c.pdf — Automated vs validated ASR + FP  → Section 6 (Paradox)
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# ── Global style ──────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'figure.dpi': 600,
    'savefig.dpi': 600,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.15,
    'pdf.fonttype': 42,        # TrueType fonts in PDF (vector, not bitmap)
    'ps.fonttype': 42,
    'lines.antialiased': True,
    'text.antialiased': True,
    'patch.antialiased': True,
})

# ── Colours ───────────────────────────────────────────────────
C_BLUE   = '#2166ac'
C_ORANGE = '#d95f02'
C_GREEN  = '#1b9e77'
C_PINK   = '#c994c7'
C_GREY   = '#999999'
C_DKGREY = '#4a4a4a'

OUTDIR = 'figures'

# ══════════════════════════════════════════════════════════════
#  DATA
# ══════════════════════════════════════════════════════════════
conditions = [
    # (group, label, llm, fb, mt, div, asr)
    ('baselines', 'OSS-ST',            0, 0, 0, 0, 14.4),
    ('baselines', 'SS-MT',             0, 0, 1, 0, 37.5),
    ('PAIR',      'ASQ-ST (PAIR-1)',   1, 0, 0, 0, 63.7),
    ('PAIR',      'AMQ-ST (PAIR-5)',   1, 1, 0, 0, 85.9),
    ('PAIR',      'AMQ-MT',            1, 1, 1, 0, 63.4),
    ('BoK',       'BoK-ST',            1, 0, 0, 1, 85.6),
]

mechanisms_b = ['LLM-crafted\nprompting', 'Strategy\ndiversity',
                'Iterative\nfeedback', 'Multi-turn\nmemory']
ame      = [36.6, 22.4, 10.2, 0.3]
ci_lo    = [28.2, 16.9,  3.0, -6.0]
ci_hi    = [44.1, 27.8, 17.4,  7.5]
sig      = [True, True, True, False]
bar_colors_b  = [C_BLUE, C_ORANGE, C_ORANGE, C_GREEN]
bar_hatches_b = ['',     'xxxx',   '////',   '']


# ══════════════════════════════════════════════════════════════
#  FIGURE A — Conditions & mechanism encoding  (column-width)
# ══════════════════════════════════════════════════════════════
def make_panel_a():
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.7, len(conditions) + 0.1)
    ax.axis('off')

    # Column positions — spread mechanism columns wider
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
    mech_colors   = [C_BLUE, C_ORANGE, C_GREEN, C_PINK]

    # ── Header row
    header_y = len(conditions) - 0.1
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

    # ── Bar colours / hatches per row
    bar_col = [C_DKGREY, C_DKGREY, C_BLUE, C_BLUE, C_BLUE, C_ORANGE]
    bar_hat = ['', '', '////', '////', '////', 'xxxx']

    # ── Rows (reversed so first condition is at top)
    prev_grp = None
    for idx, (grp, label, llm, fb, mt, div, asr) in enumerate(
            reversed(conditions)):
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

        ri = len(conditions) - 1 - idx
        blen = (asr / 100.0) * (col_bar_e - col_bar_s)
        rect = plt.Rectangle(
            (col_bar_s, y - 0.16), blen, 0.32,
            facecolor=bar_col[ri], edgecolor='black', lw=0.6,
            hatch=bar_hat[ri], alpha=0.75, clip_on=False)
        ax.add_patch(rect)
        ax.text(col_bar_s + blen + 0.008, y, f'{asr}',
                fontsize=10.5, va='center', fontweight='bold')

    # ── Group separator lines
    for yb in [1.5, 4.5]:
        ax.plot([col_cond - 0.02, col_bar_e + 0.01], [yb, yb],
                color='#cccccc', lw=0.6)

    # ── Legend
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

    n = len(mechanisms_b)
    y_pos = np.arange(n)

    for i in range(n):
        # CI whisker
        ax.plot([ci_lo[i], ci_hi[i]], [y_pos[i]] * 2,
                color='black', lw=1.5, zorder=3)
        ax.plot(ci_hi[i], y_pos[i], 'o', color='black', ms=5, zorder=4)
        ax.plot(ci_lo[i], y_pos[i], '|', color='black', ms=8,
                markeredgewidth=1.5, zorder=4)

        # Bar
        fc = bar_colors_b[i] if sig[i] else C_GREEN
        ax.barh(y_pos[i], ame[i], height=0.55, left=0,
                color=fc, edgecolor='black', lw=0.6,
                hatch=bar_hatches_b[i], alpha=0.85, zorder=2)

        # Value + CI label
        ns = '' if sig[i] else ' (ns)'
        ax.text(ci_hi[i] + 1.5, y_pos[i],
                f'+{ame[i]} [{ci_lo[i]}, {ci_hi[i]}]{ns}',
                va='center', fontsize=10)

    ax.axvline(x=0, color='black', lw=0.9)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(mechanisms_b, fontsize=11)
    ax.set_xlabel('Average marginal effect on ASR (pp)', fontsize=11)
    ax.set_xlim(-12, 55)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.invert_yaxis()

    # Interaction-term note — placed below the x-axis label
    ax.text(0.98, -0.18,
            'Interaction: feedback $\\times$ multi-turn, OR = 0.04, p < .001',
            fontsize=9, fontstyle='italic', color=C_DKGREY,
            transform=ax.transAxes, va='top', ha='right')

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

    # ── Slope chart (ax1) ──
    x_raw, x_val = 0, 1
    bok_raw, bok_val   = 91.2, 85.6
    pair_raw, pair_val = 85.0, 85.9

    ax1.plot([x_raw, x_val], [bok_raw, bok_val], 's--', color=C_ORANGE,
             lw=2.5, ms=10, markeredgecolor='black', markeredgewidth=0.8,
             zorder=5)
    ax1.plot([x_raw, x_val], [pair_raw, pair_val], 'o-', color=C_BLUE,
             lw=2.5, ms=10, markeredgecolor='black', markeredgewidth=0.8,
             zorder=5)

    # Endpoint labels
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

    # Gap annotations
    mid_raw = (bok_raw + pair_raw) / 2
    ax1.annotate('', xy=(x_raw + 0.06, bok_raw - 0.3),
                 xytext=(x_raw + 0.06, pair_raw + 0.3),
                 arrowprops=dict(arrowstyle='<->', color=C_DKGREY, lw=1.2))
    ax1.text(x_raw + 0.14, mid_raw, '+6.2 pp\nraw lead',
             fontsize=10, color=C_DKGREY, va='center')

    ax1.text(x_val + 0.40, (pair_val + bok_val) / 2,
             r'validated $\approx$ tie' + '\n($-$0.3 pp)',
             fontsize=10, color='black', fontweight='bold', va='center')

    ax1.set_xlim(-0.45, 1.75)
    ax1.set_ylim(83.5, 92.5)
    ax1.set_xticks([x_raw, x_val])
    ax1.set_xticklabels(['raw\nautomated', 'human-\nvalidated'], fontsize=10)
    ax1.set_ylabel('ASR (%)', fontsize=11)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.grid(axis='y', alpha=0.2)

    # ── FP bar chart (ax2) ──
    fp_pair, fp_bok = 5, 23
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
