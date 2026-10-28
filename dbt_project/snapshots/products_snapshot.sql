{% snapshot products_snapshot %} 

{{
    config(
        target_schema="snapshots",
        unique_key="product_id",
        strategy="check",
        check_cols=["product_category_name"]
    )
}}

SELECT * FROM {{ source('olist', 'products') }}

{% endsnapshot %}