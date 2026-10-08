"""Row recall against model size (test split), for small on-premises models.
Reads bench/results_summary.json only (no new runs). Colour = model type (OCR/document-parsing specialised vs
general-purpose vision-language model), fill = where it ran (filled: self-hosted on one H100; hollow: API).
Sizes are total parameters as listed in the results table (Cohere Parse: 2.3B per Cohere's documentation).
Mistral OCR and LandingAI ADE, whose sizes are not published, are drawn as reference lines; the PaddleOCR pipeline (no parameter
count in the table) is left out. Command A Vision: 111.9B, from its public checkpoint (CohereLabs/command-a-vision-07-2025). Palette: validated two-slot categorical (blue #2a78d6, orange #eb6834).
Writes bench/figures/size_accuracy.{pdf,png}.   usage: python bench/size_accuracy.py
"""
import json
import re
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
FIG = PAPER / "bench" / "figures"
SPECIALISED = {"dots.mocr", "Chandra OCR 2", "Chandra OCR 1", "Surya OCR 2", "Nanonets-OCR2", "Persian–Arabic line OCR",
               "Cohere Parse", "Mistral OCR", "LandingAI ADE", "Qari-OCR v0.3", "PaddleOCR-VL-1.6"}
SHORT = {"Persian–Arabic line OCR": "Persian–Arabic line", "Nemotron Nano 12B VL": "Nemotron 12B",
         "Qwen3-VL-32B (FP8)": "Qwen3-VL-32B"}
# label offsets in points (dx, dy) and alignment, placed by hand to avoid collisions
LABEL = {
    ("Cohere Parse", "API"): (-6, 5, "right"), ("dots.mocr", "self"): (6, 3, "left"), ("Chandra OCR 2", "self"): (6, -9, "left"),
    ("Qwen3.6-27B", "API"): (-6, -3, "right"), ("Chandra OCR 1", "self"): (0, -8, "center"),
    ("Persian–Arabic line OCR", "self"): (-6, -3, "right"), ("Qwen3.8-27B", "self"): (6, 3, "left"),
    ("Qwen3.8-27B", "API"): (6, -4, "left"), ("Surya OCR 2", "self"): (6, -3, "left"),
    ("Qwen3-VL-32B (FP8)", "self"): (6, -6, "left"), ("Nanonets-OCR2", "self"): (6, -3, "left"),
    ("ERNIE 4.5 VL", "API"): (-6, 4, "right"), ("Nemotron Nano 12B VL", "self"): (6, 2, "left"),
    ("Qari-OCR v0.3", "self"): (6, -4, "left"), ("PaddleOCR-VL-1.6", "self"): (6, 2, "left"),
    ("Command A Vision", "API"): (0, -8, "center"),
}


def size_b(params):
    m = re.match(r"\s*([\d.]+)\s*B", params or "")
    return float(m.group(1)) if m else None


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["pdf.fonttype"] = 42; plt.rcParams["ps.fonttype"] = 42   # TrueType, not Type 3 (embedded fonts)
    plt.rcParams.update({"font.size": 7, "axes.labelsize": 7.5, "xtick.labelsize": 7, "ytick.labelsize": 7})
    rows = [r for r in json.loads((PAPER / "bench" / "results_summary.json").read_text())["tables"]["test"] if r["table"] == "main"]
    ink, muted, blue, orange = "#0b0b0b", "#52514e", "#2a78d6", "#eb6834"
    fig, ax = plt.subplots(figsize=(3.5, 2.75))
    ax.axvspan(0.4, 10, color="#f1f0ec", zorder=0)
    ax.text(0.45, 3, "small (<10B)", color=muted, fontsize=6.5, va="bottom")
    refs = sorted((r for r in rows if r["system"] in ("Mistral OCR", "LandingAI ADE")), key=lambda r: r["row"])
    for i, ref in enumerate(refs):                   # hosted services whose size is not published: reference lines,
        y = 100 * ref["row"]                         # the lower one labelled below its line, the higher one above
        ax.axhline(y, color=muted, lw=0.8, ls=(0, (4, 3)), zorder=1)
        ax.text(600, y + (1.2 if i == len(refs) - 1 else -1.2), f"{ref['system']} (size not published)", color=muted,
                fontsize=6, ha="right", va="bottom" if i == len(refs) - 1 else "top")
    for r in rows:
        if "out of the box" in r["setting"]:
            continue                      # dots.mocr is shown with the adopted pipeline
        b = size_b(r["params"])
        if b is None:
            continue
        where = "API" if r["how"] == "API" else "self"
        col = blue if r["system"] in SPECIALISED else orange
        y = 100 * r["row"]
        ax.scatter([b], [y], s=26, marker="o", facecolor=col if where == "self" else "white", edgecolor=col,
                   linewidth=1.3, zorder=3)
        dx, dy, ha = LABEL.get((r["system"], where), (6, 0, "left"))
        name = SHORT.get(r["system"], r["system"]) + (" (API)" if where == "API" and r["system"].startswith("Qwen3.8") else "")
        ax.annotate(name, (b, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va="center", fontsize=6, color=ink)
    ax.set_xscale("log"); ax.set_xlim(0.4, 700); ax.set_ylim(-4, 104)
    ax.set_xticks([0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]); ax.set_xticklabels(["0.5", "1", "2", "5", "10", "20", "50", "100", "200", "500"])
    ax.set_xlabel("Parameters (billions, log scale)"); ax.set_ylabel("Row recall, test split (%)")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e4e3df", lw=0.6); ax.set_axisbelow(True)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", ls="", markersize=4.5, markerfacecolor=blue, markeredgecolor=blue, label="OCR / document parsing"),
         Line2D([], [], marker="o", ls="", markersize=4.5, markerfacecolor=orange, markeredgecolor=orange, label="general-purpose VLM"),
         Line2D([], [], marker="o", ls="", markersize=4.5, markerfacecolor="white", markeredgecolor=muted, label="through an API (hollow)")]
    ax.legend(handles=h, loc="lower right", bbox_to_anchor=(1.0, 0.27), fontsize=6, frameon=False, handletextpad=0.3, borderaxespad=0.2)
    fig.tight_layout(pad=0.3)
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"size_accuracy.{ext}", dpi=300)
    print("wrote", FIG / "size_accuracy.pdf")


if __name__ == "__main__":
    main()
