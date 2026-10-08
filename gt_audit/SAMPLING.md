# How the audit sample was drawn

- **Frame:** the 29 filings whose ground truth was drafted by the first annotator. The three pilot filings transcribed by annotators (Aramco 2024, Ma'aden 2024, Arabian Drilling 2024) are excluded.
- **Strata:** the format of the statement pages, by the format of the statement pages. The garbled text-layer filing counts as text layer.
- **Draw:** one filing per stratum, chosen with `random.Random(20261001).choice` over the alphabetically sorted filing IDs, strata in the order text layer, images, scanned (`tools/make_audit_packet.py`). The seed is today's date (1 Oct 2026), fixed before the draw.
- **Size:** 3 of 32 filings (9%), as planned ("about 10%").


| Stratum                 | Filings in frame | Chosen         | Split | Statements | Rows    | Figures |
| ----------------------- | ---------------- | -------------- | ----- | ---------- | ------- | ------- |
| text layer              | 13               | almarai_FY2024 | Test  | 5          | 143     | 336     |
| images in a digital PDF | 12               | halwani_FY2024 | Test  | 5          | 115     | 223     |
| fully scanned           | 4                | bishah_FY2016  | Dev   | 4          | 73      | 148     |
| **Total**               | 29               |                |       | **14**     | **331** | **707** |


Filings in each stratum:

- **text layer:** al_mubarak_usd_trade_fund_H1-2022, alahli_global_trade_fund_H1-2023, alif_meem_yaa_FY2023, almarai_FY2024, aramco_FY2023, ashmore_saudi_equity_fund_H1-2020, blom_saudi_fund_FY2022, liva_FY2024, mesc_H1-2023, musharaka_reit_FY2019, othaim_FY2024, riyad_aliemar_fund_FY2023, saudi_re_FY2024
- **images in a digital PDF:** al_rajhi_FY2024, bahri_FY2024, bank_aljazira_FY2024, buruj_FY2024, cenomi_retail_FY2024, halwani_FY2024, herfy_FY2024, maadaniyah_Q1-2025, nama_FY2024, sedco_capital_reit_FY2022, snb_FY2024, taiba_FY2024
- **fully scanned:** al_khodari_FY2018, alinma_tokio_marine_FY2022, bishah_FY2016, kingdom_holding_FY2024

With 707 audited figures and no ground-truth error found, the exact one-sided 95% upper bound on the ground-truth error rate would be 0.42%. Each error found raises it.