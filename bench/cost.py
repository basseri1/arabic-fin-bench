"""RQ3 cost: self-hosted cost per 1,000 pages from the measured throughput on one H100, against hosted API prices, with
break-even monthly volumes and a cost-versus-volume figure (bench/figures/cost_volume.{png,pdf}).

Prices are a dated snapshot (28 Sep 2026) of public list prices; OpenRouter costs are the amounts billed in our runs.
Self-hosted throughput is the solo, 16-requests-in-flight wall clock (bench/RESULTS.md). The two-engine setup that the
verification of RQ2 needs runs dots.mocr's pipeline and Chandra OCR 2 one after the other on the same GPU.
Cloud GPU rental stands in for the cost of on-premises hardware; for strict data residency the GPU must be on premises
or in an in-country facility, whose cost this does not model.
Writes bench/COST.md and bench/cost_summary.json.  usage: python bench/cost.py
"""
import json
import math
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
HOURS_PER_MONTH = 730
OVERHEAD_H = 10 / 60           # per on-demand batch: VM start, model load and teardown (about 10 minutes, observed)
GPU = {  # $/GPU-hour, NVIDIA HGX H100, Nebius price list (https://nebius.com/prices), read 28 Sep 2026
    "on-demand, to 30 Sep 2026": 3.85, "on-demand, from 1 Oct 2026": 4.50, "reserved (35% off the new rate)": 4.50 * 0.65}
HEADLINE = "on-demand, from 1 Oct 2026"
API = {  # $ per 1,000 pages
    "Cohere Parse (API list price)": (1.50, "cohere.com/blog/parse, 27 Aug 2026"),
    "Mistral OCR (API list price)": (4.00, "mistral.ai/pricing/api, read 28 Sep 2026"),
    "Mistral OCR (batch API, half price)": (2.00, "mistral.ai/pricing/api, read 28 Sep 2026"),
}


def ade_prices():
    """LandingAI ADE, DPT-3 Pro: credits per page = 1 per page + 0.5 per 1,000 output Markdown characters on the
    priority tier (synchronous calls), half on the standard tier (Parse Jobs), each request rounded up to 0.1 credit;
    1 credit = $0.01 (docs.landing.ai dpt3/credit-consumption and ade/ade-pricing, read 3 Oct 2026). Output sizes are
    this run's (results32/landingai_ade_plain/_timing.jsonl), so the price is that of these 158 pages."""
    f = PAPER / "bench" / "results32" / "landingai_ade_plain" / "_timing.jsonl"
    if not f.exists():
        return {}
    recs = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    recs = [r for r in recs if r.get("status") == "completed"]
    if not recs:
        return {}
    up = lambda x: math.ceil(round(x * 10, 6)) / 10
    chars = [r.get("output_markdown_chars") or r.get("chars") or 0 for r in recs]
    prio = sum(up(1 + 0.5 * c / 1000) for c in chars) / len(chars)
    std = sum(up(0.5 + 0.25 * c / 1000) for c in chars) / len(chars)
    src = "docs.landing.ai credit rates, read 3 Oct 2026; output sizes of this run"
    return {"LandingAI ADE (API list price, synchronous)": (round(prio * 10, 2), src),
            "LandingAI ADE (Parse Jobs, standard tier)": (round(std * 10, 2), src)}


API.update(ade_prices())
BILLED = {"Qwen3.6-27B via OpenRouter": "qwen36_27b_plain", "Qwen3.8-27B via OpenRouter": "qwen38_27b_plain",
          "ERNIE 4.5 VL via OpenRouter": "ernie45_vl_plain"}


def ppm(summary, system, key):
    return next(r["ppm"] for r in summary["speed"] if r["system"] == system and key in r["setting"])


def main():
    S = json.loads((PAPER / "bench" / "results_summary.json").read_text())
    dots_p, dots_o, chandra = ppm(S, "dots.mocr", "adopted"), ppm(S, "dots.mocr", "out of the box"), ppm(S, "Chandra OCR 2", "own input")
    selfhosted = {"dots.mocr, out of the box": dots_o, "dots.mocr, adopted pipeline": dots_p, "Chandra OCR 2": chandra,
                  "two engines (dots.mocr pipeline + Chandra OCR 2), as RQ2 needs": 1 / (1 / dots_p + 1 / chandra)}
    per1k = {cfg: {g: price / (p * 60) * 1000 for g, price in GPU.items()} for cfg, p in selfhosted.items()}
    capacity = {cfg: p * 60 * HOURS_PER_MONTH for cfg, p in selfhosted.items()}
    billed = {}
    for name, run in BILLED.items():
        last = {}
        for l in (PAPER / "bench" / "results32" / run / "_timing.jsonl").read_text().splitlines():
            if l.strip():
                r = json.loads(l); last[r["page"]] = r
        billed[name] = 1000 * sum(r.get("cost_usd") or 0 for r in last.values()) / len(last)
    prov = json.loads((PAPER / "bench" / "providers_summary.json").read_text())["rows"]
    pinned = {r["label"].split(": ", 1)[1]: 1000 * r["cost"] / 24 for r in prov if r["cost"] is not None}
    apis = {**{k: v[0] for k, v in API.items()}, **billed}
    monthly_gpu = GPU[HEADLINE] * HOURS_PER_MONTH
    breakeven = {cfg: {api: monthly_gpu / (price / 1000) for api, price in apis.items()} for cfg in selfhosted}
    pct = lambda x: f"{x:,.2f}"
    out = ["# Cost per 1,000 pages: self-hosted against hosted APIs (RQ3)", "",
           "Snapshot of public list prices on 28 Sep 2026; OpenRouter costs are the amounts billed in our runs. Self-hosted "
           "throughput is measured on one H100 with the model alone on the GPU (`RESULTS.md`, Speed). Cloud GPU rental stands in "
           "for the cost of on-premises hardware.", "",
           "## Self-hosted, at full GPU utilisation", "",
           "| Configuration | Pages per minute | " + " | ".join(f"$ per 1,000 pages, {g} (${p:.2f}/h)" for g, p in GPU.items()) +
           " | Capacity of one GPU (pages per month) |", "|---|---:|" + "---:|" * len(GPU) + "---:|"]
    for cfg, p in selfhosted.items():
        out.append(f"| {cfg} | {p:.1f} | " + " | ".join(pct(per1k[cfg][g]) for g in GPU) + f" | {capacity[cfg]:,.0f} |")
    out += ["", "At lower utilisation a dedicated GPU costs proportionally more per page (at 25% utilisation, four times as much). "
            f"Renting per batch adds about {OVERHEAD_H * 60:.0f} minutes of start-up per batch: "
            + "; ".join(f"{n:,} pages with two engines ${GPU[HEADLINE] * (OVERHEAD_H + n / (selfhosted['two engines (dots.mocr pipeline + Chandra OCR 2), as RQ2 needs'] * 60)) / n * 1000:.2f} per 1,000"
                        for n in (1000, 10000, 100000)) + ".", "",
            "## Hosted APIs", "",
            "| Service | $ per 1,000 pages | Source |", "|---|---:|---|"]
    for k, (price, src) in API.items():
        out.append(f"| {k} | {pct(price)} | {src} |")
    for k, v in billed.items():
        out.append(f"| {k} | {pct(v)} | billed in our run (158 pages) |")
    out += ["", "Qwen3.8-27B pinned to one provider (24 pages each): " + ", ".join(f"{k} ${v:.2f}" for k, v in sorted(pinned.items(), key=lambda kv: kv[1])) +
            " per 1,000 pages. Command A Vision lists no public price for production use (contact sales) and is left out.", "",
            f"## Break-even monthly volume for a dedicated GPU (${GPU[HEADLINE]:.2f}/h × {HOURS_PER_MONTH} h = ${monthly_gpu:,.0f} a month)", "",
            "Pages per month above which one dedicated GPU costs less than the API; '—' when that volume exceeds what one GPU can process.", "",
            "| Configuration | " + " | ".join(apis) + " |", "|---|" + "---:|" * len(apis)]
    for cfg in selfhosted:
        cells = [f"{breakeven[cfg][a]:,.0f}" if breakeven[cfg][a] <= capacity[cfg] else "—" for a in apis]
        out.append(f"| {cfg} | " + " | ".join(cells) + " |")
    out += ["", "**Reading.** At list prices, sovereignty is not a cost saving: with the two engines that verification needs, a "
            f"fully used GPU costs about ${per1k['two engines (dots.mocr pipeline + Chandra OCR 2), as RQ2 needs'][HEADLINE]:.2f} per 1,000 pages "
            "on demand, close to Mistral OCR's standard price, above its batch price and above Cohere Parse; one engine alone costs "
            f"about ${per1k['dots.mocr, adopted pipeline'][HEADLINE]:.2f}. Below full utilisation the gap widens. The case for self-hosting "
            "sensitive documents rests on control of the data and of the serving stack, at a cost of the same order as the APIs.", "",
            "![Cost against volume](figures/cost_volume.png)", ""]
    (PAPER / "bench" / "COST.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    json.dump(dict(gpu_prices=GPU, selfhosted_ppm=selfhosted, per_1000=per1k, capacity=capacity, api=apis, pinned=pinned,
                   breakeven=breakeven), open(PAPER / "bench" / "cost_summary.json", "w"), indent=1)
    plot(selfhosted, apis, capacity)
    print("\n".join(out))


def plot(selfhosted, apis, capacity):
    import math
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams['pdf.fonttype'] = 42; plt.rcParams['ps.fonttype'] = 42  # TrueType, not Type 3 (embedded fonts)
    vols = [10 ** (3 + i * 4 / 200) for i in range(201)]          # 1,000 to 10 million pages a month
    fig, ax = plt.subplots(figsize=(6.6, 4.2), dpi=150)
    api_style = {"Cohere Parse (API list price)": ("#6b6b6b", "-"), "Mistral OCR (API list price)": ("#1f5fa8", "-"),
                 "Mistral OCR (batch API, half price)": ("#1f5fa8", "--"),
                 "LandingAI ADE (API list price, synchronous)": ("#9c5b2e", "-"),
                 "LandingAI ADE (Parse Jobs, standard tier)": ("#9c5b2e", "--")}
    for name, price in apis.items():
        if name not in api_style:
            continue
        col, ls = api_style[name]
        ax.plot(vols, [v * price / 1000 for v in vols], color=col, ls=ls, lw=1.8, label=name)
    two = "two engines (dots.mocr pipeline + Chandra OCR 2), as RQ2 needs"
    price_h = GPU[HEADLINE]
    dedicated = [price_h * HOURS_PER_MONTH * math.ceil(v / capacity[two]) for v in vols]
    ax.plot(vols, dedicated, color="#c0392b", lw=2.2, label="Self-hosted, two engines, dedicated H100s")
    per_page = price_h / (selfhosted[two] * 60)
    ax.plot(vols, [price_h * OVERHEAD_H + v * per_page for v in vols], color="#c0392b", ls=":", lw=2.2,
            label="Self-hosted, two engines, H100 rented per monthly batch")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Pages per month"); ax.set_ylabel("Cost per month (US$)")
    ax.grid(True, which="major", color="#e3e3e3", lw=0.6); ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    # title in the caption: ax.set_title(f"Monthly cost against volume (H100 at ${price_h:.2f}/h; list prices 28 Sep 2026)", fontsize=9)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(PAPER / "bench" / "figures" / f"cost_volume.{ext}")


if __name__ == "__main__":
    main()
