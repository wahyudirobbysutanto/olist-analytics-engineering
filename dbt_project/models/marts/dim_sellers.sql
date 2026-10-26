WITH ref_stg_olist__sellers AS (
    SELECT *
    FROM {{ ref('stg_olist__sellers') }}
)
SELECT 
    seller_id,
    seller_city,
    seller_state
FROM ref_stg_olist__sellers