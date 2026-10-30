# Olist Analytics Engineering

![Olist Executive Dashboard](images/olist_dashboard.png)

## 📊 Interactive Data Lineage
[Click here to view the interactive dbt Docs & Lineage Graph](https://wahyudirobbysutanto.github.io/olist-analytics-engineering/)

![dbt Lineage Graph](images/dbt_docs_lineage.png)

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

| Layer | Tool |
|---|---|
| Ingestion | Python (pandas, SQLAlchemy) |
| Warehouse | PostgreSQL |
| Transformation | dbt-core + dbt-postgres |
| Orchestration | Prefect 3.x (Phase 3) |
| Data Quality | dbt tests + source freshness |
| CI/CD | GitHub Actions (Phase 3) |
| AI Agent | Streamlit, LangChain, Groq/Gemini |

## Project Structure
```text
olist-analytics/
├── ingestion/          # CSV → PostgreSQL raw schema
├── dbt_project/
│   ├── models/         # staging, marts (star schema)
│   │   ├── staging/    # 1:1 with sources, minimal transforms
│   │   └── marts/      # star schema (dim_*, fact_*)
│   ├── snapshots/      # SCD Type 2 history tracking
│   └── tests/          # custom data tests
├── ai_agent/           # Streamlit AI Data Analyst (Text-to-SQL)
├── sql_script/         # Database setup scripts (Read-only user & AI history)
├── data/               # local only, gitignored (see Data Setup)
├── images/             # Dashboard screenshots for README
└── .github/workflows/  # CI/CD (GitHub Actions)
```

## Data Setup

CSV files are not committed to this repo (too large). Download from 
[Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) 
and place in `data/`:
```text
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

## Roadmap

- [x] **Phase 1: Staging Layer** (Orders, Customers)
- [x] **Phase 2: Star Schema** (Add Products, Order Items, Dims, Facts)
- [x] **Phase 3: Complete Marts & CI/CD** (Sellers, Payments, GitHub Actions)
- [x] **Phase 4: Business Intelligence** (Metabase Dashboard & Data Visualization)
- [x] **Phase 5A: Advanced Modeling** (Snapshots / SCD Type 2)
- [x] **Phase 5B: AI Agent Layer** (Auto-Insights & Text-to-SQL)
- [x] **Phase 5C: Data Lineage & Documentation** (dbt Docs hosted on GitHub Pages)
- [ ] **Phase 6: Cloud Migration** (BigQuery/Snowflake)

Progress is tracked via pull requests — each phase is a PR with design decisions and trade-offs documented.

## Design Decisions

*(Updated as phases complete. See PRs for full context.)*

### Why sources, not seeds, for large CSVs?

dbt seeds reload the full file on every build and don't support incremental loading. Files >1k rows belong in an ingestion script and are declared as sources.

### Why staging views, marts tables?

Staging models are cheap transformations (renames, casts) — views avoid redundant storage. Marts are queried by BI tools and benefit from materialization (tables).

### Why TRUNCATE CASCADE instead of DROP TABLE in ingestion?

When re-running the Python ingestion script, a standard `DROP TABLE` fails because dbt views depend on the raw tables. We use a conditional `TRUNCATE ... CASCADE` to clear data safely without breaking the downstream dbt dependencies.

### Why Fact Table grain is at `order_item` level?

One order can contain multiple items. To analyze product categories and freight values accurately, the `fact_orders` table must be at the `order_item` grain (112,650 rows), joined to `dim_products` and `dim_customers` (Star Schema).

### Why implement SCD Type 2 (dbt Snapshots) for products?

Product categories can change over time. If we use a standard dbt model (which drops and recreates the table), historical transactions would incorrectly reflect the new category, causing inaccurate past reports. We use `dbt snapshot` to track history (SCD Type 2) so we can see what a product's category was at any given point in time.

### How to handle fan-out in fact tables with SCD Type 2?

When joining a fact table with an SCD Type 2 dimension, a standard join would multiply the rows (fan-out) because a single `product_id` can exist multiple times in the dimension table. To prevent this, we implement a **Point-in-Time Join** in `fact_orders`:

```sql
INNER JOIN dim_products p 
  ON oi.product_id = p.product_id 
  AND o.order_purchase_timestamp >= p.dbt_valid_from 
  AND (o.order_purchase_timestamp < p.dbt_valid_to OR p.dbt_valid_to IS NULL)
```

This ensures that each transaction is joined ONLY to the product version that was active at the exact moment the order was placed, preserving data accuracy and revenue totals.

## 🤖 Phase 5B: The AI Data Analyst Agent

To push the boundaries of modern Data Engineering, I integrated an **Agentic AI Layer** on top of the dbt data warehouse. 

### Features:
- **Text-to-SQL Engine:** Users can ask business questions in plain English, and the AI (powered by Gemini & Groq) writes and executes the SQL.
- **Self-Correction QA Loop:** Implements a dual-agent architecture. AI 1 generates the SQL; AI 2 (QA) validates the results. If AI 2 rejects the SQL, it feeds the error back to AI 1 for automatic correction (up to 3 retries).
- **Dynamic Schema Introspection:** The AI dynamically reads the PostgreSQL `information_schema` so it always knows the latest tables and columns without hardcoding.
- **Smart Visualizations:** The AI determines the best chart type (bar, line, area) based on the data returned.
- **Multi-Provider Resiliency:** Built with LangChain `with_fallbacks`, ensuring high availability by automatically switching from Google Gemini to Groq (Llama 3.3) if rate limits are hit.
- **Interactive History:** All queries and auto-generated insights are saved to PostgreSQL and can be re-run from an interactive UI.

### How to Run:
1. Create the read-only AI user and history tables by running `sql_script/create_read_only_user.sql`.
2. Add your `GEMINI_API_KEY` and `GROQ_API_KEY` to `.env`.
3. Run the Streamlit app:
```bash
streamlit run ai_agent/app.py
```


## License

MIT — see [LICENSE](LICENSE).

## Author

**Wahyudi Robby Sutanto** — Analytics Engineer
- LinkedIn: [LinkedIn](https://www.linkedin.com/in/wahyudirs/)

