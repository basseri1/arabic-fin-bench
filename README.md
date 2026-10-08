# Arabic Financial Statement Extraction Benchmark

A benchmark for extracting figures from Arabic financial statements, with ground truth, a scorer, verification
checks and the outputs of every evaluated system.

The benchmark holds 32 public filings from the Saudi Exchange, companies and funds, annual and interim, with
text-layer, image and fully scanned statement pages: 156 primary financial statements, 3,394 rows that carry
figures and 8,059 figures, transcribed as printed, most of them with Arabic-Indic digits. Every printed total or
subtotal whose components are printed in the same statement is checked arithmetically; 767 of the 773 reconcile,
and the other six are recorded in an exception ledger rather than corrected.

The filings and their page images are not redistributed, in keeping with the Saudi Exchange's terms of use.
`FILINGS.md` identifies each file exactly (issuer, report, period, page count, pages transcribed, source,
retrieval date, URL where one exists, SHA-256 checksum), so that the inputs can be regenerated from the originals
with `bench/render_pages.py`.

## Layout

| Path | Contents |
|---|---|
| `gt/` | Ground truth, one JSON file per filing; schema in `tools/schema.json`; `GT_COVERAGE.md` gives the share of figures covered by printed totals |
| `annotation/`, `ANNOTATION_GUIDELINE.md` | The annotation workbooks (one per filing) and the guideline they follow |
| `exceptions.json`, `EXCEPTIONS.md` | The exception ledger: inconsistencies printed in the filings, kept as printed |
| `FILINGS.md`, `dataset_inventory.csv` | The retrieval guide and the dataset inventory (formats, splits) |
| `tools/` | Ground-truth tooling: workbook and JSON conversion, validation, the scorer (`score.py`, `gtlib.py`), the coverage and exception scripts, and the scripts of the independent checks |
| `bench/vm_scripts/` | The evaluation harness: runners for every system, the small-model pipeline (contrast enhancement, structure check and retry, band merge, arithmetic verification), the confidence and routing rules, and the page renderer |
| `bench/*.py`, `bench/*_summary.json`, `bench/*.md` | Analysis scripts, their JSON results and the written-up results: main results, statistics, structure metrics (GriTS, TEDS), failure taxonomy, root causes, routing of values and facts, sensitivity, cost, providers |
| `bench/results32/` | The output of every system on every statement page, as scored (Markdown or HTML tables, plus raw responses in `_raw/` where kept) |
| `bench/logs32/` | Run logs; `bench/CHECKPOINTS.md` gives the revision of every self-hosted checkpoint |
| `gt_iaa/`, `gt_ctx/`, `gt_audit/` | The independent checks of the ground truth: sampling, the annotator's returned workbooks, adjudication and reports (the page packets are not included) |
| `scorer_check/` | The human check of the fact scorer: key, results and scope analysis |

## Scoring

`tools/score.py` scores a system's output against the ground truth: row recall (every figure of a row on one output
line), figure, sign and label recall, precision, and facts in context (value, line item and period all right).
`bench/structure_metrics.py` and `bench/teds_cer.py` compute GriTS and TEDS. Digits are normalized before scoring
(Arabic-Indic digits, Arabic separators) and repetition loops are cut, for every system alike.

Paths in the scripts that pointed at local machines were replaced by `/path/to/...` placeholders; set the
environment variables they read (for example `IMG_DIR`, `OUT_DIR`) to your own locations.

## License

Released under the MIT License (see `LICENSE`).
