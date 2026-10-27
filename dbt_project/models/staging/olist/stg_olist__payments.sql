WITH src_payments AS (
    SELECT *
    FROM {{ source('olist', 'payments') }}
)
SELECT
    order_id,
    payment_sequential,
    payment_type,
    CAST(payment_installments AS DECIMAL(10,2)) AS payment_installments,
    CAST(payment_value AS DECIMAL(10,2)) AS payment_value
FROM src_payments