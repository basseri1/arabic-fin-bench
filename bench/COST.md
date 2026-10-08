# Cost per 1,000 pages: self-hosted against hosted APIs (RQ3)

Snapshot of public list prices on 28 Sep 2026; OpenRouter costs are the amounts billed in our runs. Self-hosted throughput is measured on one H100 with the model alone on the GPU (`RESULTS.md`, Speed). Cloud GPU rental stands in for the cost of on-premises hardware.

## Self-hosted, at full GPU utilisation

| Configuration | Pages per minute | $ per 1,000 pages, on-demand, to 30 Sep 2026 ($3.85/h) | $ per 1,000 pages, on-demand, from 1 Oct 2026 ($4.50/h) | $ per 1,000 pages, reserved (35% off the new rate) ($2.93/h) | Capacity of one GPU (pages per month) |
|---|---:|---:|---:|---:|---:|
| dots.mocr, out of the box | 69.7 | 0.92 | 1.08 | 0.70 | 3,053,118 |
| dots.mocr, adopted pipeline | 55.1 | 1.16 | 1.36 | 0.88 | 2,414,093 |
| Chandra OCR 2 | 36.6 | 1.75 | 2.05 | 1.33 | 1,603,181 |
| two engines (dots.mocr pipeline + Chandra OCR 2), as RQ2 needs | 22.0 | 2.92 | 3.41 | 2.22 | 963,397 |

At lower utilisation a dedicated GPU costs proportionally more per page (at 25% utilisation, four times as much). Renting per batch adds about 10 minutes of start-up per batch: 1,000 pages with two engines $4.16 per 1,000; 10,000 pages with two engines $3.48 per 1,000; 100,000 pages with two engines $3.42 per 1,000.

## Hosted APIs

| Service | $ per 1,000 pages | Source |
|---|---:|---|
| Cohere Parse (API list price) | 1.50 | cohere.com/blog/parse, 27 Aug 2026 |
| Mistral OCR (API list price) | 4.00 | mistral.ai/pricing/api, read 28 Sep 2026 |
| Mistral OCR (batch API, half price) | 2.00 | mistral.ai/pricing/api, read 28 Sep 2026 |
| LandingAI ADE (API list price, synchronous) | 25.96 | docs.landing.ai credit rates, read 3 Oct 2026; output sizes of this run |
| LandingAI ADE (Parse Jobs, standard tier) | 13.23 | docs.landing.ai credit rates, read 3 Oct 2026; output sizes of this run |
| Qwen3.6-27B via OpenRouter | 8.28 | billed in our run (158 pages) |
| Qwen3.8-27B via OpenRouter | 3.63 | billed in our run (158 pages) |
| ERNIE 4.5 VL via OpenRouter | 2.00 | billed in our run (158 pages) |

Qwen3.8-27B pinned to one provider (24 pages each): Darkbloom $2.07, Alibaba $3.49, DeepInfra $3.49, Parasail $3.70, Reka $4.50 per 1,000 pages. Command A Vision lists no public price for production use (contact sales) and is left out.

## Break-even monthly volume for a dedicated GPU ($4.50/h × 730 h = $3,285 a month)

Pages per month above which one dedicated GPU costs less than the API; '—' when that volume exceeds what one GPU can process.

| Configuration | Cohere Parse (API list price) | Mistral OCR (API list price) | Mistral OCR (batch API, half price) | LandingAI ADE (API list price, synchronous) | LandingAI ADE (Parse Jobs, standard tier) | Qwen3.6-27B via OpenRouter | Qwen3.8-27B via OpenRouter | ERNIE 4.5 VL via OpenRouter |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| dots.mocr, out of the box | 2,190,000 | 821,250 | 1,642,500 | 126,541 | 248,299 | 396,632 | 904,006 | 1,639,556 |
| dots.mocr, adopted pipeline | 2,190,000 | 821,250 | 1,642,500 | 126,541 | 248,299 | 396,632 | 904,006 | 1,639,556 |
| Chandra OCR 2 | — | 821,250 | — | 126,541 | 248,299 | 396,632 | 904,006 | — |
| two engines (dots.mocr pipeline + Chandra OCR 2), as RQ2 needs | — | 821,250 | — | 126,541 | 248,299 | 396,632 | 904,006 | — |

**Reading.** At list prices, sovereignty is not a cost saving: with the two engines that verification needs, a fully used GPU costs about $3.41 per 1,000 pages on demand, close to Mistral OCR's standard price, above its batch price and above Cohere Parse; one engine alone costs about $1.36. Below full utilisation the gap widens. The case for self-hosting sensitive documents rests on control of the data and of the serving stack, at a cost of the same order as the APIs.

![Cost against volume](figures/cost_volume.png)

