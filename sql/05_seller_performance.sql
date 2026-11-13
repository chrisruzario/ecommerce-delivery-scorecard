SELECT
    seller_id,
    COUNT(*) AS eligible_orders,
    COUNT(*) FILTER (WHERE is_late) AS late_orders,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_late)
        / COUNT(*),
        2
    ) AS late_rate_pct,

    ROUND(
        AVG(delay_days) FILTER (WHERE is_late),
        2
    ) AS average_late_delay_days

FROM public.vw_order_performance

WHERE delivery_kpi_eligible
  AND seller_id IS NOT NULL

GROUP BY seller_id

HAVING COUNT(*) >= 100

ORDER BY late_rate_pct DESC, eligible_orders DESC, seller_id

LIMIT 10;