WITH olist__order_items AS (
    SELECT * FROM {{ ref('stg_olist__order_items') }}
),
olist__orders AS (
    SELECT * FROM {{ ref('stg_olist__orders') }}
),
dim_customers AS (
    SELECT * FROM {{ ref('dim_customers') }}
),
dim_products AS (
    SELECT * FROM {{ ref('dim_products') }}
),
dim_sellers AS (
    SELECT * FROM {{ ref('dim_sellers') }}
)
SELECT
    o.order_id,
    oi.order_item_id,
    s.seller_id,
    s.seller_city,
    s.seller_state,
    o.customer_id,
    c.customer_city,
    c.customer_state,
    oi.product_id,
    p.product_category_name,
    o.order_status,
    o.order_purchase_timestamp,
    oi.price,
    oi.freight_value,
    oi.price+oi.freight_value AS total_amount 
FROM olist__order_items oi
INNER JOIN olist__orders o ON o.order_id = oi.order_id
INNER JOIN dim_customers c ON o.customer_id = c.customer_id
INNER JOIN dim_products p ON oi.product_id = p.product_id
    AND o.order_purchase_timestamp >= p.dbt_valid_from 
    AND (o.order_purchase_timestamp < p.dbt_valid_to OR p.dbt_valid_to IS NULL)
INNER JOIN dim_sellers s ON oi.seller_id = s.seller_id