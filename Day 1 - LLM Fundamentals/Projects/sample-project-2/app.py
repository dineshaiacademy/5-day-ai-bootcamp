import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.title("Sample Project 2")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.warning("OPENAI_API_KEY not set. Copy .env.example to .env and fill in your key.")

st.write("This shows a second, independent project living under the same day.")
