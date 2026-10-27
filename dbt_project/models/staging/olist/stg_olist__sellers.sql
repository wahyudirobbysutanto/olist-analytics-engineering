WITH src_sellers AS (
    SELECT *
    FROM {{ source('olist', 'sellers') }}
)
SELECT
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
FROM src_sellers