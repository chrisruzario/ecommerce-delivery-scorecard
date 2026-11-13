-- One row per order; ineligible orders retain NULL delivery metrics.
CREATE OR REPLACE VIEW public.vw_order_performance AS
SELECT
    o.order_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_delivered_timestamp,
    o.order_estimated_delivery_date,
    o.delivery_kpi_eligible,
    c.customer_state,
    i.seller_id,
    p.product_category_name,
    CASE WHEN o.delivery_kpi_eligible THEN
        EXTRACT(EPOCH FROM (
            o.order_delivered_timestamp - o.order_purchase_timestamp
        )) / 86400.0
    END AS delivery_days,
    CASE WHEN o.delivery_kpi_eligible THEN
        GREATEST(
            o.order_delivered_timestamp::date
            - o.order_estimated_delivery_date::date, 0
        )
    END AS delay_days,
    CASE WHEN o.delivery_kpi_eligible THEN
        o.order_delivered_timestamp::date
        > o.order_estimated_delivery_date::date
    END AS is_late
FROM public.orders AS o
LEFT JOIN public.customers AS c ON o.customer_id = c.customer_id
LEFT JOIN public.order_items AS i ON o.order_id = i.order_id
LEFT JOIN public.products AS p ON i.product_id = p.product_id;
