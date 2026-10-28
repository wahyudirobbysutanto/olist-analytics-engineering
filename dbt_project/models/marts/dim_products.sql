WITH ref_products_snapshot AS (
    SELECT * FROM {{ ref('products_snapshot') }}
)
SELECT
    dbt_scd_id,
    product_id, 
    product_category_name, 
    product_weight_g, 
    product_length_cm, 
    product_height_cm, 
    product_width_cm,
    dbt_valid_from,
    dbt_valid_to
FROM ref_products_snapshot