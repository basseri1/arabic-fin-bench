# Obtaining the filings

The benchmark does not redistribute the filings or their page images (Saudi Exchange terms of use). Every file was obtained from the Saudi Exchange website (www.saudiexchange.sa). Obtain each one as described below, then check its SHA-256 checksum (`shasum -a 256 FILE.pdf` or `certutil -hashfile FILE.pdf SHA256`) and render its statement pages with `bench/render_pages.py` to reproduce the exact page images the systems received.

Written by `tools/filings_guide.py` from `dataset_inventory.csv` and `gt/`.

## al_khodari_FY2018

- Issuer: Al Khodari Sons (شركة أبناء عبدالله الخضري)
- Report: annual report (audited financial statements), period ending 31 Dec 2018; Arabic version, 53 PDF pages
- Statement pages transcribed: 8, 9, 10, 11
- SHA-256: `daa33dd0326e8f17b86750393669d957bb30097ca70f5e06499d2193db67e216`
- URL: not recorded. On www.saudiexchange.sa, find the issuer by its name (Arabic name above), open its financial reports, and select the annual report (audited financial statements) for the period ending 31 Dec 2018, Arabic version, 53 pages. The file was not re-checked against the exchange's current pages; verify it by the checksum above.

## al_mubarak_usd_trade_fund_H1-2022

- Issuer: Al Mubarak USD Trade Fund (صندوق المبارك)
- Report: interim financial statements, first half, period ending 30 Jun 2022; Arabic version, 10 PDF pages
- Statement pages transcribed: 3, 4, 5, 6
- SHA-256: `bba6110211707a4d976573957274e7250dab30886a66881ce0fc141a6e7b0575`
- URL: not recorded. On www.saudiexchange.sa, find the issuer by its name (Arabic name above), open its financial reports, and select the interim financial statements, first half for the period ending 30 Jun 2022, Arabic version, 10 pages. The file was not re-checked against the exchange's current pages; verify it by the checksum above.

## al_rajhi_FY2024

- Issuer: Al Rajhi Bank
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 106 PDF pages
- Statement pages transcribed: 9, 10, 11, 12, 13, 14, 15
- SHA-256: `fe030715044e5bf8dd82b610862d1379c5556317d3ec0d17acc86e5a1fab7ba7`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/353_0_2025-02-09_10-59-21_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## alahli_global_trade_fund_H1-2023

- Issuer: AlAhli Global Trade Fund (صندوق الأهلي للتجارة)
- Report: interim financial statements, first half, period ending 30 Jun 2023; Arabic version, 13 PDF pages
- Statement pages transcribed: 3, 4, 5, 6
- SHA-256: `ea520b7429b218060324f2a8e06a404b751b2e151e689261ed810f030f5e0450`
- URL: not recorded. On www.saudiexchange.sa, find the issuer by its name (Arabic name above), open its financial reports, and select the interim financial statements, first half for the period ending 30 Jun 2023, Arabic version, 13 pages. The file was not re-checked against the exchange's current pages; verify it by the checksum above.

## alif_meem_yaa_FY2023

- Issuer: Alif Meem Yaa Medical Supplies & Equipment (شركة ألف ميم ياء للمعدات والأجهزة الطبية)
- Report: annual report (audited financial statements), period ending 31 Dec 2023; Arabic version, 45 PDF pages
- Statement pages transcribed: 6, 7, 8, 9
- SHA-256: `2327b2e496faf5d6dfa5d68f6097d4cb049ce81dc7593233c573d8ab01982425`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/2684_0_2024-03-31_21-48-58_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## alinma_tokio_marine_FY2022

- Issuer: Alinma Tokio Marine (شركة الانماء طوكيو)
- Report: annual report (audited financial statements), period ending 31 Dec 2022; Arabic version, 75 PDF pages
- Statement pages transcribed: 7, 8, 9, 10, 11
- SHA-256: `c62a2e9f4c6796f5c5fced00e5fabb0fe3f897f3b47da932f852d89d8ab7a9a1`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/517_0_2023-03-29_11-26-55_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## almarai_FY2024

- Issuer: Almarai (المراعي)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 61 PDF pages
- Statement pages transcribed: 8, 9, 10, 11, 12, 13
- SHA-256: `b16a80b0bfb43617080d31908585d9ce5fd200e307568d95fdf6f231188448ac`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/408_0_2025-01-20_15-02-50_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## arabian_drilling_FY2024

- Issuer: Arabian Drilling
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 55 PDF pages
- Statement pages transcribed: 8, 9, 10, 11, 12, 13
- SHA-256: `a995bf66c1e6a136f1b5736d140cbd6d66b974aad6ce4ec6f1687bd8c14ee689`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/3703_0_2025-03-12_08-38-31_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## aramco_FY2023

- Issuer: Saudi Aramco (FY2023)
- Report: annual report (audited financial statements), period ending 31 Dec 2023; Arabic version, 87 PDF pages
- Statement pages transcribed: 12, 13, 14, 15, 16
- SHA-256: `905027d71a07f28e63119f316fa078b33c8509b51190f9e5895e0e35629969e6`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/1541_0_2024-03-11_10-08-23_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## aramco_FY2024

- Issuer: Saudi Aramco
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 84 PDF pages
- Statement pages transcribed: 12, 13, 14, 15, 16
- SHA-256: `cc6ceba6a07454bbed6d9f319411fb8835eba8d8346c7245958107afa8f0ff72`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/1541_0_2025-03-04_09-24-08_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## ashmore_saudi_equity_fund_H1-2020

- Issuer: Ashmore Saudi Equity Fund (شركة أشمور)
- Report: interim financial statements, first half, period ending 30 Jun 2020; Arabic version, 18 PDF pages
- Statement pages transcribed: 7, 8, 9, 10
- SHA-256: `87a8750278d9c72f1bb7a7475148822b9ace44947a47d649fd29583518bd9158`
- URL: not recorded. On www.saudiexchange.sa, find the issuer by its name (Arabic name above), open its financial reports, and select the interim financial statements, first half for the period ending 30 Jun 2020, Arabic version, 18 pages. The file was not re-checked against the exchange's current pages; verify it by the checksum above.

## bahri_FY2024

- Issuer: Bahri (National Shipping Co. of Saudi Arabia) (الشركة السعودي للنقل البحري)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 48 PDF pages
- Statement pages transcribed: 7, 8, 9, 10, 11
- SHA-256: `cd1630cb61d26f1b1b5ae1b7e3a4343331cf236b06c7ad45e00bbd5672d32d3e`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/439_0_2025-03-26_06-30-50_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## bank_aljazira_FY2024

- Issuer: Bank AlJazira
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 135 PDF pages
- Statement pages transcribed: 7, 8, 9, 10, 11, 12
- SHA-256: `8086ac666d3614b45f6ef3f2d99d5cca00b9cad3a2c725d215dacc166f44074f`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/329_0_2025-02-10_13-12-30_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## bishah_FY2016

- Issuer: Bishah Agricultural Development (شركة بيشة للتنمية الزراعية)
- Report: annual report (audited financial statements), period ending 31 Dec 2016; Arabic version, 20 PDF pages
- Statement pages transcribed: 4, 5, 6, 7
- SHA-256: `9f557625a4ce481873be5eaa09b55978531e4e82a0632ea48e828b1763248ba1`
- URL: not recorded. On www.saudiexchange.sa, find the issuer by its name (Arabic name above), open its financial reports, and select the annual report (audited financial statements) for the period ending 31 Dec 2016, Arabic version, 20 pages. The file was not re-checked against the exchange's current pages; verify it by the checksum above.

## blom_saudi_fund_FY2022

- Issuer: Blom Saudi Fund (صندوق بلوم)
- Report: annual report (audited financial statements), period ending 31 Dec 2022; Arabic version, 20 PDF pages
- Statement pages transcribed: 4, 5, 6, 7
- SHA-256: `d584108fbe83521c7042353b17037753de415ebde0e02a9b1cddc559b872499b`
- URL: not recorded. On www.saudiexchange.sa, find the issuer by its name (Arabic name above), open its financial reports, and select the annual report (audited financial statements) for the period ending 31 Dec 2022, Arabic version, 20 pages. The file was not re-checked against the exchange's current pages; verify it by the checksum above.

## buruj_FY2024

- Issuer: Buruj Cooperative Insurance (شركة بروج للتأمين)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 61 PDF pages
- Statement pages transcribed: 8, 9, 10, 11, 12
- SHA-256: `8982af36b1a8addb26b550fa296ae693d2ec1822e0e486032dee8a5e86408241`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/511_0_2025-03-26_21-55-31_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## cenomi_retail_FY2024

- Issuer: Fawaz Alhokair (Cenomi Retail) (شركة فواز الحكير)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 64 PDF pages
- Statement pages transcribed: 9, 10, 11, 12, 13, 14
- SHA-256: `bccab796b8a008927a3edd456f1ef525f6e65eebd4218610824f7f9a217db1b6`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/459_0_2025-04-09_07-11-29_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## halwani_FY2024

- Issuer: Halwani Bros (حلواني واخوانه)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 61 PDF pages
- Statement pages transcribed: 7, 8, 9, 10, 11, 12, 13
- SHA-256: `0de0910610b336aa8fc77070bc08b7fa5f8b90ecf4efc100fbc9a37b544dc964`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/469_0_2025-03-04_22-00-02_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## herfy_FY2024

- Issuer: Herfy Food Services (شركة هرفي)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 56 PDF pages
- Statement pages transcribed: 7, 8, 9, 10
- SHA-256: `b3025d0c786f561c024acc06b6ee5c4173c0c4f6b74ed09e01ff2395dbf4d7cf`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/470_0_2025-03-11_16-59-09_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## kingdom_holding_FY2024

- Issuer: Kingdom Holding (المملكة القابضة)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 66 PDF pages
- Statement pages transcribed: 7, 8, 9, 10, 11
- SHA-256: `08260242ed57b0f690fd309d9cf5fe6010a9b9fd7ce46ec6ab496c5a35f84434`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/463_0_2025-03-17_15-51-22_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## liva_FY2024

- Issuer: LIVA Insurance (شركة ليفا)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 81 PDF pages
- Statement pages transcribed: 7, 8, 9, 10, 11
- SHA-256: `60706e1040e3af69375892fb63ec75895def51b376652bebb1b6fa1edfab7ecf`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/512_0_2025-02-20_08-39-00_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## maadaniyah_Q1-2025

- Issuer: Maadaniyah (National Metal Manufacturing & Casting) (الشركة الوطنية لتصنيع وسبك المعادن)
- Report: interim financial statements, first quarter, period ending 31 Mar 2025; Arabic version, 15 PDF pages
- Statement pages transcribed: 4, 5, 6, 7
- SHA-256: `a2aa33bf564678530db1e8277b90bf43d125c2a16816ed4a0927f800778b05c9`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/402_0_2025-05-13_16-05-03_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## maaden_FY2024

- Issuer: Ma'aden (Saudi Arabian Mining Co.)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 126 PDF pages
- Statement pages transcribed: 11, 12, 13, 14, 15, 16
- SHA-256: `bfb35f4a6f885af5107a93c793c163700d1820cc1fb99b14e62f5539405c6b0e`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/370_0_2025-03-13_13-01-24_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## mesc_H1-2023

- Issuer: Middle East Specialized Cables (MESC) (شركة الشرق الأوسط)
- Report: interim financial statements, first half, period ending 30 Jun 2023; Arabic version, 15 PDF pages
- Statement pages transcribed: 4, 5, 6, 7
- SHA-256: `27f833b75ba0985111b125a15e38ea70b0cabfc1859919e66f995a0c21be2573`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/417_0_2023-08-03_16-37-54_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## musharaka_reit_FY2019

- Issuer: Musharaka REIT (صندوق ريت)
- Report: annual report (audited financial statements), period ending 31 Dec 2019; Arabic version, 32 PDF pages
- Statement pages transcribed: 6, 7, 8, 9, 10
- SHA-256: `b08cf6bcc59638d4ec1ba6734d009de8dd016934381c3ec411579928c19d198a`
- URL: not recorded. On www.saudiexchange.sa, find the issuer by its name (Arabic name above), open its financial reports, and select the annual report (audited financial statements) for the period ending 31 Dec 2019, Arabic version, 32 pages. The file was not re-checked against the exchange's current pages; verify it by the checksum above.

## nama_FY2024

- Issuer: Nama Chemicals (شركة نماء للبيتروكيماويات)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 44 PDF pages
- Statement pages transcribed: 7, 8, 9, 10
- SHA-256: `0d82e3786c42c247f6efeabf6832f9a762f4c3f271efcc8764dbe8499b3bc2e5`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/401_0_2025-04-10_21-07-03_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## othaim_FY2024

- Issuer: Abdullah Al-Othaim Markets (شركة أسواق عبدالله العثيم)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 56 PDF pages
- Statement pages transcribed: 7, 8, 9, 10, 11, 12
- SHA-256: `5ceaeb7901cbcf4a1bed5a9d7bbbc9ce0cbb46b0dcd9371956f713dc743206d3`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/432_0_2025-04-08_22-14-35_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## riyad_aliemar_fund_FY2023

- Issuer: Riyad Al-I'mar Fund (open-ended) (صندوق الرياض للاعمار)
- Report: annual report (audited financial statements), period ending 31 Dec 2023; Arabic version, 28 PDF pages
- Statement pages transcribed: 6, 7, 8, 9
- SHA-256: `8d1ab2eff5ad6dbc4d162746df9c0d2343ba16b21bd65bd1416c269e14ce853f`
- URL: not recorded. On www.saudiexchange.sa, find the issuer by its name (Arabic name above), open its financial reports, and select the annual report (audited financial statements) for the period ending 31 Dec 2023, Arabic version, 28 pages. The file was not re-checked against the exchange's current pages; verify it by the checksum above.

## saudi_re_FY2024

- Issuer: Saudi Re (Saudi Reinsurance Co.)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 76 PDF pages
- Statement pages transcribed: 8, 9, 10, 11, 12
- SHA-256: `20facaa981682e4201b779c931dc7b16fc36cad8fd850b3d1eb9eee549ca3396`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/504_0_2025-03-23_10-25-05_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## sedco_capital_reit_FY2022

- Issuer: SEDCO Capital REIT (صندوق سدكو)
- Report: annual report (audited financial statements), period ending 31 Dec 2022; Arabic version, 32 PDF pages
- Statement pages transcribed: 7, 8, 9, 10
- SHA-256: `1e1c3cab223cc8092045af45890f0b76bcdad68b9269c85e71f274d8a4ceb6b2`
- URL: not recorded. On www.saudiexchange.sa, find the issuer by its name (Arabic name above), open its financial reports, and select the annual report (audited financial statements) for the period ending 31 Dec 2022, Arabic version, 32 pages. The file was not re-checked against the exchange's current pages; verify it by the checksum above.

## snb_FY2024

- Issuer: Saudi National Bank (SNB)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 120 PDF pages
- Statement pages transcribed: 12, 13, 14, 15, 16
- SHA-256: `41dc8f56318bf50b2c7ffb9e7729812bb978bd2d988bfaf9e131256054dd7973`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/607_0_2025-02-06_14-39-01_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)

## taiba_FY2024

- Issuer: Taiba Investments (شركة طيبة للاستثمار)
- Report: annual report (audited financial statements), period ending 31 Dec 2024; Arabic version, 62 PDF pages
- Statement pages transcribed: 9, 10, 11, 12, 13, 14
- SHA-256: `51989e7f671ec14e76c0b092d6d2d037eeab7a4e70b69f2649c0607dc328907e`
- URL: https://www.saudiexchange.sa/Resources/fsPdf/445_0_2025-03-26_19-51-21_Ar.pdf (downloaded or checked against the exchange's copy on 27 Sep 2026)
