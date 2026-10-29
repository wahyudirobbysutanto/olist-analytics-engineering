import streamlit as st
import pandas as pd
import json
import time
from sqlalchemy import create_engine, text
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
import os

# 1. MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="Olist AI Analyst", layout="wide", page_icon="🤖")

# 2. Load Environment Variables & Setup Database
load_dotenv()
DB_USER = os.getenv("AI_DB_USER", "ai_agent_user")
DB_PASS = os.getenv("AI_DB_PASSWORD", "ai_password_123")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DATABASE", "olist_warehouse")
DB_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URI)

# 3. Setup LLMs (Primary & Fallback)
# Primary LLM (Groq)
primary_llm = ChatGroq(
    model=os.getenv("GROQ_MODEL_LLM", "openai/gpt-oss-120b"), 
    temperature=0, 
    groq_api_key=os.getenv("GROQ_API_KEY"),
    max_retries=0
)

# Fallback LLM (Gemini)
fallback_llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL_LLM", "gemini-2.5-flash"), 
    temperature=0, 
    api_key=os.getenv("GEMINI_API_KEY"),
    max_retries=2
)

# Combine with fallback mechanism
llm = primary_llm.with_fallbacks(
    [fallback_llm], 
    exceptions_to_handle=(Exception,) 
)

# 4. Dynamic Schema Introspection
@st.cache_data(ttl=3600)
def get_dynamic_schema():
    query = """
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'analytics_marts' AND LEFT(table_name, 3) != 'ai_'
        ORDER BY table_name, ordinal_position;
    """
    with engine.connect() as conn:
        rows = conn.execute(text(query)).fetchall()
    
    schema_text = "Available Tables:\n"
    current_table = ""
    for row in rows:
        full_table = f"{row[0]}.{row[1]}"
        if full_table != current_table:
            if current_table != "": schema_text += ")\n"
            schema_text += f"- {full_table} ("
            current_table = full_table
        else:
            schema_text += ", "
        schema_text += f"{row[2]}"
    schema_text += ")\n"
    return schema_text

SCHEMA = get_dynamic_schema()

# 5. Helper Functions
def clean_json(text):
    """Removes markdown backticks from AI response to safely parse JSON."""
    return text.replace("```json", "").replace("```", "").strip()

def render_chart(df, chart_type):
    """Dynamically renders the chart, auto-pivoting 3-column data and ignoring text columns."""
    if df.empty or len(df.columns) < 2:
        return st.dataframe(df)
    
    # --- SMART PIVOT LOGIC ---
    # If there are 3 columns (e.g., Date, Category, Number), pivot to create multi-line charts
    if len(df.columns) == 3 and df[df.columns[1]].dtype == 'object':
        try:
            # Index = Date, Columns = Category, Values = Number
            chart_data = df.pivot_table(
                index=df.columns[0], 
                columns=df.columns[1], 
                values=df.columns[2], 
                aggfunc='sum'
            )
        except Exception:
            # If pivot fails (e.g., duplicates), fallback to standard mode
            chart_data = df.set_index(df.columns[0])
    else:
        # Standard mode (2 columns or multiple numeric columns)
        chart_data = df.set_index(df.columns[0])
    
    # Only select numeric columns for plotting to prevent "mixed types" errors
    chart_data = chart_data.select_dtypes(include=['number', 'float', 'int'])
    
    if chart_data.empty:
        return st.dataframe(df)

    # Render Chart
    if chart_type == "line":
        st.line_chart(chart_data)
    elif chart_type == "area":
        st.area_chart(chart_data)
    elif chart_type == "bar":
        st.bar_chart(chart_data)
    else:
        st.dataframe(df) # Fallback to table

def generate_valid_sql(question, max_retries=3):
    """AI 1 generates SQL -> Executes -> AI 2 Validates. If fail, loop back with feedback."""
    feedback = "None"
    
    for attempt in range(max_retries):
        # AI 1: Generate SQL & Chart Type
        sql_prompt = f"""
        You are a PostgreSQL expert. Write a SQL query for the question.
        Schema: {SCHEMA}
        Question: {question}
        Feedback from previous attempt: {feedback}
        
        CRITICAL RULES for Charting:
        1. If the user asks for "products" or "items" in general, group by `product_category_name` instead of `product_id` to make the chart readable.
        2. Avoid using long IDs (like UUIDs or hashes) as the X-axis for charts.
        
        Return ONLY valid JSON:
        {{"sql": "SELECT ...", "chart_type": "bar|line|area|table"}}
        """
        try:
            res1 = json.loads(clean_json(llm.invoke(sql_prompt).content))
            sql = res1['sql']
            chart_type = res1.get('chart_type', 'table')
            
            # Execute SQL
            df = pd.read_sql(sql, engine)
            
            # AI 2: QA Validation
            qa_prompt = f"""
            You are a QA Data Engineer. 
            User Question: {question}
            Executed SQL: {sql}
            Data Sample (Top 5 rows): {df.head(5).to_json(orient='records') if not df.empty else 'Empty'}
            
            CRITICAL RULES for Charting:
            1. If the user asks for "products" or "items" in general, group by `product_category_name` instead of `product_id` to make the chart readable.
            2. Avoid using long IDs (like UUIDs or hashes) as the X-axis for charts.

            Does this SQL and data accurately answer the user's question?
            
            NOTE: It is ACCEPTABLE to group by `product_category_name` instead of `product_id` if the user asks for general "products", because product IDs are unreadable hashes.
            
            Return ONLY valid JSON:
            {{"status": "PASS" or "FAIL", "reason": "If FAIL, explain exactly why the SQL is wrong so the generator can fix it."}}
            """
            res2 = json.loads(clean_json(llm.invoke(qa_prompt).content))
            
            if res2['status'] == "PASS":
                return sql, chart_type, df, "PASS"
            else:
                feedback = res2['reason']
                st.warning(f"⚠️ Attempt {attempt+1} failed QA. AI is correcting itself. Reason: {feedback}")
                
        except Exception as e:
            feedback = f"SQL Execution Error: {e}"
            st.warning(f"⚠️ Attempt {attempt+1} failed. Error: {e}")
            time.sleep(1) # Small delay before retry
            
    return None, None, None, "FAIL"

# --- UI ---
st.title("🤖 Olist AI Data Analyst (Self-Correcting)")
tab1, tab2, tab3 = st.tabs(["Ask AI", "Auto-Insights", "Interactive History"])

# TAB 1: ASK AI
with tab1:
    user_question = st.text_input("Ask a specific question:")
    if st.button("Ask AI"):
        if user_question:
            with st.spinner("AI is generating and self-validating SQL..."):
                sql, chart_type, df, status = generate_valid_sql(user_question)
                
                if status == "PASS":
                    st.success("✅ SQL Validated by QA Agent!")
                    st.code(sql, language="sql")
                    render_chart(df, chart_type)
                    
                    # Generate Business Insight
                    with st.spinner("Generating business insight..."):
                        insight_prompt = f"Based on this data sample: {df.head(5).to_json(orient='records')}, provide a 1-sentence business insight for the question: '{user_question}'."
                        insight = llm.invoke(insight_prompt).content
                        st.info(f"💡 **Insight:** {insight}")
                    
                    # Save to Database
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO analytics_marts.ai_query_history (question, sql_query, insight, chart_type) VALUES (:q, :s, :i, :c)"), 
                                     {"q": user_question, "s": sql, "i": insight, "c": chart_type})
                else:
                    st.error("❌ AI failed to generate valid SQL after 3 attempts.")

# TAB 2: AUTO-INSIGHTS
with tab2:
    st.subheader("Let AI find new insights automatically")
    if st.button("Generate Auto-Insights"):
        with st.spinner("AI is exploring your data..."):
            try:
                history_df = pd.read_sql("SELECT title FROM analytics_marts.ai_auto_insights", engine)
                past_titles = "\n".join([f"- {t}" for t in history_df['title'].tolist()]) if not history_df.empty else "None"
                
                # Added PostgreSQL Dialect Instructions
                auto_prompt = f"""
                You are a Senior Data Analyst using PostgreSQL. Schema: {SCHEMA}
                Past generated insights: {past_titles}
                
                Suggest 2 NEW and DIFFERENT business questions and their SQL queries.
                
                CRITICAL RULES:
                1. Use ONLY PostgreSQL syntax. For date math, use CURRENT_DATE - INTERVAL 'X months' (NEVER use DATEADD).
                2. Return ONLY valid JSON array:
                [{{"title": "Question...", "sql": "SELECT ...", "chart_type": "bar|line|area|table"}}]
                If no new insights, return []
                """
                res = json.loads(clean_json(llm.invoke(auto_prompt).content))
                
                if not res:
                    st.warning("No new insights found. All patterns have been analyzed.")
                else:
                    for item in res:
                        st.markdown(f"### 📊 {item['title']}")
                        sql = item['sql']
                        chart_type = item.get('chart_type', 'table')
                        
                        st.code(sql, language="sql")
                        
                        try:
                            df = pd.read_sql(sql, engine)
                            
                            if df.empty:
                                st.warning("⚠️ Data returned is empty.")
                                insight = "Query executed successfully but returned no data (likely due to historical dataset date constraints)."
                            else:
                                render_chart(df, chart_type)
                                
                                # Prohibit weird unicode characters
                                insight_prompt = f"""
                                Based on data: {df.head(5).to_json(orient='records')}, give a 1-sentence business insight for: '{item['title']}'.
                                Use plain standard text (e.g., write 'BRL' or 'R$' normally, do not use weird unicode spaces or characters).
                                """
                                insight = llm.invoke(insight_prompt).content
                                st.info(f"💡 **Insight:** {insight}")
                                
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO analytics_marts.ai_auto_insights (title, sql_query, insight, chart_type) 
                                    VALUES (:t, :s, :i, :c)
                                    ON CONFLICT (title) DO NOTHING
                                """), {"t": item['title'], "s": sql, "i": insight, "c": chart_type})
                                    
                        except Exception as e:
                            st.error(f"SQL Error for '{item['title']}': {e}")
                            
                        st.divider()
            except Exception as e:
                st.error(f"Error generating auto-insights: {e}")

# TAB 3: INTERACTIVE HISTORY
with tab3:
    st.subheader("Re-run Past Queries")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Chat History**")
        try:
            # Fetch all data at once (safer from parameter errors)
            chat_hist = pd.read_sql("SELECT question, sql_query, chart_type FROM analytics_marts.ai_query_history ORDER BY created_at DESC", engine)
            chat_hist = chat_hist.drop_duplicates(subset=['question'])
            
            if not chat_hist.empty:
                selected_chat = st.selectbox("Select a past question:", chat_hist['question'].tolist(), key="chat_select")
                if st.button("Load Chat Result"):
                    # Filter using Pandas, not WHERE in SQL (avoids weird character errors)
                    row = chat_hist[chat_hist['question'] == selected_chat].iloc[0]
                    sql = row['sql_query']
                    c_type = row['chart_type']
                    
                    st.code(sql, language="sql")
                    df = pd.read_sql(sql, engine)
                    render_chart(df, c_type)
            else:
                st.write("No chat history yet.")
        except Exception as e:
            st.error(f"Error loading chat history: {e}")

    with col2:
        st.markdown("**Auto-Insight History**")
        try:
            auto_hist = pd.read_sql("SELECT title, sql_query, chart_type FROM analytics_marts.ai_auto_insights ORDER BY created_at DESC", engine)
            auto_hist = auto_hist.drop_duplicates(subset=['title'])
            
            if not auto_hist.empty:
                selected_auto = st.selectbox("Select an auto-insight:", auto_hist['title'].tolist(), key="auto_select")
                if st.button("Load Auto-Insight Result"):
                    row = auto_hist[auto_hist['title'] == selected_auto].iloc[0]
                    sql = row['sql_query']
                    c_type = row['chart_type']
                    
                    st.code(sql, language="sql")
                    df = pd.read_sql(sql, engine)
                    render_chart(df, c_type)
            else:
                st.write("No auto-insight history yet.")
        except Exception as e:
            st.error(f"Error loading auto-insight history: {e}")