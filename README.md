# E-commerce Delivery Performance Scorecard

**Where are deliveries late, and how does delivery performance vary by customer state, seller and product category?**

## Status

Phase 1 is complete: Python/pandas data inspection, in-memory cleaning, delivery KPIs and customer-state analysis. Seller/category analysis, PostgreSQL, automated Excel reporting and Power BI are planned, not yet implemented.

## Results

Computed from the dataset's training files using the included script.

| Metric | Result |
|---|---:|
| Orders inspected | 89,316 |
| Eligible delivered orders | 87,422 |
| Late orders | 5,604 |
| On-time delivery rate | 93.59% |
| Average delivery time | 12.43 days |
| Average delay among late orders | 10.45 days |
| Illustrative on-time target | 90% |
| Gap to target | +3.59 percentage points |

### Initial findings

- Overall on-time delivery exceeds the illustrative target, but late deliveries average 10.45 calendar days overdue.
- AL has the highest late rate among states with at least 100 eligible orders: 20.62% (67 of 325 orders).
- RJ has 1,275 late orders out of 11,249 eligible orders, a late rate of 11.33%. It accounts for 22.75% of all late orders in this sample. Both rate and volume matter when prioritising further investigation.
- These comparisons describe associations, not the causes of delays or seller responsibility.

## KPI dictionary

| KPI | Formula and interpretation |
|---|---|
| Eligible orders | Status is delivered; purchase, actual delivery and estimated delivery dates are present and parseable; delivery is not before purchase |
| On-time rate | Eligible orders with actual delivery calendar date on or before estimated date / eligible orders × 100 |
| Delivery time | (Actual delivery timestamp − purchase timestamp) in seconds / 86,400; mean across eligible orders |
| Delay days | Maximum of actual delivery calendar date − estimated calendar date and zero |
| Average late delay | Mean delay days among late eligible orders only |
| State late rate | Late eligible orders in a customer state / eligible orders in that state × 100 |
| Target gap | On-time percentage − 90%, expressed in percentage points |

Delivery on the estimated date counts as on time, regardless of time of day. The 90% target and minimum state volume of 100 orders are illustrative project choices, not company service commitments.

## Dataset

Source: [Ecommerce Order & Supply Chain Dataset by bytadit on Kaggle](https://www.kaggle.com/datasets/bytadit/ecommerce-order-dataset).

Download and extract the dataset yourself. Use only these five files from **train**, placed directly inside `data/raw/`:

- `df_Orders.csv`
- `df_OrderItems.csv`
- `df_Customers.csv`
- `df_Products.csv`
- `df_Payments.csv`

The test orders omit delivery outcomes needed for these KPIs. Raw data is not distributed in this repository. Check the dataset page's current licence and attribution requirements before reuse. The repository's code licence does not grant rights to the source dataset.

## Run locally

Python 3.12 is recommended. The script was verified with Python 3.12.14 and pandas 2.2.3.

From the repository root, after placing the training CSVs:

```bash
python -m pip install -r requirements.txt
python python/01_inspect_data.py
```

Alternatively, open the saved script in Spyder and run the whole file with F5. Paths are resolved relative to the script, so the working directory does not need to be changed.

The script prints quality checks, KPI results and the ten states with the highest late rates. Cleaned DataFrames remain in memory; it does not write cleaned CSVs, database tables or reports yet. Original CSVs are unchanged.

## Data quality and validation

- Removed 61,865 exact duplicate product rows in memory, leaving 27,451 unique product IDs.
- Retained missing product attributes: 141 missing categories and two records missing each physical measurement after deduplication.
- Identified 1,889 missing actual delivery timestamps, including six orders marked delivered.
- Excluded 1,888 orders not marked delivered and six delivered orders missing delivery dates from delivery KPIs. All 89,316 orders remain in the full orders DataFrame.
- Five canceled orders have delivery dates; status-based eligibility excludes them.
- Found no invalid date strings and no deliveries before purchase.
- Confirmed no missing or repeated IDs for the tested keys after product deduplication.
- Confirmed all checked foreign-key references match.
- Customer join preserved 87,422 eligible rows, with no unmatched customers.

This dataset has one item and one payment row per order. That is an observed property of these files, not a general e-commerce modelling assumption. Most checks currently report counts rather than enforcing database constraints.

## Limitations

This is a historical training subset, not a current operational scorecard. No review scores or carrier handover dates are supplied, so satisfaction analysis and warehouse/transit stage breakdowns are unavailable. Delivered-only metrics do not capture the experience of orders that never arrived. Small state samples and differences in product/seller mix can affect comparisons.

Payment values were observed during preliminary inspection to differ from item price plus shipping for 89,314 orders; reconciliation remains open and is not implemented in this script. No revenue or freight-share conclusions are presented.

## Repository contents

| Path | Purpose |
|---|---|
| `python/01_inspect_data.py` | Inspection, cleaning, delivery KPIs, state analysis and relationship checks |
| `requirements.txt` | pandas dependency used for verification |
| `data/raw/README.md` | Local dataset placement instructions |
| `docs/phase1_output.txt` | Reproduced console results |

## Next steps

- Add a persistent quality log and reproducible database ingestion.
- Build PostgreSQL tables with keys and an order-performance view.
- Analyse monthly trends, sellers and product categories in SQL.
- Generate an automated Excel scorecard.
- Build a Power BI dashboard and document additional findings.
