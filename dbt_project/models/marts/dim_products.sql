WITH ref_stg_olist__products AS (
    SELECT * FROM {{ ref('stg_olist__products') }}
)
SELECT
    product_id, 
    product_category_name, 
    product_weight_g, 
    product_length_cm, 
    product_height_cm, 
    product_width_cm
FROM ref_stg_olist__products