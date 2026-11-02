WITH ref_stg_olist__sellers AS (
    SELECT *
    FROM {{ ref('sellers_snapshot') }}
)
SELECT 
    {{ dbt_utils.generate_surrogate_key(['seller_id', 'dbt_valid_from']) }} AS seller_sk,
    seller_id,
    seller_city,
    seller_state,
    dbt_valid_from,
    dbt_valid_to
FROM ref_stg_olist__sellers