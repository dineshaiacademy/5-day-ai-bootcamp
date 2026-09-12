import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.title("Streamlit + LLM Starter")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.warning("OPENAI_API_KEY not set. Copy .env.example to .env and fill in your key.")

prompt = st.text_input("Enter a prompt")
if prompt:
    # TODO: replace with a real LLM call, e.g.:
    # from openai import OpenAI
    # client = OpenAI(api_key=api_key)
    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[{"role": "user", "content": prompt}],
    # )
    # st.write(response.choices[0].message.content)
    st.write(f"Echo: {prompt}")
