WITH ref_stg_olist__customers AS (
    SELECT * 
    FROM {{ ref('customers_snapshot') }}
)
SELECT
    {{ dbt_utils.generate_surrogate_key(['customer_id', 'dbt_valid_from']) }} AS customer_sk,
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    dbt_valid_from,
    dbt_valid_to
FROM ref_stg_olist__customers