# The row side of the common base

Method: header of `bench/row_side.py`. Common base as in Table 10 (`bench/common_subset.py`): 3,878 figures.

## Where the label of a misplaced figure points

| System | Misplaced row | next line | line before | section heading | two lines away | three or more lines away | another statement | credited to another cell | One line off |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Cohere Parse | 6 | 4 (66.7%) | 2 (33.3%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 100.0% |
| Mistral OCR | 332 | 121 (36.4%) | 134 (40.4%) | 62 (18.7%) | 13 (3.9%) | 2 (0.6%) | 0 (0.0%) | 0 (0.0%) | 76.8% |
| LandingAI ADE | 11 | 0 (0.0%) | 0 (0.0%) | 11 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0.0% |
| dots.mocr pipeline, seed 0 | 50 | 17 (34.0%) | 18 (36.0%) | 15 (30.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 70.0% |
| dots.mocr pipeline, seed 1 | 55 | 27 (49.1%) | 14 (25.5%) | 14 (25.5%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 74.5% |
| dots.mocr pipeline, seed 2 | 67 | 19 (28.4%) | 28 (41.8%) | 18 (26.9%) | 2 (3.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 70.1% |
| Chandra OCR 2, own input size | 548 | 233 (42.5%) | 200 (36.5%) | 77 (14.1%) | 25 (4.6%) | 13 (2.4%) | 0 (0.0%) | 0 (0.0%) | 79.0% |

## Lines printed without a label

110 of the eligible figures (2.8%) sit on subtotals or totals that carry no label in the filing. No output can state their line item, so the scorer never credits them as complete facts.

| System | Unresolved row | of which: no label / label unmatched | of which on unlabeled lines | Misplaced row on unlabeled lines | Row side | Row side without unlabeled lines | Period side |
|---|---:|---|---:|---:|---:|---:|---:|
| Cohere Parse | 136 | 64 / 72 | 0 | 0 | 3.7% | 3.7% | 0.7% |
| Mistral OCR | 256 | 231 / 25 | 0 | 18 | 15.2% | 14.7% | 2.9% |
| LandingAI ADE | 157 | 0 / 157 | 0 | 6 | 4.3% | 4.2% | 4.4% |
| dots.mocr pipeline, seed 0 | 1180 | 1162 / 18 | 0 | 5 | 31.7% | 31.6% | 0.2% |
| dots.mocr pipeline, seed 1 | 1291 | 1270 / 21 | 0 | 3 | 34.7% | 34.6% | 0.2% |
| dots.mocr pipeline, seed 2 | 1229 | 1206 / 23 | 2 | 3 | 33.4% | 33.3% | 0.4% |
| Chandra OCR 2, own input size | 374 | 317 / 57 | 2 | 25 | 23.8% | 23.1% | 5.9% |

## Where each system puts the labels of its table rows (test pages, statements with period columns)

| System | Pages | Labels mostly in its tables | Mostly outside its tables only | Mostly absent from the output |
|---|---:|---:|---:|---:|
| Cohere Parse | 96 | 83 | 1 | 12 |
| Mistral OCR | 96 | 85 | 4 | 7 |
| LandingAI ADE | 96 | 90 | 0 | 6 |
| dots.mocr pipeline, seed 0 | 96 | 68 | 4 | 24 |
| dots.mocr pipeline, seed 1 | 96 | 65 | 4 | 27 |
| dots.mocr pipeline, seed 2 | 96 | 66 | 5 | 25 |
| Chandra OCR 2, own input size | 96 | 82 | 7 | 7 |
