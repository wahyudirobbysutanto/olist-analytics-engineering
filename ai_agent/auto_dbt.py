import argparse
import os
import urllib.parse
import subprocess
import json
import yaml
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables from .env file
load_dotenv()

# Parse database credentials securely
DB_USER = urllib.parse.quote_plus(os.getenv("DBT_AGENT_USER", "dbt_agent_user"))
DB_PASS = urllib.parse.quote_plus(os.getenv("DBT_AGENT_PASSWORD", "dbt_agent_password_123"))
DB_HOST = urllib.parse.quote_plus(os.getenv("POSTGRES_HOST", "localhost"))
DB_PORT = urllib.parse.quote_plus(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = urllib.parse.quote_plus(os.getenv("POSTGRES_DATABASE", "olist_warehouse"))

DB_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URI)

# Initialize LLM
primary_llm = ChatGroq(
    model=os.getenv("GROQ_MODEL_LLM", "openai/gpt-oss-120b"), 
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY")
)
fallback_llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL_LLM", "gemini-2.5-flash"),
    temperature=0,
    api_key=os.getenv("GEMINI_API_KEY")
)
llm = primary_llm.with_fallbacks([fallback_llm], exceptions_to_handle=(Exception,))

def clean_json(text):
    """Strips markdown code block formatting from the AI response."""
    return text.replace("```json", "").replace("```", "").strip()

def get_source_name():
    """Reads the dbt source name dynamically from the _olist__sources.yml file."""
    sources_path = Path("dbt_project/models/staging/olist/_olist__sources.yml")
    if sources_path.exists():
        with open(sources_path, 'r') as f:
            data = yaml.safe_load(f)
            if data and 'sources' in data and len(data['sources']) > 0:
                return data['sources'][0]['name']
    return "raw"

def generate_staging():
    """Generates dbt staging models and YAML tests for all raw tables."""
    print("🤖 Running Staging Generator Module...")
    source_name = get_source_name()
    print(f"🔗 Detected dbt source name: {source_name}")
    
    query_tables = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw';"
    with engine.connect() as conn:
        tables = [row[0] for row in conn.execute(text(query_tables)).fetchall()]
    
    print(f"📊 Found {len(tables)} tables in raw schema: {tables}")

    for table_name in tables:
        print(f"\n--- Processing raw.{table_name} ---")
        query_cols = f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'raw' AND table_name = '{table_name}' ORDER BY ordinal_position;"
        with engine.connect() as conn:
            cols = conn.execute(text(query_cols)).fetchall()
        
        schema_info = ", ".join([f"{c[0]} ({c[1]})" for c in cols])
        
        prompt = f"""
        You are a Senior Analytics Engineer. 
        Based on this raw table schema: {table_name} ({schema_info}).
        
        Task 1: Write a dbt staging SQL model. Name it `stg_olist__{table_name}.sql`.
        - CRITICAL RULE 1: You MUST use exactly this syntax to reference the table: {{{{ source('{source_name}', '{table_name}') }}}}
        - CRITICAL RULE 2: NEVER end your SQL code with a semicolon (;).
        - CRITICAL RULE 3: You MUST SELECT ALL columns present in the raw table schema.
        - CRITICAL RULE 4: If you CAST a column (e.g., `CAST(date_col AS TIMESTAMP)`), you MUST keep the EXACT SAME column name as an alias (e.g., `AS date_col`).
        - Use a WITH statement. Do NOT write business logic.
        
        Task 2: Write the dbt schema.yml test for this model.
        - CRITICAL RULE 5: ONLY use the `unique` test on the absolute Primary Key of the table.
        - CRITICAL RULE 6: NEVER put a `unique` test on foreign keys or sequence IDs. 
        - WARNING FOR SPECIFIC TABLES: In `payments` and `order_items`, the `order_id` is a Foreign Key (NOT unique). In `order_items`, `order_item_id` is a Sequence ID (NOT unique). ONLY apply `not_null` to these.
        - CRITICAL RULE 7: Do NOT put `not_null` tests on date columns that represent status-dependent milestones (like delivery dates), as orders can be pending/canceled. ONLY apply `not_null` to Primary Keys, Foreign Keys, and guaranteed fields (like price).
        
        Return ONLY valid JSON format:
        {{"sql": "SELECT ...", "yaml": "version: 2\\nmodels:\\n  - name: ..."}}
        """
        
        print(f"🧠 AI is writing the SQL and YAML for {table_name}...")
        try:
            response = llm.invoke(prompt).content
            result = json.loads(clean_json(response))
            
            base_dir = Path("dbt_project/models/staging/olist")
            base_dir.mkdir(parents=True, exist_ok=True)
            
            sql_path = base_dir / f"stg_olist__{table_name}.sql"
            yml_path = base_dir / f"_stg_olist__{table_name}.yml"
            
            # FIX: Added encoding='utf-8'
            sql_path.write_text(result['sql'], encoding='utf-8')
            yml_path.write_text(result['yaml'], encoding='utf-8')
            
            print(f"✅ Successfully generated: {sql_path.name} & {yml_path.name}")
        except Exception as e:
            print(f"❌ Failed to generate for {table_name}: {e}")

def auto_heal(target_selector="staging", max_retries=3):
    """Runs dbt build, catches errors, and asks the AI to fix them."""
    print(f"\n🩺 Running Auto-Healing Loop for: {target_selector}...")
    source_name = get_source_name()
    
    sources_path = Path("dbt_project/models/staging/olist/_olist__sources.yml")
    sources_content = sources_path.read_text(encoding='utf-8') if sources_path.exists() else "No sources.yml found"

    staging_files = [f.name for f in Path("dbt_project/models/staging/olist").glob("*") if f.is_file()]
    snapshot_files = [f.name for f in Path("dbt_project/snapshots").glob("*") if f.is_file()]
    available_files = staging_files + snapshot_files

    for attempt in range(1, max_retries + 1):
        print(f"\n--- Healer Attempt {attempt} of {max_retries} ---")
        
        cmd = ["dbt", "build"]
        if target_selector != "all":
            cmd.extend(["--select", f"+{target_selector}"])
            
        result = subprocess.run(cmd, cwd="dbt_project", capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ dbt build SUCCESS! Target '{target_selector}' is valid.")
            return

        print("❌ dbt build FAILED. AI is analyzing the error...")
        error_log = result.stdout + result.stderr
        
        print("\n--- Raw Error Output ---")
        print("\n".join(error_log.split("\n")[-20:]))
        print("------------------------\n")

        heal_prompt = f"""
        You are a Senior Analytics Engineer. The dbt build failed.
        
        Error Log:
        {error_log[-2500:]} (showing last 2500 chars)
        
        Here are the ONLY files available in the project:
        {available_files}
        
        Source Context:
        {sources_content}
        
        Identify which file is causing the issue and fix it.
        Remember:
        - Use `{{{{ source('{source_name}', 'table_name') }}}}`.
        - NEVER use semicolons (;) at the end of SQL.
        - `check_cols` in snapshot MUST be `'all'` (string), not `['all']` (list).
        - If a test failed due to `unique`, analyze the column. If it is a Sequence ID or a Foreign Key (like `order_id` in `payments` or `order_item_id` in `order_items`), REMOVE the `unique` test. ONLY Primary Keys should have `unique` tests.
        Respond ONLY in valid JSON format:
        - CRITICAL FOR SNAPSHOTS: If you are fixing a snapshot file, you MUST use Jinja syntax: {{% snapshot name %}} {{{{ config(...) }}}} {{% endsnapshot %}}. NEVER use JSON format. NEVER change the strategy to 'timestamp'. ALWAYS use strategy='check' and check_cols='all'.
        {{"file_path": "filename.extension", "corrected_content": "The new fixed code here"}}
        """
        
        print("🧠 AI is deciding which file to fix...")
        try:
            response = llm.invoke(heal_prompt).content
            result_json = json.loads(clean_json(response))
            
            if isinstance(result_json, list):
                result_json = result_json[0]
                
            file_name = Path(result_json['file_path']).name
            
            file_path = Path("dbt_project/snapshots") / file_name
            if not file_path.exists():
                file_path = Path("dbt_project/models/staging/olist") / file_name

            if file_path.exists():
                # FIX: Added encoding='utf-8'
                file_path.write_text(result_json['corrected_content'], encoding='utf-8')
                print(f"✅ AI has updated the file: {file_path}")
            else:
                print(f"⚠️ AI tried to fix a file that doesn't exist: {file_name}")
        except Exception as e:
            print(f"❌ Auto-healing failed: {e}")
            break
            
    print("\n⚠️ Max retries reached. Please check the errors manually.")

def generate_snapshot():
    """Generates SCD Type 2 snapshot SQL files for specified staging models."""
    print("\n🕰️ Running Snapshot Generator Module...")
    
    snapshot_models_str = os.getenv("SNAPSHOT_MODELS", "")
    if not snapshot_models_str:
        print("⚠️ No SNAPSHOT_MODELS defined in .env. Skipping.")
        return
        
    snapshot_models = [model.strip() for model in snapshot_models_str.split(",") if model.strip()]
    print(f"📋 Found {len(snapshot_models)} models to snapshot: {snapshot_models}")

    for model_name in snapshot_models:
        print(f"\n--- Processing snapshot for {model_name} ---")
        
        snapshot_base_name = model_name.replace("stg_olist__", "") + "_snapshot"
        
        prompt = f"""
        You are a Senior Analytics Engineer.
        Write a dbt snapshot SQL file for the model `{model_name}`.
        
        You MUST follow this EXACT TEMPLATE. Do not change the syntax:
        
        {{% snapshot {snapshot_base_name} %}}
        {{{{
            config(
                target_schema='snapshots',
                unique_key='YOUR_PRIMARY_KEY_HERE',
                strategy='check',
                check_cols='all'
            )
        }}}}
        
        SELECT * FROM {{{{ ref('{model_name}') }}}}
        
        {{% endsnapshot %}}
        
        CRITICAL RULES:
        1. Replace 'YOUR_PRIMARY_KEY_HERE' with the actual primary key (e.g., customer_id, product_id, seller_id).
        2. check_cols MUST be exactly 'all' (a single string), NEVER a list like ['all'].
        
        Return ONLY the raw SQL code. No markdown, no explanations.
        """
        
        print(f"🧠 AI is writing the Snapshot SQL for {model_name}...")
        try:
            response = llm.invoke(prompt).content
            sql_content = response.replace("```sql", "").replace("```", "").strip()
            
            base_dir = Path("dbt_project/snapshots")
            base_dir.mkdir(parents=True, exist_ok=True)
            
            snapshot_path = base_dir / f"{snapshot_base_name}.sql"
            # FIX: Added encoding='utf-8'
            snapshot_path.write_text(sql_content, encoding='utf-8')
            print(f"✅ Successfully generated: {snapshot_path.name}")
            
        except Exception as e:
            print(f"❌ Failed to generate snapshot for {model_name}: {e}")

def generate_marts_docs():
    """Reads Marts SQL files and generates schema.yml tests and documentation."""
    print("\n📝 Running Marts Documentation Module...")
    
    marts_dir = Path("dbt_project/models/marts")
    if not marts_dir.exists():
        print("⚠️ Marts directory not found.")
        return
        
    sql_files = list(marts_dir.glob("*.sql"))
    if not sql_files:
        print("⚠️ No SQL files found in marts directory.")
        return
        
    print(f"📋 Found {len(sql_files)} Marts models to document.")

    for sql_file in sql_files:
        model_name = sql_file.stem
        print(f"\n--- Processing Marts model: {model_name} ---")
        
        sql_content = sql_file.read_text(encoding='utf-8')
        
        # We avoid using markdown backticks inside the prompt string to prevent Python syntax errors
        prompt = f"""
        You are a Senior Analytics Engineer.
        I have a dbt model named `{model_name}` with the following SQL code:
        
        {sql_content}
        
        Task: Read the final SELECT statement of this SQL code and generate a dbt schema.yml file for it.
        
        CRITICAL RULES:
        1. ONLY include columns that are actually outputted in the final SELECT statement.
        2. If the model name starts with fct_ or fact_, the Primary Key might be a composite key (e.g., order_id + order_item_id). Do NOT put unique on order_id alone if it's a fact table; only put not_null.
        3. If the model name starts with dim_, put unique and not_null on the surrogate key (e.g., product_sk, customer_sk) and the natural ID (e.g., product_id).
        4. Add relationships tests for foreign keys (e.g., customer_id referencing dim_customers, product_id referencing dim_products).
        5. Include a short description for the model and for each column based on the SQL logic.
        
        Return ONLY valid YAML format (no markdown, no explanations).
        """
        
        print(f"🧠 AI is generating documentation and tests for {model_name}...")
        try:
            response = llm.invoke(prompt).content
            yaml_content = response.replace("```yaml", "").replace("```", "").strip()
            
            yml_path = marts_dir / f"_{model_name}.yml"
            yml_path.write_text(yaml_content, encoding='utf-8')
            
            print(f"✅ Successfully generated: {yml_path.name}")
            
        except Exception as e:
            print(f"❌ Failed to generate docs for {model_name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Olist AI Co-Pilot for dbt")
    parser.add_argument("--mode", choices=["staging", "snapshots", "heal", "marts", "all"], required=True)
    args = parser.parse_args()

    print(f"🚀 Starting Auto-DBT Agent in mode: {args.mode.upper()}")
    
    if args.mode == "staging":
        generate_staging()
        auto_heal(target_selector="staging")
    elif args.mode == "snapshots":
        generate_snapshot()
        auto_heal(target_selector="snapshots")
    elif args.mode == "heal":
        auto_heal(target_selector="all")
    elif args.mode == "marts":
        generate_marts_docs()
        auto_heal(target_selector="marts")
    elif args.mode == "all":
        generate_staging()
        auto_heal(target_selector="staging")
        generate_snapshot()
        auto_heal(target_selector="snapshots")
        generate_marts_docs()
        auto_heal(target_selector="marts")