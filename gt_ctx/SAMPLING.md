# How the context-check sample was drawn

- **Frame:** the 32 filings except the six used by earlier checks of the ground truth (al_khodari_FY2018, alif_meem_yaa_FY2023, almarai_FY2024, bishah_FY2016, halwani_FY2024, sedco_capital_reit_FY2022), whose labels have already circulated.
- **Strata:** the format of the statement pages, (a garbled text layer counts as text layer).
- **Draw:** one filing per stratum with `random.Random('gt_ctx 2026-10-02').choice` over the alphabetically sorted filing IDs, strata in the order text layer, images, scanned (`tools/make_context_packet.py`). The seed was fixed before the draw.

| Stratum | Filings in frame | Chosen | Split | Statements | Rows with figures | Value columns |
|---|---:|---|---|---:|---:|---:|
| text layer | 12 | ashmore_saudi_equity_fund_H1-2020 | Dev | 4 | 38 | 8 |
| images in a digital PDF | 12 | maadaniyah_Q1-2025 | Test | 4 | 89 | 10 |
| fully scanned | 2 | kingdom_holding_FY2024 | Test | 5 | 136 | 16 |

Filings in each stratum:

- **text layer:** al_mubarak_usd_trade_fund_H1-2022, alahli_global_trade_fund_H1-2023, aramco_FY2023, aramco_FY2024, ashmore_saudi_equity_fund_H1-2020, blom_saudi_fund_FY2022, liva_FY2024, mesc_H1-2023, musharaka_reit_FY2019, othaim_FY2024, riyad_aliemar_fund_FY2023, saudi_re_FY2024
- **images in a digital PDF:** al_rajhi_FY2024, arabian_drilling_FY2024, bahri_FY2024, bank_aljazira_FY2024, buruj_FY2024, cenomi_retail_FY2024, herfy_FY2024, maadaniyah_Q1-2025, maaden_FY2024, nama_FY2024, snb_FY2024, taiba_FY2024
- **fully scanned:** alinma_tokio_marine_FY2022, kingdom_holding_FY2024
