# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 14:26:04 2026

@author: chrisruzario
"""

from pathlib import Path
from datetime import datetime
from getpass import getpass

import pandas as pd
from sqlalchemy import create_engine, URL, text


PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "excel_output"
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "delivery_scorecard.xlsx"

# Illustrative thresholds, not company targets.
TARGET = 0.90
AMBER_THRESHOLD = 0.85
MINIMUM_ORDERS = 100

connection_url = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password=getpass("PostgreSQL password: "),
    host="localhost",
    port=5432,
    database="ecommerce_delivery"
)

engine = create_engine(
    connection_url,
    connect_args={"connect_timeout": 10}
)

summary_sql = """
SELECT
    COUNT(*) AS eligible_orders,
    COUNT(*) FILTER (WHERE is_late) AS late_orders,
    COUNT(*) FILTER (WHERE NOT is_late) AS on_time_orders,
    AVG(delivery_days) AS average_delivery_days,
    AVG(delay_days) FILTER (WHERE is_late) AS average_late_delay_days
FROM public.vw_order_performance
WHERE delivery_kpi_eligible;
"""

monthly_sql = """
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', order_purchase_timestamp) AS month,
        COUNT(*) AS eligible_orders,
        COUNT(*) FILTER (WHERE NOT is_late) AS on_time_orders
    FROM public.vw_order_performance
    WHERE delivery_kpi_eligible
    GROUP BY DATE_TRUNC('month', order_purchase_timestamp)
)
SELECT
    month AS purchase_month,
    eligible_orders,
    on_time_orders,
    1.0 * on_time_orders / eligible_orders AS on_time_rate,
    1.0 * SUM(on_time_orders) OVER rolling_window
        / NULLIF(SUM(eligible_orders) OVER rolling_window, 0)
        AS rolling_3_month_rate
FROM monthly
WINDOW rolling_window AS (
    ORDER BY month
    RANGE BETWEEN INTERVAL '2 months' PRECEDING AND CURRENT ROW
)
ORDER BY month;
"""

# These expressions are fixed by the script, not user input.
dimensions = {
    "States": "customer_state",
    "Sellers": "seller_id",
    "Categories": "product_category_name"
}

try:
    # Read all sheets from one consistent database snapshot.
    with engine.connect().execution_options(
        isolation_level="REPEATABLE READ"
    ) as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))

            summary = pd.read_sql_query(text(summary_sql), connection)
            monthly = pd.read_sql_query(text(monthly_sql), connection)

            reports = {}

            for sheet_name, column in dimensions.items():
                query = f"""
                SELECT
                    COALESCE({column}, 'Unknown') AS dimension,
                    COUNT(*) AS eligible_orders,
                    COUNT(*) FILTER (WHERE is_late) AS late_orders,
                    1.0 * COUNT(*) FILTER (WHERE is_late)
                        / COUNT(*) AS late_rate,
                    AVG(delivery_days) AS average_delivery_days,
                    AVG(delay_days) FILTER (WHERE is_late)
                        AS average_late_delay_days
                FROM public.vw_order_performance
                WHERE delivery_kpi_eligible
                GROUP BY COALESCE({column}, 'Unknown')
                HAVING COUNT(*) >= :minimum_orders
                ORDER BY late_rate DESC, eligible_orders DESC, dimension;
                """

                reports[sheet_name] = pd.read_sql_query(
                    text(query),
                    connection,
                    params={"minimum_orders": MINIMUM_ORDERS}
                )

finally:
    engine.dispose()


# Verify the monthly figures reconcile to the headline counts.
result = summary.iloc[0]
eligible = int(result["eligible_orders"])
late = int(result["late_orders"])
on_time = int(result["on_time_orders"])

if eligible == 0:
    raise ValueError("No eligible orders found. Check the database view.")

if late + on_time != eligible:
    raise ValueError("Late and on-time orders do not reconcile.")

if int(monthly["eligible_orders"].sum()) != eligible:
    raise ValueError("Monthly order counts do not match the summary.")

if int(monthly["on_time_orders"].sum()) != on_time:
    raise ValueError("Monthly on-time counts do not match the summary.")

monthly["purchase_month"] = pd.to_datetime(monthly["purchase_month"])
monthly["illustrative_target"] = TARGET


with pd.ExcelWriter(
    OUTPUT_FILE,
    engine="xlsxwriter",
    datetime_format="mmm yyyy",
    engine_kwargs={
        "options": {
            "strings_to_formulas": False,
            "strings_to_urls": False
        }
    }
) as writer:

    workbook = writer.book

    title_format = workbook.add_format({
        "bold": True, "font_size": 18, "font_color": "#172B4D"
    })
    header_format = workbook.add_format({
        "bold": True, "bg_color": "#172B4D",
        "font_color": "white", "text_wrap": True,
        "valign": "vcenter"
    })
    integer_format = workbook.add_format({"num_format": "#,##0"})
    decimal_format = workbook.add_format({"num_format": "0.00"})
    percent_format = workbook.add_format({"num_format": "0.00%"})
    note_format = workbook.add_format({
        "font_color": "#555555", "text_wrap": True, "valign": "top"
    })
    green_format = workbook.add_format({
        "bg_color": "#E2F0D9", "font_color": "#375623"
    })
    amber_format = workbook.add_format({
        "bg_color": "#FFF2CC", "font_color": "#7F6000"
    })
    red_format = workbook.add_format({
        "bg_color": "#FCE4D6", "font_color": "#9C0006"
    })

    # SUMMARY
    sheet = workbook.add_worksheet("Summary")
    writer.sheets["Summary"] = sheet

    sheet.hide_gridlines(2)
    sheet.set_column("A:A", 39)
    sheet.set_column("B:B", 20)
    sheet.set_column("C:C", 24)
    sheet.set_column("D:D", 20)

    sheet.merge_range("A1:D1", "Delivery Performance Scorecard", title_format)
    sheet.merge_range(
        "A2:D2",
        f"Historical training dataset | Generated {datetime.now():%Y-%m-%d %H:%M}",
        note_format
    )

    sheet.write_row("A4", ["Metric", "Value", "Target", "Status"], header_format)

    sheet.write("A5", "Eligible delivered orders")
    sheet.write_number("B5", eligible, integer_format)

    sheet.write("A6", "Late orders")
    sheet.write_number("B6", late, integer_format)

    sheet.write("A7", "On-time delivery rate")
    rate = on_time / eligible
    sheet.write_formula("B7", "=(B5-B6)/B5", percent_format, rate)
    sheet.write_number("C7", TARGET, percent_format)

    status = (
        "On target" if rate >= TARGET
        else "Watch" if rate >= AMBER_THRESHOLD
        else "Below threshold"
    )
    sheet.write_formula(
        "D7",
        '=IF(B7>=C7,"On target",IF(B7>=B12,"Watch","Below threshold"))',
        None,
        status
    )

    sheet.write("A8", "Average delivery time (days)")
    sheet.write_number(
        "B8", float(result["average_delivery_days"]), decimal_format
    )

    sheet.write("A9", "Average delay: late orders only (days)")
    delay = result["average_late_delay_days"]
    if pd.notna(delay):
        sheet.write_number("B9", float(delay), decimal_format)
    else:
        sheet.write("B9", "N/A")

    sheet.write("A10", "Gap to target (percentage points)")
    sheet.write_formula(
        "B10", "=(B7-C7)*100", decimal_format, (rate - TARGET) * 100
    )

    sheet.write("A12", "Illustrative amber threshold")
    sheet.write_number("B12", AMBER_THRESHOLD, percent_format)

    for formula, fmt in [
        ("=$B$7>=$C$7", green_format),
        ("=AND($B$7<$C$7,$B$7>=$B$12)", amber_format),
        ("=$B$7<$B$12", red_format)
    ]:
        sheet.conditional_format("B7:D7", {
            "type": "formula", "criteria": formula, "format": fmt
        })

    notes = [
        "Eligibility: delivered status, valid purchase/actual/estimated dates, "
        "and delivery not before purchase.",
        "On time means delivered on or before the estimated calendar date. "
        "Delivery time uses elapsed days; delay uses calendar days.",
        "Targets are illustrative. Other KPIs have no target assigned.",
        "Rankings include groups with at least 100 eligible orders. "
        "High late rates do not establish the cause of delays.",
        "Monthly results group by purchase month. Rolling rates are weighted "
        "by orders across the current and previous two calendar months. "
        "Missing months have no eligible orders; early windows may be partial.",
        "Source: Kaggle — bytadit/ecommerce-order-dataset, training files; "
        "PostgreSQL public.vw_order_performance."
    ]

    for row, note in enumerate(notes, start=14):
        sheet.merge_range(row, 0, row, 3, note, note_format)
        sheet.set_row(row, 34)

    # MONTHLY AND RANKING SHEETS
    all_reports = {"Monthly": monthly, **reports}

    for sheet_name, frame in all_reports.items():
        frame.to_excel(
            writer, sheet_name=sheet_name,
            startrow=3, index=False, header=False
        )
        ws = writer.sheets[sheet_name]
        ws.hide_gridlines(2)
        ws.freeze_panes(3, 1)
        ws.set_column(0, 0, 35)
        ws.set_column(1, len(frame.columns) - 1, 23, decimal_format)
        ws.set_row(2, 42)

        ws.write(0, 0, f"{sheet_name} Performance", title_format)

        for col, name in enumerate(frame.columns):
            label = name.replace("_", " ").title()
            ws.write(2, col, label, header_format)

            if "orders" in name:
                ws.set_column(col, col, 19, integer_format)
            elif "rate" in name or name == "illustrative_target":
                ws.set_column(col, col, 23, percent_format)

        if len(frame):
            ws.autofilter(2, 0, len(frame) + 2, len(frame.columns) - 1)

        if sheet_name != "Monthly":
            ws.write(
                1, 0,
                f"Minimum {MINIMUM_ORDERS} eligible orders; highest late rate first."
            )

    # MONTHLY LINE CHART
    monthly_sheet = writer.sheets["Monthly"]
    monthly_sheet.merge_range(
        "A2:F2",
        "Purchase-month cohorts; rolling rate weighted by order count.",
        note_format
    )
    monthly_sheet.set_row(1, 30)

    chart = workbook.add_chart({"type": "line"})
    last_row = len(monthly) + 2

    for col, label, colour in [
        (3, "Monthly on-time rate", "#4472C4"),
        (4, "Three-month rolling rate", "#172B4D"),
        (5, "Illustrative target", "#999999")
    ]:
        chart.add_series({
            "name": label,
            "categories": ["Monthly", 3, 0, last_row, 0],
            "values": ["Monthly", 3, col, last_row, col],
            "line": {"color": colour, "width": 2}
        })

    chart.set_title({"name": "On-time delivery by purchase month"})
    chart.set_x_axis({"date_axis": True, "num_format": "mmm yy"})
    chart.set_y_axis({"num_format": "0%", "min": 0, "max": 1})
    chart.set_legend({"position": "bottom"})
    chart.set_size({"width": 820, "height": 420})

    monthly_sheet.insert_chart("H3", chart)


print(f"\nReport created successfully:\n{OUTPUT_FILE}")