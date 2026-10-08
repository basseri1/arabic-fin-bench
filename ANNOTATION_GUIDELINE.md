# Annotation guideline — Arabic financial-statement ground truth

This guideline covers how the ground truth is drafted, verified and stored. It applies to all 32 filings in `dataset_inventory.csv`.

## 1. Workflow


| Step                  | Who                                                          | Output                                                                                                                                      |
| --------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Draft              | Annotator                                                    | `drafts/FILING_ID.txt` → `drafts/FILING_ID.json`                                                                                            |
| 2. Automatic checks   | `tools/validate_gt.py`                                       | Every listed total must equal its components. For the 14 filings with a text layer, every figure must also appear on the page's text layer. |
| 3. Human verification | second Annotator                                             | `annotation/FILING_ID.xlsx`: check every yellow cell against the page image, then sign `verified_by`                                        |
| 4. Convert            | `tools/xlsx_to_json.py`                                      | `gt/FILING_ID.json`, written only when it validates                                                                                         |
| 5. Second check       | A second annotator, on about 10% of filings chosen at random | Agreement rate reported with the benchmark                                                                                                        |


`drafts/` holds ground truth. `gt/` holds only double verified files. The three pilot filings (Aramco 2024, Ma'aden 2024, Arabian Drilling 2024) were transcribed and verified by the first author earlier, in the pilot.

## 2. What to transcribe

- **The primary statements:**
  - financial position;
  - income, or profit or loss;
  - comprehensive income, or the combined "profit or loss and other comprehensive income";
  - changes in equity, or changes in net assets for funds;
  - cash flows.
- **Printed supplementary tables** at the foot of the cash flow statement: non-cash transactions and interest received or paid. Use statement type `other`, or keep the rows inside the cash flow statement where they sit under the same header.
- **Do not transcribe notes to the financial statements.**
- **One statement per sheet.** A statement that runs over two pages is one statement; list both pages, e.g. `12, 13`. When a changes-in-equity statement prints each year on its own page with different columns (Al Rajhi), make it two statements.



## 3. Rows

- **One Excel row per printed line, in printed order.**
- **Row kinds:**
  - **section:** a heading without figures, e.g. "الموجودات المتداولة".
  - **item:** a line with figures.
  - **subtotal / total:** a line that sums other lines.
- **A label that wraps onto two printed lines is one row.**
- **A printed total line with no label** (a bare subtotal under a rule) is kept, with the label empty.
- **Rows printed with dashes in every column** are kept, with every value `-`.



## 4. Labels and notes

- **Labels exactly as printed**, in Arabic, including spelling variants (e.g. "الاخرى") and brackets.
  - Text-layer artefacts are not printed text. Examples: reversed words, "املالي" for "المالي", private glyphs such as "ʏ" or "ؤ". Type the label as it appears on the page image.
- **Notes column:** the note references as printed. Examples: `7`, `6-ب`, `7 (ح)`, `34(أ)`. Separate several references with a comma: `8، 9`.



## 5. Values

- **Type what is printed**, using Western digits in Excel. Record the printed digit style once per filing in `digits` on the filing sheet (`arabic-indic`, `western` or `mixed`).
- **Parentheses mean negative:** `(1,234)` → `-1234`, or type `(1,234)` and the converter handles it.
- **A printed dash** (`-`, `–`, `—`) is typed as `-` and means zero. An empty cell stays empty.
- **Never rescale.** Each statement records its own scale (`1`, `1000` or `1000000`) and currency.
  - Per-share figures stay in riyals or dollars even when the statement is in thousands. So do unit counts and net asset value per unit.
  - Put a short comment on such rows, e.g. "riyals per share".
- **Decimal separator.** Some filings print it as a comma, e.g. `٠,٨٦` for 0.86, or as `٫`. Type the number, e.g. `0.86`.
- **Columns:** the header as printed in row 7, the period end in row 8 (`YYYY-MM-DD`), and the currency in row 9 only when it differs from the statement currency (e.g. Aramco's USD columns).



## 6. Totals and the live check

- **Fill** `sum_of` **for every total or subtotal whose components are printed in the same statement.**
  - Give the Excel rows it adds up: `12:18`, or `12,15,20`.
  - Put a minus sign in front of rows that are subtracted: `11,-19`.
- **The check column shows ✓ when the total equals its components** within 1 unit, and ✗ otherwise. Every total in the dataset shows ✓: 767 of 767 across all 32 filings, recalculated in LibreOffice.
- **Printed inconsistencies.** Filings sometimes print a total that does not equal its components, or a figure with the wrong sign. Keep the printed value and do not "fix" the filing. Leave `sum_of` empty on that total and explain it in the comment column. Known cases:


| Filing                     | Where                                                  | What is printed                                                                                      |
| -------------------------- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Blom Saudi Fund FY2022     | Comprehensive income, total expenses 2022              | 564,308 without parentheses; the components and 2021 are negative                                    |
| Nama FY2024                | Changes in equity, OCI 2023, total column              | (385), although the component and the comprehensive income statement show +385                       |
| Alinma Tokio Marine FY2022 | Income statement 2022, rows 28 and 34                  | Two figures printed in parentheses. The subtotals and the cash flow statement imply positive values. |
| Bishah FY2016              | Income statement 2015, loss before extraordinary items | (1,474); the components give (1,473,570)                                                             |
| Cenomi Retail FY2024       | Changes in equity, OCI 2023                            | Differs by 1 riyal from the comprehensive income statement (rounding)                                |
| Kingdom Holding FY2024     | Changes in equity 2024                                 | A row of figures printed without a label                                                             |




## 7. Commands

```
python tools/draft_to_json.py drafts/FILING_ID.txt --workbook   # draft → JSON + workbook (yellow cells)
python tools/validate_gt.py gt/*.json drafts/*.json --textlayer  # schema, arithmetic, text-layer cross-check
python tools/textlayer.py drafts/FILING_ID.json                  # per-figure text-layer report
python tools/xlsx_to_json.py annotation/FILING_ID.xlsx           # verified workbook → gt/FILING_ID.json
python tools/approve_drafts.py drafts/*.json --by NAME --date D   # approved drafts → gt/ (never overwrites gt/)
python tools/score.py --results RESULTS_DIR --split test          # score model outputs against gt/
python tools/render.py FILING_ID --pages 8-13 --out DIR          # page images for checking (--grid 2x2 for wide pages)
```

