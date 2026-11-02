{% snapshot customers_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='customer_id',
        strategy='check',
        check_cols='all'
    )
}}

SELECT * FROM {{ ref('stg_olist__customers') }}

{% endsnapshot %}