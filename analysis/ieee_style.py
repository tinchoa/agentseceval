"""
IEEE Transactions / Conference figure style.

Column widths:
  - Single column: 3.5 in (88.9 mm)
  - Double column: 7.16 in (181.9 mm)
"""

import matplotlib as mpl


def ieee_rcparams():
    return {
        "font.family": "serif",
        "font.size": 10,
        "axes.titlesize": 10,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 10,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
        "lines.linewidth": 1.0,
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.minor.width": 0.6,
        "ytick.minor.width": 0.6,
        "errorbar.capsize": 3,
    }


def apply_ieee_style():
    """Apply IEEE style globally via rcParams."""
    mpl.rcParams.update(ieee_rcparams())


SINGLE_COL = 3.5    # inches
DOUBLE_COL = 7.16   # inches

# Recommended heights (golden ratio ~ 1.618)
SINGLE_COL_H = SINGLE_COL / 1.618   # ≈ 2.16 in
DOUBLE_COL_H = DOUBLE_COL / 1.618   # ≈ 4.43 in
