{% snapshot sellers_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='seller_id',
        strategy='check',
        check_cols='all'
    )
}}

SELECT * FROM {{ ref('stg_olist__sellers') }}

{% endsnapshot %}