# -*- coding: utf-8 -*-
"""
Created on Thu Nov 12 13:54:18 2026

@author: chrisruzario
"""

from pathlib import Path
import pandas as pd

# Find the project folder from this script's location.
PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"

# Load identifiers as text to preserve IDs and leading zeros.
orders = pd.read_csv(
    RAW_DIR / "df_Orders.csv",
    dtype={"order_id": "string", "customer_id": "string"}
)

items = pd.read_csv(
    RAW_DIR / "df_OrderItems.csv",
    dtype={
        "order_id": "string",
        "product_id": "string",
        "seller_id": "string"
    }
)

customers = pd.read_csv(
    RAW_DIR / "df_Customers.csv",
    dtype={
        "customer_id": "string",
        "customer_zip_code_prefix": "string"
    }
)

products = pd.read_csv(
    RAW_DIR / "df_Products.csv",
    dtype={"product_id": "string"}
)

payments = pd.read_csv(
    RAW_DIR / "df_Payments.csv",
    dtype={"order_id": "string"}
)

# Group the tables so we can inspect them with one loop.
tables = {
    "orders": orders,
    "items": items,
    "customers": customers,
    "products": products,
    "payments": payments
}

for name, df in tables.items():
    print(f"\n--- {name.upper()} ---")
    print(f"Rows: {df.shape[0]:,} | Columns: {df.shape[1]}")
    print("Duplicate rows:", df.duplicated().sum())
    print("Missing values:")
    print(df.isna().sum())

print("\nORDER STATUS COUNTS")
print(orders["order_status"].value_counts(dropna=False))

# Check which order statuses have missing delivery dates.
print("\nMISSING DELIVERY DATES BY STATUS")

missing_delivery = orders["order_delivered_timestamp"].isna()

print(
    orders.loc[missing_delivery, "order_status"]
    .value_counts()
)


# Remove exact duplicate product rows in a separate copy.
products_clean = products.drop_duplicates().copy()

print("\nPRODUCT DUPLICATE CHECK")
print("Original rows:", len(products))
print("After removing exact duplicates:", len(products_clean))

# Each product ID should identify one product record.
remaining_duplicate_ids = products_clean["product_id"].duplicated().sum()

print("Remaining duplicate product IDs:", remaining_duplicate_ids)


# Check missing values again after removing duplicate rows.
print("\nMISSING VALUES IN UNIQUE PRODUCT RECORDS")
print(products_clean.isna().sum())

# Keep the original orders unchanged.
orders_clean = orders.copy()

date_columns = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_timestamp",
    "order_estimated_delivery_date"
]

print("\nDATE CONVERSION CHECK")

for column in date_columns:
    original = orders_clean[column]

    converted = pd.to_datetime(original, errors="coerce")

    # Count values that existed but could not be read as dates.
    invalid_count = (original.notna() & converted.isna()).sum()

    print(f"{column}: {invalid_count} invalid date values")
    orders_clean[column] = converted


# Flag delivery dates earlier than purchase.
delivery_before_purchase = (
    orders_clean["order_delivered_timestamp"]
    < orders_clean["order_purchase_timestamp"]
)

print(
    "\nDelivery before purchase:",
    delivery_before_purchase.sum()
)


# Define eligibility for our delivery scorecard.
required_dates_present = orders_clean[
    [
        "order_purchase_timestamp",
        "order_delivered_timestamp",
        "order_estimated_delivery_date"
    ]
].notna().all(axis=1)

orders_clean["delivery_kpi_eligible"] = (
    orders_clean["order_status"].eq("delivered")
    & required_dates_present
    & ~delivery_before_purchase
)

delivery_orders = orders_clean.loc[
    orders_clean["delivery_kpi_eligible"]
].copy()

print("\nDELIVERY KPI ELIGIBILITY")
print("All orders:", len(orders_clean))
print("Eligible orders:", len(delivery_orders))
print("Excluded orders:", (~orders_clean["delivery_kpi_eligible"]).sum())

# Compare calendar dates so delivery on the promised day is on time.
actual_date = delivery_orders["order_delivered_timestamp"].dt.normalize()
estimated_date = delivery_orders["order_estimated_delivery_date"].dt.normalize()

delivery_orders["delay_days"] = (
    actual_date - estimated_date
).dt.days.clip(lower=0)

delivery_orders["is_late"] = delivery_orders["delay_days"] > 0

# Preserve fractional days for elapsed delivery time.
delivery_orders["delivery_days"] = (
    delivery_orders["order_delivered_timestamp"]
    - delivery_orders["order_purchase_timestamp"]
).dt.total_seconds() / 86400

# Calculate headline KPIs.
on_time_rate = (~delivery_orders["is_late"]).mean() * 100

average_delivery_days = delivery_orders["delivery_days"].mean()

average_late_delay = delivery_orders.loc[
    delivery_orders["is_late"], "delay_days"
].mean()

late_count = delivery_orders["is_late"].sum()

# This is a project assumption, not a target supplied by the company.
illustrative_target = 90.0

print("\nDELIVERY SCORECARD")
print(f"Eligible orders: {len(delivery_orders):,}")
print(f"Late orders: {late_count:,}")
print(f"On-time delivery rate: {on_time_rate:.2f}%")
print(f"Average delivery time: {average_delivery_days:.2f} days")
print(f"Average delay for late orders: {average_late_delay:.2f} days")
print(f"Illustrative on-time target: {illustrative_target:.0f}%")
print(f"Gap to target: {on_time_rate - illustrative_target:+.2f} percentage points")


# Attach the customer's state to each eligible order.
delivery_by_location = delivery_orders.merge(
    customers[["customer_id", "customer_state"]],
    on="customer_id",
    how="left",
    validate="many_to_one",
    indicator=True
)

print("\nCUSTOMER JOIN CHECK")
print("Rows before join:", len(delivery_orders))
print("Rows after join:", len(delivery_by_location))
print(
    "Orders without a matching customer:",
    delivery_by_location["_merge"].eq("left_only").sum()
)

# Summarise delivery performance by customer state.
state_summary = (
    delivery_by_location
    .groupby("customer_state", dropna=False)
    .agg(
        eligible_orders=("order_id", "size"),
        late_orders=("is_late", "sum"),
        average_delivery_days=("delivery_days", "mean")
    )
    .reset_index()
)

state_summary["late_rate_pct"] = (
    state_summary["late_orders"]
    / state_summary["eligible_orders"]
    * 100
)

state_summary["on_time_rate_pct"] = (
    100 - state_summary["late_rate_pct"]
)

# An illustrative minimum volume for more meaningful comparisons.
minimum_orders = 100

worst_states = (
    state_summary.loc[
        state_summary["eligible_orders"] >= minimum_orders
    ]
    .sort_values(
        ["late_rate_pct", "eligible_orders"],
        ascending=[False, False]
    )
    .head(10)
)

print("\nSTATES WITH HIGHEST LATE RATES — MINIMUM 100 ORDERS")
print(worst_states.round(2).to_string(index=False))

# Check whether the intended database keys are unique.
key_checks = [
    ("orders", orders_clean, "order_id"),
    ("customers", customers, "customer_id"),
    ("products", products_clean, "product_id"),
    ("items", items, "order_id"),
    ("payments", payments, "order_id")
]

print("\nKEY CHECKS")

for name, df, key in key_checks:
    print(
        f"{name}.{key}: "
        f"{df[key].isna().sum()} missing, "
        f"{df[key].duplicated().sum()} repeated"
    )


# Check that references point to records in the related table.
relationship_checks = [
    ("Orders → Customers",
     orders_clean["customer_id"], customers["customer_id"]),

    ("Items → Orders",
     items["order_id"], orders_clean["order_id"]),

    ("Items → Products",
     items["product_id"], products_clean["product_id"]),

    ("Payments → Orders",
     payments["order_id"], orders_clean["order_id"])
]

print("\nRELATIONSHIP CHECKS")

for label, source_ids, target_ids in relationship_checks:
    unmatched = (~source_ids.isin(target_ids)).sum()
    print(f"{label}: {unmatched} unmatched references")