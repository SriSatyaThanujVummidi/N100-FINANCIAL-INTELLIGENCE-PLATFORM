# Day 6 — Manual Data Quality Review

Random sample (seed=42): ['SUNPHARMA', 'BAJFINANCE', 'ADANIGREEN', 'HAL', 'EICHERMOT']

## Part 1 — Full profile dump for manual cross-check against source Excel

## SUNPHARMA
- Name: Sun Pharmaceuticals Industries Ltd
- face_value=1.0, book_value=288.0, roce%=17.3, roe%=16.7
- Sector: Healthcare / Pharmaceuticals (weight 0.3%)
- profitandloss: 12 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- balancesheet: 13 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03', '2024-09']
- cashflow: 12 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- financial_ratios: 12 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- Latest P&L (2024-03): sales=48497.0, expenses=35479.0, operating_profit=13018.0, opm%=28.0, net_profit=9610.0
- Latest BS (2024-09): total_assets=88116.0, total_liabilities=88116.0 (diff=0.0%)
- Latest CF (2024-03): CFO=12135.0, CFI=-763.0, CFF=-6710.0, net_cash_flow=4662.0
- documents=16, prosandcons=0, peer_groups membership=1

## BAJFINANCE
- Name: Bajaj Finance Ltd
- face_value=2.0, book_value=1402.0, roce%=11.9, roe%=22.1
- Sector: Financials / Consumer Finance (weight 1.78%)
- profitandloss: 10 years -> ['2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- balancesheet: 11 years -> ['2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03', '2024-09']
- cashflow: 10 years -> ['2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- financial_ratios: 10 years -> ['2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- Latest P&L (2024-03): sales=54972.0, expenses=18886.0, operating_profit=16099.0, opm%=19987.0, net_profit=14451.0
- Latest BS (2024-09): total_assets=420656.0, total_liabilities=420656.0 (diff=0.0%)
- Latest CF (2024-03): CFO=-72760.0, CFI=-7171.0, CFF=82415.0, net_cash_flow=2484.0
- documents=16, prosandcons=0, peer_groups membership=1

## ADANIGREEN
- Name: Adani Green Energy Ltd
- face_value=10.0, book_value=67.0, roce%=96.5, roe%=14.7
- Sector: Energy / Renewable Energy (weight 1.23%)
- profitandloss: 8 years -> ['2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- balancesheet: 9 years -> ['2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03', '2024-09']
- cashflow: 8 years -> ['2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- financial_ratios: 8 years -> ['2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- Latest P&L (2024-03): sales=9220.0, expenses=1902.0, operating_profit=7318.0, opm%=79.0, net_profit=1260.0
- Latest BS (2024-09): total_assets=98258.0, total_liabilities=98258.0 (diff=0.0%)
- Latest CF (2024-03): CFO=7713.0, CFI=-21060.0, CFF=13953.0, net_cash_flow=606.0
- documents=16, prosandcons=0, peer_groups membership=1

## HAL
- Name: Hindustan Aeronautics Ltd
- face_value=5.0, book_value=465.0, roce%=38.9, roe%=28.9
- Sector: Industrials / Defence & Aerospace (weight 1.6%)
- profitandloss: 12 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- balancesheet: 10 years -> ['2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03', '2024-09']
- cashflow: 8 years -> ['2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- financial_ratios: 8 years -> ['2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- Latest P&L (2024-03): sales=30381.0, expenses=20631.0, operating_profit=9749.0, opm%=32.0, net_profit=7595.0
- Latest BS (2024-09): total_assets=476.0, total_liabilities=476.0 (diff=0.0%)
- Latest CF (2024-03): CFO=8226.0, CFI=-6412.0, CFF=-1999.0, net_cash_flow=-185.0
- documents=16, prosandcons=0, peer_groups membership=0

## EICHERMOT
- Name: Eicher Motors Ltd
- face_value=1.0, book_value=693.0, roce%=31.1, roe%=24.2
- Sector: Consumer Discretionary / Two Wheelers (weight 3.13%)
- profitandloss: 12 years -> ['2012-12', '2013-12', '2014-12', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- balancesheet: 13 years -> ['2012-12', '2013-12', '2014-12', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03', '2024-09']
- cashflow: 12 years -> ['2012-12', '2013-12', '2014-12', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- financial_ratios: 12 years -> ['2012-12', '2013-12', '2014-12', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- Latest P&L (2024-03): sales=16536.0, expenses=12206.0, operating_profit=4329.0, opm%=26.0, net_profit=4001.0
- Latest BS (2024-09): total_assets=24380.0, total_liabilities=24380.0 (diff=0.0%)
- Latest CF (2024-03): CFO=3724.0, CFI=-2834.0, CFF=-844.0, net_cash_flow=45.0
- documents=16, prosandcons=0, peer_groups membership=1

## Part 2 — Year coverage check, all companies (DQ-16: flag < 5 years)

**2 companies below 5-year combined coverage:**

| company_id | P&L yrs | BS yrs | CF yrs | min |
|---|---|---|---|---|
| JIOFIN | 2 | 3 | 2 | 2 |
| SBIN | 12 | 0 | 12 | 0 |

## Part 3 — Re-verify the 3 known Day-5 edge-case companies

## TVSMOTOR
- Name: TVS Motor Company Ltd
- face_value=None, book_value=None, roce%=None, roe%=None
- Sector: Consumer Discretionary / Two Wheelers (weight 2.16%)
- profitandloss: 12 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- balancesheet: 13 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03', '2024-09']
- cashflow: 12 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- financial_ratios: 12 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- Latest P&L (2024-03): sales=39145.0, expenses=33645.0, operating_profit=5500.0, opm%=14.0, net_profit=1779.0
- Latest BS (2024-09): total_assets=44946.0, total_liabilities=44946.0 (diff=0.0%)
- Latest CF (2024-03): CFO=-1253.0, CFI=-1001.0, CFF=2759.0, net_cash_flow=505.0
- documents=16, prosandcons=0, peer_groups membership=1

## PNB
- Name: Punjab National Bank
- face_value=2.0, book_value=110.0, roce%=1.63, roe%=8.7
- Sector: Financials / Public Sector Banks (weight 3.82%)
- profitandloss: 12 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- balancesheet: 12 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- cashflow: 12 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- financial_ratios: 12 years -> ['2013-03', '2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- Latest P&L (2024-03): sales=109065.0, expenses=39623.0, operating_profit=None, opm%=None, net_profit=9157.0
- Latest BS (2024-03): total_assets=72371.0, total_liabilities=72371.0 (diff=0.0%)
- Latest CF (2024-03): CFO=-27939.0, CFI=-1506.0, CFF=3518.0, net_cash_flow=-25928.0
- documents=16, prosandcons=0, peer_groups membership=1

## ADANIENSOL
- Name: Adani Energy Solutions Ltd
- face_value=10.0, book_value=175.0, roce%=9.0, roe%=8.59
- Sector: Energy / Power & Utilities (weight 0.65%)
- profitandloss: 11 years -> ['2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- balancesheet: 12 years -> ['2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03', '2024-09']
- cashflow: 11 years -> ['2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- financial_ratios: 11 years -> ['2014-03', '2015-03', '2016-03', '2017-03', '2018-03', '2019-03', '2020-03', '2021-03', '2022-03', '2023-03', '2024-03']
- Latest P&L (2024-03): sales=16607.0, expenses=10896.0, operating_profit=5711.0, opm%=30.0, net_profit=1196.0
- Latest BS (2024-09): total_assets=69107.0, total_liabilities=69107.0 (diff=0.0%)
- Latest CF (2024-03): CFO=6038.0, CFI=-4943.0, CFF=-543.0, net_cash_flow=551.0
- documents=16, prosandcons=0, peer_groups membership=0
