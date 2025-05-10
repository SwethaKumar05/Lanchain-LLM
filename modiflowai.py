import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
import copy
import plotly.express as px

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# LLM setup
llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GOOGLE_API_KEY)

# Page config
st.set_page_config(page_title="File Modifier with Undo", layout="wide")

# ---------- CUSTOM STYLING ----------
st.markdown("""
    <style>
        body {
            background-color: white !important;
        }
        .custom-header {
            background: linear-gradient(to right, #e3f2fd, #f0f7ff);
            padding: 1.5rem 2rem;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 1.5rem;
            box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.1);
            animation: slideIn 1.2s ease-out;
        }
        @keyframes slideIn {
            0% {
                opacity: 0;
                transform: translateY(-20px);
            }
            100% {
                opacity: 1;
                transform: translateY(0);
            }
        }
    </style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown("""
    <div class="custom-header">
        <h1>📁 ModiFlow AI</h1>
    </div>
""", unsafe_allow_html=True)

# ---------- SIDEBAR NAVIGATION ----------
st.sidebar.title("📂 Navigation")
page = st.sidebar.radio("Go to", ["Main", "Dashboard"])

# ---------- SESSION STATE ----------
if "history" not in st.session_state:
    st.session_state.history = []

if "df" not in st.session_state:
    st.session_state.df = None

if "modified_df" not in st.session_state:
    st.session_state.modified_df = None

if "changes_applied" not in st.session_state:
    st.session_state.changes_applied = False

# ---------- FILE UPLOAD ----------
uploaded_file = st.file_uploader("📁 Upload a file", type=["csv", "xlsx", "xls", "json"])
if uploaded_file and st.session_state.df is None:
    file_type = uploaded_file.name.split(".")[-1].lower()
    try:
        if file_type == "csv":
            df = pd.read_csv(uploaded_file)
        elif file_type in ["xlsx", "xls"]:
            df = pd.read_excel(uploaded_file)
        elif file_type == "json":
            df = pd.read_json(uploaded_file)
        else:
            st.error("Unsupported file type")
            df = None

        if df is not None:
            df.columns = [col.lower() for col in df.columns]
            st.session_state.df = df
            st.session_state.history.append({"action": "Initial upload", "df": copy.deepcopy(df)})

    except Exception as e:
        st.error(f"Error reading file: {e}")

# ---------- UTILITY FUNCTION ----------
def normalize_categorical_values(df):
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].apply(lambda x: str(x).capitalize() if pd.notnull(x) else x)
    return df

# ---------- PATCH FOR SCATTER PLOT ISSUE ----------
@st.cache_data
def safe_numeric(df, col):
    try:
        return pd.to_numeric(df[col], errors='coerce')
    except:
        return df[col]
    
# ---------- MAIN PAGE ----------
if page == "Main":
    if st.session_state.df is not None:
        st.subheader("📌 Current Dataset")
        st.dataframe(st.session_state.df)

        # Action Selector
        action = st.selectbox("👇 Choose a common action (optional)", ["", "Add Row", "Add Column", "Edit Cell", "Delete Row", "Delete Column"])
        instruction = st.text_input("✏️ Enter your instruction to modify the DataFrame")

        # Add Row Logic
        if action == "Add Row":
            st.markdown("👤 Enter values for the new row:")
            new_row = {}
            for col in st.session_state.df.columns:
                new_row[col] = st.text_input(f"{col}:", key=f"add_row_{col}")
            if st.button("➕ Add Row"):
                try:
                    st.session_state.df.loc[len(st.session_state.df)] = new_row
                    st.session_state.history.append({"action": "Add Row", "df": copy.deepcopy(st.session_state.df)})
                    st.success("✅ Row added successfully.")
                except Exception as e:
                    st.error(f"❌ Error adding row: {str(e)}")

        # Handle LLM-based Modification
        elif instruction:
            standardized_instruction = instruction.lower()

            prompt_template = PromptTemplate.from_template(
                """
                You are a Python data assistant. The user has a DataFrame called `df`.

                Given this instruction: "{input}", generate valid Python pandas code to modify the DataFrame.

                ❗ Important rules:
                - Output only valid Python code (no text or explanations).
                - Do NOT include ```python or ``` in your output.
                - No if-conditions or column existence checks.

                Instruction: {input}
                """
            )

            chain = LLMChain(llm=llm, prompt=prompt_template)
            raw_output = chain.run(input=standardized_instruction)
            cleaned_output = "\n".join(
                line for line in raw_output.strip().split("\n") if not line.strip().startswith("```")
            )
            code_lines = cleaned_output.split("\n")


            st.subheader("🤖 Generated Code")
            for line in code_lines:
                st.code(line.strip(), language="python")

            try:
                local_env = {"df": copy.deepcopy(st.session_state.df)}
                for line in code_lines:
                    exec(line.strip(), {}, local_env)
                st.session_state.modified_df = normalize_categorical_values(local_env["df"])
                st.success("✅ Dataset preview updated!")
                st.dataframe(st.session_state.modified_df)
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

        # Apply Changes
        if st.button("✔️ Apply changes to the original dataset") and st.session_state.modified_df is not None:
            st.session_state.df = copy.deepcopy(st.session_state.modified_df)
            st.session_state.history.append({"action": instruction or action, "df": copy.deepcopy(st.session_state.df)})
            st.session_state.changes_applied = True
            st.success("✅ Changes applied to the original dataset.")
            st.dataframe(st.session_state.df)

        # Undo Changes
        if st.session_state.changes_applied:
            if st.button("↩️ UNDO"):
                if len(st.session_state.history) > 1:
                    st.session_state.history.pop()
                    st.session_state.df = copy.deepcopy(st.session_state.history[-1]["df"])
                    st.session_state.changes_applied = False
                    st.success("✅ Reverted to the previous version.")
                    st.dataframe(st.session_state.df)
                else:
                    st.warning("⚠️ No more changes to undo.")

        # Download CSV
        csv = st.session_state.df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv, "modified_data.csv", "text/csv")

        # History Log
        st.subheader("📝 History Log of Changes")
        for i, entry in enumerate(st.session_state.history):
            st.markdown(f"- {i+1}. {entry['action']}")
            

# ---------- DASHBOARD ----------
elif page == "Dashboard" and st.session_state.df is not None:
    st.subheader("📈 Dashboard Overview")

    # Column Overview
    st.markdown("### 🧾 Dataset Columns")
    st.write(list(st.session_state.df.columns))

    # Univariate
    with st.expander("🔍 Univariate Analysis"):
        selected_col = st.selectbox("Select a column for univariate analysis", st.session_state.df.columns)
        df = st.session_state.df

        if pd.api.types.is_numeric_dtype(df[selected_col]):
            plot_type = st.radio("Choose numeric plot", ["Histogram", "Box", "Violin", "Line"])
            
            if plot_type == "Histogram":
                fig = px.histogram(df, x=selected_col, nbins=20, title=f"Histogram of {selected_col}")
            elif plot_type == "Box":
                fig = px.box(df, y=selected_col, title=f"Box Plot of {selected_col}")
            elif plot_type == "Violin":
                fig = px.violin(df, y=selected_col, box=True, title=f"Violin Plot of {selected_col}")
            elif plot_type == "Line":
                fig = px.line(df, y=selected_col, title=f"Line Plot of {selected_col} over Index")
            
            st.plotly_chart(fig)
            st.write("📈 **Summary Statistics:**")
            st.write(df[selected_col].describe())

        else:
            plot_type = st.radio("Choose categorical plot", ["Bar", "Pie", "Line"])
            value_counts = df[selected_col].value_counts().reset_index()
            value_counts.columns = [selected_col, "Count"]

            if plot_type == "Bar":
                fig = px.bar(value_counts, x=selected_col, y="Count", title=f"Bar Chart of {selected_col}")
            elif plot_type == "Pie":
                fig = px.pie(value_counts, names=selected_col, values="Count", title=f"Pie Chart of {selected_col}")
            elif plot_type == "Line":
                fig = px.line(value_counts, x=selected_col, y="Count", title=f"Line Plot of {selected_col}")
            
            st.plotly_chart(fig)



    # Bivariate
    with st.expander("🔍 Bivariate Analysis"):
        col1 = st.selectbox("X-axis column", st.session_state.df.columns, key="bivar1")
        col2 = st.selectbox("Y-axis column", st.session_state.df.columns, key="bivar2")
        df = st.session_state.df

        is_num1 = pd.api.types.is_numeric_dtype(df[col1])
        is_num2 = pd.api.types.is_numeric_dtype(df[col2])

        if is_num1 and is_num2:
            plot_type = st.radio("Choose numeric vs numeric plot", ["Scatter", "Line", "Hexbin", "Density Heatmap"])
            
            if plot_type == "Scatter":
                fig = px.scatter(df, x=col1, y=col2, title=f"Scatter Plot: {col1} vs {col2}")
            elif plot_type == "Line":
                fig = px.line(df, x=col1, y=col2, title=f"Line Plot: {col1} vs {col2}")
            elif plot_type == "Hexbin":
                fig = px.density_heatmap(df, x=col1, y=col2, nbinsx=20, nbinsy=20, title=f"Hexbin Heatmap: {col1} vs {col2}")
            elif plot_type == "Density Heatmap":
                fig = px.density_heatmap(df, x=col1, y=col2, title=f"Density Heatmap: {col1} vs {col2}")
            
            st.plotly_chart(fig)

        elif not is_num1 and not is_num2:
            st.write("Cross-tabulation:")
            st.write(pd.crosstab(df[col1], df[col2]))

            fig = px.bar(pd.crosstab(df[col1], df[col2]), barmode='group', title=f"Grouped Bar Chart: {col1} vs {col2}")
            st.plotly_chart(fig)

        else:
            plot_type = st.radio("Choose category vs numeric plot", ["Box", "Violin", "Strip"])
            
            cat_col = col1 if not is_num1 else col2
            num_col = col2 if not is_num1 else col1

            if plot_type == "Box":
                fig = px.box(df, x=cat_col, y=num_col, title=f"Box Plot: {num_col} by {cat_col}")
            elif plot_type == "Violin":
                fig = px.violin(df, x=cat_col, y=num_col, box=True, title=f"Violin Plot: {num_col} by {cat_col}")
            elif plot_type == "Strip":
                fig = px.strip(df, x=cat_col, y=num_col, title=f"Strip Plot: {num_col} by {cat_col}")

            st.plotly_chart(fig)


    # Multivariate
    with st.expander("🔍 Multivariate Analysis"):
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        
        if len(numeric_cols) >= 2:
            st.markdown("### 📊 Correlation Heatmap")
            corr = df[numeric_cols].corr()
            st.dataframe(corr.style.background_gradient(cmap="coolwarm"))
            fig = px.imshow(corr, text_auto=True, title="Correlation Matrix")
            st.plotly_chart(fig)

            st.markdown("### 🟡 Pair Plot (Scatter Matrix)")
            fig = px.scatter_matrix(df, dimensions=numeric_cols[:5], title="Scatter Matrix (Top 5 numeric columns)")
            st.plotly_chart(fig)

            st.markdown("### 🎨 Parallel Coordinates Plot")
            fig = px.parallel_coordinates(df[numeric_cols], color=numeric_cols[0], title="Parallel Coordinates Plot")
            st.plotly_chart(fig)
        else:
            st.warning("⚠️ Not enough numeric columns for multivariate visualizations.")

