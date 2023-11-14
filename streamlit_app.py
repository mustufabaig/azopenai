#Note: The openai-python library support for Azure OpenAI is in preview.
      #Note: This code sample requires OpenAI Python library version 0.28.1 or lower.
import os
import openai
import streamlit as st

openai.api_type = "azure"
openai.api_base = "https://mbaig-openai.openai.azure.com/"
openai.api_version = "2023-07-01-preview"
openai.api_key = st.secrets["OPENAI_API_KEY"]

message_text = [{"role":"system","content":"You are an AI assistant who works for payment processor."}]
question = st.chat_input("How can I help you?")
message_text.append({"role":"user","content":question})

response = openai.ChatCompletion.create(
  engine="mbaig-gpt4",
  messages = message_text,
  temperature=0.7,
  max_tokens=800,
  top_p=0.95,
  frequency_penalty=0,
  presence_penalty=0,
  stop=None
)

st.set_page_config(layout="wide")

st.write(response)
