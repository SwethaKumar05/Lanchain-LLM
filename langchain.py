from dotenv import load_dotenv
import os
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

import streamlit as st
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain
from langchain_google_genai import GoogleGenerativeAI

# Page setup
st.set_page_config(page_title="PG University & Legal Guide", layout="centered")
st.title("🎓 Study Abroad Info Assistant")
st.write("Get a comparison of top postgraduate universities and legal guidelines for international students.")

# Input form
with st.form("input_form"):
    country_name = st.text_input("Enter Country Name", placeholder="e.g., Germany")
    field = st.selectbox(
        "Select Field of Study",
        ["Engineering", "Computer Science", "Business", "Medicine", "Data Science", "Law", "Psychology","Artificial Intelligence","Cybersecurity",
         "Environmental Science","Robotics","Biotechnology","Digital Marketing","Finance & Accounting","Architecture & Design","Game Development",
         "International Relations","Public Health","Education Technology","Renewable Energy"]
    )
    submitted = st.form_submit_button("Get Info")

# When form is submitted
if submitted and country_name and field:
    # Initialize LLM
    llm = GoogleGenerativeAI(model="gemini-2.0-flash")

    # First Prompt: University Comparison
    prompt = PromptTemplate(
        input_variables=['Country_name', 'Field'],
        template="""Compare the top postgraduate (master’s) universities in {Country_name} for {Field}. 
Include their location, popular specializations, program duration, and estimated tuition fees for international students in a table format."""
    )
    compare_chain = LLMChain(llm=llm, prompt=prompt, output_key="college_comparison")

    # Second Prompt: Legal & Student Guidelines
    prompt_rules = PromptTemplate(
        input_variables=['Country_name'],
        template="""List some important legal rules and student-related guidelines for students moving to {Country_name} for college. 
Keep it short and categorized under ‘Legal Acts & Rules’ and ‘Student-Specific Advice’. Use bullet points for clarity"""
    )
    rule_chain = LLMChain(llm=llm, prompt=prompt_rules, output_key="legal_guidelines")

    # Sequential Chain
    chain = SequentialChain(
        chains=[compare_chain, rule_chain],
        input_variables=['Country_name', 'Field'],
        output_variables=['college_comparison', 'legal_guidelines']
    )

    # Run chain
    with st.spinner("Generating information..."):
        output = chain({
            'Country_name': country_name,
            'Field': field
        })

    # Display results
    st.subheader("🏫 University Comparison")
    st.markdown(output['college_comparison'])

    st.subheader("📜 Legal & Student Guidelines")
    st.markdown(output['legal_guidelines'])
