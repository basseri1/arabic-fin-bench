# Context check of the ground truth (author side): gt_ctx

The independent re-transcription (`gt_iaa`) gave the annotator our rows, labels and periods and tested only the figures.
This check tests the context: the annotator receives the figures and reconstructs every row label, column header and
period from the page images alone. Three filings not used by any earlier check, drawn at random, one per page format
(`SAMPLING.md`): Ashmore Saudi Equity Fund H1 2020, Maadaniyah Q1 2025, Kingdom Holding 2024; 263 rows with figures,
22 dated value columns (12 equity-component columns carry no period).

## Steps

1. **Send the packet.** Give the annotator `packet.zip`. It contains no label, header, period or comment from the
   ground truth, only the row kinds, note references and figures. Same rules as before: page images only, no OCR or AI
   tools, no copying text out of the PDFs, own name and real times recorded.
2. **Collect.** Put the three returned workbooks (`*_context.xlsx`) and `time_log.csv` in `returned/`.
3. **Score.** `python tools/score_context_check.py` from `paper/`. It first checks that no row or figure was changed,
   then writes `results/CONTEXT_REPORT.md` and `results/adjudication.csv` (every label or period that is not the same).
4. **Adjudicate** each line of `adjudication.csv` against the page: `GT_WRONG`, `AUDIT_WRONG`, `BOTH_WRONG` or
   `EQUIVALENT` (both name the same printed line; spelling or typing differs). Re-run; decisions are kept.
5. **Report** in Sec. III-B: label agreement and the adjudicated rate of wrong ground-truth labels among the 263 rows
   with figures (with no error, the exact one-sided 95% bound is 1.13%), and the same for the 22 periods (bound 12.7%).
   Correct any ground-truth error through the annotation workbook, then re-run the bench scripts and `make_tables.py`.

The scorer was tested on simulated returns: filled from the ground truth it reports 263/263 labels and 22/22 periods;
with one statement's labels shifted by a row and three periods changed, it flags 29 labels and 3 periods.
