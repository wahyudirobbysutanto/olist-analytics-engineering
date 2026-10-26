WITH src_olist_order_items AS (
    SELECT *
    FROM {{ source('olist', 'order_items')}}
)
SELECT
    order_id,
    order_item_id,
    product_id,
    seller_id,
    CAST(shipping_limit_date AS TIMESTAMP) AS shipping_limit_date,
    price,
    freight_value
FROM src_olist_order_items
