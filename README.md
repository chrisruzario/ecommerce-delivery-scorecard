# E-commerce Delivery Performance Scorecard

**Where are deliveries late, and how does delivery performance vary by customer state, seller and product category?**

## Status

Python inspection and initial PostgreSQL analysis are complete: cleaned-table ingestion, five primary keys, four foreign keys, join indexes, an order-performance view, headline KPIs and customer-state analysis. Monthly trends with a weighted three-month rolling rate, seller/category analysis and automated Excel reporting are also complete. Power BI remains planned.

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
- March 2018 has the lowest observed monthly on-time rate: 82.24% across 6,352 eligible orders. The three-month rolling rate is 87.63%.
- Office furniture has a 10.98% late rate (58 of 528 orders), with average delivery time of 22.23 days and average late delay of 15.12 days.
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

The inspection script prints quality checks, KPI results and the ten states with the highest late rates. Its cleaned DataFrames remain in memory; the separate loader below persists them to PostgreSQL. Original CSVs are unchanged.

## PostgreSQL setup and execution

1. Install PostgreSQL and create an empty database named `ecommerce_delivery`.
2. Install `requirements.txt` in your active Python environment.
3. From the repository root in a **terminal/Anaconda Prompt**, run:

```bash
python python/02_load_database.py
```

The loader connects to localhost:5432 as postgres and asks for the database password. Do not put passwords in scripts or commits. Use a terminal: Spyder's QtConsole may display password input.

4. In pgAdmin, connect the Query Tool to `ecommerce_delivery` and execute the SQL files in numbered order, from `00` through `06`.

The loader creates customers, products, orders, order_items and payments in the public schema. Products has 27,451 rows; each other table has 89,316. It commits all five tables together only after row-count verification. Existing tables cause the initial loader to stop without overwriting them. The keys/indexes script is also a one-time setup; do not rerun it after success.

The view preserves all orders and uses NULL delivery metrics for ineligible orders. KPI queries explicitly filter the eligibility flag. Dates are compared as calendar dates, matching Python.

### Verification checkpoint

The local PostgreSQL load and nine key constraints were confirmed successful. The author confirmed the SQL headline results match Python: 87,422 eligible orders, 5,604 late orders, 93.59% on-time, 12.43 delivery days and 10.45 late-delay days. The state query was run locally; its reference results are in `docs/phase1_output.txt`. This is manual local validation, not automated database CI.

## Automated Excel reporting

[Download the sample workbook](excel_output/delivery_scorecard.xlsx).

After completing the database setup, run this from the repository root in a terminal:

```bash
python python/03_excel_report.py
```

Enter the PostgreSQL password when prompted. The script queries the database view and regenerates `excel_output/delivery_scorecard.xlsx`. Close the workbook in Excel before rerunning: the output is overwritten. No password is stored in the script.

The workbook contains Summary, Monthly, States, Sellers and Categories sheets, including a monthly chart, filters, frozen panes and conditional target indicators. The on-time target is 90%; amber starts at 85%. Both are illustrative. Other headline KPIs have no assigned target.

Monthly rates group by purchase month. The rolling rate combines order counts across the current and previous two calendar months rather than averaging rounded percentages. Months without eligible orders are absent; early windows can be partial. Ranking sheets include all groups with at least 100 eligible orders, while the standalone ranking SQL files return the top ten.

The report reads a consistent, read-only database snapshot and checks that monthly eligible/on-time counts reconcile with the headline counts. The uploaded sample was inspected: 87,422 eligible orders, 5,604 late orders, five sheets, one chart and no cached Excel error cells. Summary and monthly chart layouts were checked in Excel screenshots. The script passed a syntax check; the database-backed run was performed on the author's computer, not in CI.

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

This dataset has one item and one payment row per order. That is an observed property of these files, not a general e-commerce modelling assumption. Python checks report counts; the SQL setup additionally enforces the five primary keys and four foreign-key relationships.

## Limitations

This is a historical training subset, not a current operational scorecard. No review scores or carrier handover dates are supplied, so satisfaction analysis and warehouse/transit stage breakdowns are unavailable. Delivered-only metrics do not capture the experience of orders that never arrived. Small state samples and differences in product/seller mix can affect comparisons.

Payment values were observed during preliminary inspection to differ from item price plus shipping for 89,314 orders; reconciliation remains open and is not implemented in this script. No revenue or freight-share conclusions are presented.

## Repository contents

| Path | Purpose |
|---|---|
| `python/01_inspect_data.py` | Inspection, cleaning, delivery KPIs, state analysis and relationship checks |
| `python/02_load_database.py` | Initial transactional PostgreSQL load with row-count verification |
| `sql/00_keys_and_indexes.sql` | Primary keys, foreign keys and join indexes |
| `sql/01_order_performance_view.sql` | One-row-per-order delivery view |
| `sql/02_delivery_scorecard.sql` | SQL headline KPI query |
| `sql/03_state_performance.sql` | State comparison with a minimum order count |
| `python/03_excel_report.py` | Regenerate the Excel workbook from PostgreSQL |
| `sql/04_monthly_performance.sql` | Monthly and weighted three-month on-time rates |
| `sql/05_seller_performance.sql` | Seller late-rate ranking |
| `sql/06_category_performance.sql` | Category performance ranking |
| `excel_output/delivery_scorecard.xlsx` | Sample generated report |
| `requirements.txt` | Analysis, database and Excel dependencies |
| `data/raw/README.md` | Local dataset placement instructions |
| `docs/phase1_output.txt` | Reproduced console results |

## Next steps

- Add a persistent quality log and a controlled refresh process for existing database tables.
- Build a Power BI dashboard and document additional findings.
