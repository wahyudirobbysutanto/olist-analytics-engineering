WITH ref_stg_olist__payments AS (
    SELECT *
    FROM {{ ref('stg_olist__payments') }}
)
SELECT 
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
FROM ref_stg_olist__payments