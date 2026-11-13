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
    month::date AS purchase_month,
    eligible_orders,

    ROUND(
        100.0 * on_time_orders / eligible_orders,
        2
    ) AS on_time_rate_pct,

    ROUND(
        100.0 * SUM(on_time_orders) OVER rolling_window
        / NULLIF(SUM(eligible_orders) OVER rolling_window, 0),
        2
    ) AS rolling_3_month_on_time_pct

FROM monthly

WINDOW rolling_window AS (
    ORDER BY month
    RANGE BETWEEN INTERVAL '2 months' PRECEDING
              AND CURRENT ROW
)

ORDER BY month;