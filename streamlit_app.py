#Note: The openai-python library support for Azure OpenAI is in preview.
      #Note: This code sample requires OpenAI Python library version 0.28.1 or lower.
import os
import openai
import streamlit as st
import json
import db as dbconn
import pandas as pd

from pandasai import PandasAI
from pandasai.llm.openai import OpenAI
from pandasai.llm import AzureOpenAI
from pandasai import SmartDataframe
from pandasai.responses.streamlit_response import StreamlitResponse

openai.api_type = "azure"
openai.api_base = "https://mbaig-openai.openai.azure.com/"
openai.api_version = "2023-07-01-preview"
openai.api_key = st.secrets["OPENAI_API_KEY"]

message_text = [{"role":"system","content":"You are an AI assistant who works for payment processor. You will be helping merchants with their queries regarding fraud, chargeback and decline transactions. answer the question based on the context below. If the question cannot be answered using the information provided answer with \"I don't know\". \nContext: Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer to the input question. \nUnless the user specifies in the question a specific number of examples to obtain, query for at most 5 results using the LIMIT clause as per {dialect}. \nWhenever user ask to calculate ratio then make sure to use DIV0 snowflake function. \nYou can order the results to return the most informative data in the database.\nNever query for all columns from a table. You must query only the columns that are needed to answer the question. \nPay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.\nPay attention to use sysdate() function to get the current date, if the question involves \"today\".\nAlways use parent_aggregate_merchant_id=10000111, \nIf Industry is not mentioned then use \"Wholesale Clubs\". \n\nYou must always output your answer in JSON format with the following key-value pairs:\n- \"input\": input question\n- \"query\": the SQL query that you generated\n- \"error\": an error message if the query is invalid, or null if the query is valid\n- \"data-result\" : output SQL query results as pandas dataframe with column names in capitals\n- \"plot-results\" : plot SQL results using matlibplot python package\n- \"text-result\" : SQL query results in natural language\n\nOnly use the following tables:\ncreate table llmsqlchain.merchant (\n    PARENT_AGGREGATE_MERCHANT_ID number comment 'PARENT_AGGREGATE_MERCHANT_ID uniquely identifies merchant across fraud insights product. This can also be known as \"merchant_id\"',\n    PARENT_AGGREGATE_MERCHANT_NAME varchar comment 'PARENT_AGGREGATE_MERCHANT_NAME is the name of the merchant who is using fraud insights product.',\n    PRIMARY KEY (\"PARENT_AGGREGATE_MERCHANT_ID\")\n);\n\ncreate table llmsqlchain.my_me_benchmark (\n        PARENT_AGGREGATE_MERCHANT_ID number comment 'PARENT_AGGREGATE_MERCHANT_ID uniquely identifies merchant across fraud insights product. This can also be known as \"merchant_id\"',\n        PERIOD_DATE date comment 'time period of the aggregates',\n        PERIOD_QUARTER varchar comment 'quarter of the year for the aggregates',\n        REGION_DESCRIPTION varchar comment 'region of the merchant',\n        COUNTRY_DESCRIPTION varchar comment 'country of the merchant',\n        INDUSTRY_DESCRIPTION varchar comment 'industry or sector in which merchant is operating in',\n        FRAUD_AMOUNT_USD float comment 'total volume or amount of transactions which were identified as fraudulant in USD currency',\n        CLEARED_USD float comment 'total volume or amount of transactions which were successfully cleared or went through in USD currency',\n        FIRST_CHARGEBACK_AMOUNT_USD float comment 'total volume of transactions which were disputed and went through first chargeback process in USD currency',\n        APPROVAL_RATE number(30, 6) comment 'rate of approved transaction',\n        DECLINED_AUTHORIZATION_COUNT number comment 'total number or count of transactions which were declined',\n        AUTHORIZED_COUNT number comment 'total number or count of transactions which were authorized',\n        DECLINE_RATE number(30, 6) comment 'rate of declined transactions',\n        CROSS_BORDER_FRAUD_AMOUNT_USD float comment 'total volume or amount of transactions which were identified as fraud and they were done in region different than merchants region',\n        FOREIGN KEY (\"PARENT_AGGREGATE_MERCHANT_ID\") REFERENCES \"MERCHANT\" (\"PARENT_AGGREGATE_MERCHANT_ID\")\n    );\n\ncreate table llmsqlchain.my_peer_benchmark (\n        PARENT_AGGREGATE_MERCHANT_ID number comment 'PARENT_AGGREGATE_MERCHANT_ID uniquely identifies merchant across fraud insights product. This can also be known as \"merchant_id\"',\n        PERIOD_DATE date comment 'time period of the aggregates',\n        PERIOD_QUARTER varchar comment 'quarter of the year for the aggregates',\n        REGION_DESCRIPTION varchar comment 'region of the peer or competitor',\n        COUNTRY_DESCRIPTION varchar comment 'country of the peer or competitor',\n        INDUSTRY_DESCRIPTION varchar comment 'industry or sector in which peer or competitor is operating in',\n        FRAUD_AMOUNT_USD float comment 'total volume or amount of transactions which were identified as fraudulant in USD currency',\n        CLEARED_USD float comment 'total volume or amount of transactions which were successfully cleared or went through in USD currency',\n        FIRST_CHARGEBACK_AMOUNT_USD float comment 'total volume of transactions which were disputed and went through first chargeback process in USD currency',\n        APPROVAL_RATE number(30, 6) comment 'rate of approved transaction',\n        DECLINED_AUTHORIZATION_COUNT number comment 'total number or count of transactions which were declined',\n        AUTHORIZED_COUNT number comment 'total number or count of transactions which were authorized',\n        DECLINE_RATE number(30, 6) comment 'rate of declined transactions',\n        CROSS_BORDER_FRAUD_AMOUNT_USD float comment 'total volume or amount of transactions which were identified as fraud and they were done in region different than peer or competitor region',\n        FOREIGN KEY (\"PARENT_AGGREGATE_MERCHANT_ID\") REFERENCES \"MERCHANT\" (\"PARENT_AGGREGATE_MERCHANT_ID\")\n    );\n\nIf someone asks to compare data with peers then join my_me_benchmark table with my_peer_benchmark table and then compare the measures from both tables.\nIf someone mentions \"performance\" then they really mean \"volume\".\nIf someone ask for \"my chargeback\" or \"my Fraud\" or \"my declined\" then use table my_me_benchmark."}]

st.set_page_config(layout="wide")
question = st.chat_input("How can I help you?")
if question:
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
      raw_response = response;
      result_string = raw_response.choices[0].message.content
      result_json = json.loads(result_string)
      st.write(raw_response)
      st.write(result_json)
      df = dbconn.query_db(result_json["query"])
      st.code(df.to_json(orient='records'))
      st.dataframe(df)
      #pandaai
      llm = AzureOpenAI(api_token=st.secrets["OPENAI_API_KEY"], api_base="https://mbaig-openai.openai.azure.com/", api_version="2023-07-01-preview", deployment_name="mbaig-gpt4")
      #pandas_ai = PandasAI(llm)
      sdf = SmartDataframe(df, config={"llm" : llm})
      question = result_json["input"]
      st.write(question)
      #st.write(pandas_ai.run(df, prompt=question))
      st.write(sdf.chat(question))
      print(sdf.chat(question + ". Plot the histogram of regions using different colors."))
