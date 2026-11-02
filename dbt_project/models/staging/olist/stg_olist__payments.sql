WITH source_data AS (
    SELECT
        order_id,
        payment_sequential,
        payment_type,
        payment_installments,
        payment_value
    FROM {{ source('olist', 'payments') }}
)
SELECT *
FROM source_data