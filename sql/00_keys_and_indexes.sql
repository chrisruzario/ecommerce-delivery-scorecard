-- Run once after the initial Python load, in ecommerce_delivery.
-- Primary keys for items/payments reflect this dataset's one-row-per-order structure.
BEGIN;
ALTER TABLE public.customers ADD PRIMARY KEY (customer_id);
ALTER TABLE public.products ADD PRIMARY KEY (product_id);
ALTER TABLE public.orders ADD PRIMARY KEY (order_id);
ALTER TABLE public.order_items ADD PRIMARY KEY (order_id);
ALTER TABLE public.payments ADD PRIMARY KEY (order_id);
ALTER TABLE public.orders ADD CONSTRAINT fk_orders_customer
    FOREIGN KEY (customer_id) REFERENCES public.customers (customer_id);
ALTER TABLE public.order_items ADD CONSTRAINT fk_items_order
    FOREIGN KEY (order_id) REFERENCES public.orders (order_id);
ALTER TABLE public.order_items ADD CONSTRAINT fk_items_product
    FOREIGN KEY (product_id) REFERENCES public.products (product_id);
ALTER TABLE public.payments ADD CONSTRAINT fk_payments_order
    FOREIGN KEY (order_id) REFERENCES public.orders (order_id);
CREATE INDEX idx_orders_customer ON public.orders (customer_id);
CREATE INDEX idx_items_product ON public.order_items (product_id);
COMMIT;

-- Expected: five primary keys and four foreign keys.
SELECT table_name, constraint_type, constraint_name
FROM information_schema.table_constraints
WHERE table_schema = 'public'
  AND constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY')
ORDER BY table_name, constraint_type;
