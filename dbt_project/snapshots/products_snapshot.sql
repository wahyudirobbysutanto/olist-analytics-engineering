{% snapshot products_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='product_id',
        strategy='check',
        check_cols='all'
    )
}}

SELECT * FROM {{ ref('stg_olist__products') }}

{% endsnapshot %}