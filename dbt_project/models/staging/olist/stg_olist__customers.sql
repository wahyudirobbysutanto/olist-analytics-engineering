WITH src_olist_customers AS (
    SELECT *
    FROM {{ source('olist', 'customers')}}
)
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
FROM src_olist_customers
