WITH ref_stg_olist__customers AS (
    SELECT * 
    FROM {{ ref('stg_olist__customers') }}
)
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
FROM ref_stg_olist__customers