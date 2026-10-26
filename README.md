# Olist Analytics Engineering

Production-style analytics engineering project built on the 
[Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). 
Demonstrates end-to-end ELT with dbt, PostgreSQL, and Prefect — including 
staging layer design, star schema modeling, data quality tests, and 
orchestrated ingestion.

## Why This Project

Most dbt portfolio projects stop at "it runs". This project focuses on 
the questions that matter in production:

- How do you handle schema drift from upstream sources?
- When does a dbt test fail vs. error, and why does the distinction matter?
- How does grain affect fact table design as new sources arrive?
- What does "production-ready" mean beyond green tests?


## Stack
```
| Layer | Tool |
|---|---|
| Ingestion | Python (pandas, SQLAlchemy) |
| Warehouse | PostgreSQL |
| Transformation | dbt-core + dbt-postgres |
| Orchestration | Prefect 3.x |
| Data Quality | dbt tests + source freshness |
| CI | GitHub Actions (phase 2) |
```
## Project Structure
```
olist-analytics/
├── ingestion/ # CSV → PostgreSQL raw schema
├── dbt_project/
│ ├── models/
│ │ ├── staging/ # 1:1 with sources, minimal transforms
│ │ └── marts/ # star schema (dim_, fact_)
│ └── tests/ # custom data tests
├── data/ # local only, gitignored (see Data Setup)
└── .github/workflows/ # CI (phase 2)
```

## Data Setup

CSV files are not committed to this repo (too large). Download from 
[Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) 
and place in `data/`:
```
data/
├── olist_orders_dataset.csv
├── olist_customers_dataset.csv
├── olist_order_items_dataset.csv
├── olist_products_dataset.csv
├── olist_sellers_dataset.csv
├── olist_payments_dataset.csv
├── olist_reviews_dataset.csv
├── olist_geolocation_dataset.csv
└── product_category_name_translation.csv
```

Then run:

```bash
python ingestion/load_csv_to_postgres.py
cd dbt_project && dbt build
```