-- Expected: 87422 | 5604 | 93.59 | 12.43 | 10.45
SELECT
    COUNT(*) AS eligible_orders,
    COUNT(*) FILTER (WHERE is_late) AS late_orders,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE NOT is_late)
        / NULLIF(COUNT(*), 0), 2
    ) AS on_time_rate_pct,
    ROUND(AVG(delivery_days), 2) AS average_delivery_days,
    ROUND(
        AVG(delay_days) FILTER (WHERE is_late), 2
    ) AS average_late_delay_days
FROM public.vw_order_performance
WHERE delivery_kpi_eligible;
