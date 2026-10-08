# Same model, same pages, different providers

Qwen3.8-27B on 22 statements (24 pages; one statement per held-out filing, drawn with seed 0). Same prompt, temperature 0, 8,192-token cap, reasoning off. Pinned runs use OpenRouter provider routing with fallbacks disabled; every response was checked to come from the pinned provider. Quantisation is as declared by each provider to OpenRouter on the day of the run.

| Served by | Declared quantisation | Row recall | Figure recall | Statements worse than self-hosted | Cost of the run |
|---|---|---:|---:|---:|---:|
| OpenRouter pinned: Parasail | fp8 | 76.8% | 85.2% | 6 | $0.089 |
| OpenRouter pinned: Reka | not declared | 75.9% | 85.0% | 7 | $0.108 |
| OpenRouter pinned: DeepInfra | bf16 | 75.6% | 84.6% | 3 | $0.084 |
| self-hosted (official BF16 weights, vLLM) | bf16 | 74.9% | 84.3% | – | – |
| OpenRouter, unpinned (original run) | mixed | 65.3% | 77.4% | 9 | – |
| OpenRouter pinned: Alibaba | not declared | 53.3% | 68.7% | 12 | $0.084 |
| OpenRouter pinned: Darkbloom | fp4 | 32.9% | 46.1% | 19 | $0.050 |


