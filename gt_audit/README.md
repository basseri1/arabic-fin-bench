# Ground-truth audit (author side)

This folder holds a blind check of the ground truth by a second annotator, on a random sample of 3 filings. The
paper's placeholders in Sec. III-B and the Limitations wait on its result.

## Steps

1. **Send the packet.** Give the auditor `packet.zip`, or the `packet/` folder. It contains no ground-truth figure.
   The auditor works only from the page images, without OCR or AI tools.
2. **Collect the results.** Put the three completed workbooks and `time_log.csv` in `returned/`.
3. **Score.** Run `python tools/score_audit.py` from `paper/`. It compares every figure cell with `gt/`. It writes:
   - `results/AUDIT_REPORT.md`: agreement overall, by filing and by kind of disagreement;
   - `results/adjudication.csv`: one line per disagreement, with the page, row, label and column.
4. **Adjudicate.** For each line of `adjudication.csv`, look at the page and fill in `decision`:
   - `GT_WRONG`: our ground truth is wrong;
   - `AUDIT_WRONG`: the auditor's figure is wrong;
   - `BOTH_WRONG`;
   - `PRINTED`: the page itself is inconsistent.

   Add the printed value in `correct_value` when the ground truth is wrong.
5. **Re-run** `score_audit.py`. Decisions already entered are kept. The report then gives the ground-truth error rate
   with its exact 95% upper bound, and a summary sentence.
6. **Fix and record.** Correct any ground-truth error in `gt/` through the annotation workbook (`tools/xlsx_to_json.py`).
   Then re-run the bench scripts.

`SAMPLING.md` records how the three filings were drawn. Re-running `tools/make_audit_packet.py` with the same seed
rebuilds the identical packet.
