# Facts on a common assessable subset

Method: header of `bench/common_subset.py`.

Eligible: 3,878 of the 5,094 in-scope ground-truth figures of the test split (statements whose columns are periods; equity matrices excluded for every system). Each eligible cell has one outcome per system; the shares below have the same denominator for every system.

| System | Value accuracy | Line-item accuracy | Period accuracy | Fact accuracy (complete) | Unresolved | Misplaced | Wrong sign | Misread or omitted | Statements fully right | Statements with a critical error | Recovered as complete facts, all in-scope figures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Cohere Parse | 97.3% | 93.4% | 96.6% | 92.9% | 4.2% | 0.2% | 0.0% | 2.7% | 67.4% | 23.6% | 70.7% |
| Mistral OCR | 98.7% | 82.4% | 95.5% | 80.6% | 8.3% | 9.9% | 0.0% | 1.3% | 49.4% | 38.2% | 61.3% |
| LandingAI ADE | 97.8% | 91.7% | 93.2% | 89.0% | 8.4% | 0.3% | 0.0% | 2.2% | 19.1% | 42.7% | 67.8% |
| dots.mocr pipeline, seed 0 | 98.5% | 66.6% | 98.0% | 66.6% | 30.5% | 1.4% | 0.0% | 1.5% | 40.4% | 30.3% | 50.7% |
| dots.mocr pipeline, seed 1 | 98.5% | 63.7% | 97.9% | 63.6% | 33.4% | 1.5% | 0.0% | 1.4% | 37.1% | 30.3% | 48.4% |
| dots.mocr pipeline, seed 2 | 97.9% | 64.1% | 97.3% | 64.1% | 32.0% | 1.8% | 0.0% | 2.1% | 38.2% | 32.6% | 48.8% |
| Chandra OCR 2, own input size | 94.8% | 67.0% | 88.2% | 65.1% | 15.0% | 14.6% | 0.2% | 5.0% | 21.3% | 59.6% | 49.6% |

Statements with eligible figures: 89.
