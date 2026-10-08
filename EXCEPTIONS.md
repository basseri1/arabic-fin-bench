# Exception ledger

Printed totals and subtotals: 773. With a component list, all reconciling: 767. Without one: 6, each because a printed inconsistency below makes it fail as printed. Source errors are kept exactly as printed in the transcription and scored as printed.

## 1. Printed inconsistencies (source errors)

| ID | Filing | Statement | Line | Period | Kind | Printed | Implied by the rest of the filing | Note |
|---|---|---|---|---|---|---:|---:|---|
| I1 | alinma_tokio_marine_FY2022 | income | التغيرات في الاحتياطات الحسابية | 2022 | sign | (358) | 358 | 2022 figure printed in parentheses; the subtotal and the cash-flow statement imply a positive figure |
| I2 | alinma_tokio_marine_FY2022 | income | مخصص ديون مشكوك في تحصيلها | 2022 | sign | (8,580) | 8,580 | 2022 figure printed in parentheses; the subtotal and the cash-flow statement imply a positive figure |
| I3 | blom_saudi_fund_FY2022 | comprehensive income | إجمالي المصاريف | 2022 | sign | 564,308 | (564,308) | 2022 total expenses printed without parentheses, unlike its components and the 2021 figure |
| I4 | nama_FY2024 | changes in equity | الخسارة الشاملة الاخرى للسنة | total equity | sign | (385) | 385 | total-equity column of other comprehensive income printed in parentheses; its component and the comprehensive income statement show a positive figure |
| I5 | bishah_FY2016 | income | صافي الخسارة قبل الخسائر الاستثنائية | 2015 | truncated subtotal | (1,474) | (1,473,570) | 2015 subtotal printed as (1,474); its components give (1,473,570), the figure carried to the next total |
| I6 | cenomi_retail_FY2024 | changes in equity | الدخل الشامل الاخر | total equity | rounding gap | (39,641,893) | (39,641,894) in the comprehensive income statement | 2023 other comprehensive income in the changes-in-equity statement is one riyal from the comprehensive income statement |

## 2. Total checks affected (left without a component list)

| Caused by | Filing | Statement | Total | Period | Printed | Components as printed | Components corrected | Treatment |
|---|---|---|---|---|---:|---:|---:|---|
| I1 | alinma_tokio_marine_FY2022 | income | إجمالي تكاليف ومصروفات الاكتتاب | 2022 | (155,328) | (156,044) | (155,328) | kept as printed; not counted among the reconciled totals; scored as printed |
| I2 | alinma_tokio_marine_FY2022 | income | اجمالي مصروفات التشغيل الأخرى، بالصافي | 2022 | (54,025) | (71,185) | (54,025) | kept as printed; not counted among the reconciled totals; scored as printed |
| I3 | blom_saudi_fund_FY2022 | comprehensive income | إجمالي المصاريف | 2022 | 564,308 | (564,308) | (564,308) | kept as printed; not counted among the reconciled totals; scored as printed |
| I3 | blom_saudi_fund_FY2022 | comprehensive income | صافي دخل السنة | 2022 | 459,766 | 1,588,382 | 459,766 | kept as printed; not counted among the reconciled totals; scored as printed |
| I4 | nama_FY2024 | changes in equity | مجموع الدخل الشاملة للسنة | total equity | (156,500) | (157,270) | (156,500) | kept as printed; not counted among the reconciled totals; scored as printed |
| I5 | bishah_FY2016 | income | صافي الخسارة قبل الخسائر الاستثنائية | 2015 | (1,474) | (1,473,570) | (1,473,570) | kept as printed; not counted among the reconciled totals; scored as printed |

## 3. Checked, not in the source

| Filing | Statement | Line | Period | Page | Misread as | Note |
|---|---|---|---|---:|---:|---|
| halwani_FY2024 | cash flows | سداد التزامات عقود إيجار (lease payments) | 2023 | (8,095,329) | (8,065,329) | A check of the ground truth read the lease payments as (8,065,329), which would leave the financing subtotal 30,000 short. The page (re-read at 400 dpi) shows (8,095,329); with it the subtotal reconciles. The ground truth already had (8,095,329) and is unchanged. |
