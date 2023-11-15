#Note: The openai-python library support for Azure OpenAI is in preview.
      #Note: This code sample requires OpenAI Python library version 0.28.1 or lower.
import os
import openai
import streamlit as st
import json
import db as dbconn
import pandas as pd
import numpy as np

from pandasai import PandasAI
from pandasai.llm.openai import OpenAI
from pandasai.llm import AzureOpenAI
from pandasai import SmartDataframe
from pandasai.responses.streamlit_response import StreamlitResponse

openai.api_type = "azure"
openai.api_base = "https://mbaig-openai.openai.azure.com/"
openai.api_version = "2023-07-01-preview"
openai.api_key = st.secrets["OPENAI_API_KEY"]

message_text = [{"role":"system","content":"You are an AI assistant who works for payment processor. You will be helping merchants with their queries regarding fraud, chargeback and decline transactions. answer the question based on the context below. If the question cannot be answered using the information provided answer with \"I don't know\". \nContext: Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer to the input question. \nUnless the user specifies in the question a specific number of examples to obtain, query for at most 5 results using the LIMIT clause as per {dialect}. \nWhenever user ask to calculate ratio then make sure to use DIV0 snowflake function. \nYou can order the results to return the most informative data in the database.\nNever query for all columns from a table. You must query only the columns that are needed to answer the question. \nPay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.\nAlways use parent_aggregate_merchant_id=10000111, \n\nOnly use \"merchant_performance\" table with the following schema:\ncreate or replace table merchant_performance (\n    PARENT_AGGREGATE_MERCHANT_ID number comment 'PARENT_AGGREGATE_MERCHANT_ID uniquely identifies merchant across fraud insights product. This can also be known as \"merchant_id\"',\n    PARENT_AGGREGATE_MERCHANT_NAME varchar comment 'PARENT_AGGREGATE_MERCHANT_NAME is the name of the merchant who is using fraud insights product.',\n    PERIOD_DATE date comment 'time period of the aggregates',\n    PERIOD_QUARTER varchar comment 'quarter of the year for the aggregates',\n    REGION_DESCRIPTION varchar comment 'region of the merchant',\n    COUNTRY_DESCRIPTION varchar comment 'country of the merchant',\n    INDUSTRY_DESCRIPTION varchar comment 'industry or sector in which merchant is operating in',\n    FRAUD_AMOUNT_USD float comment 'total volume or amount of transactions which were identified as fraudulant in USD currency',\n    CLEARED_USD float comment 'total volume or amount of transactions which were successfully cleared or went through in USD currency',\n    FIRST_CHARGEBACK_AMOUNT_USD float comment 'total volume of transactions which were disputed and went through first chargeback process in USD currency',\n    APPROVAL_RATE number(30, 6) comment 'rate of approved transaction',\n    DECLINED_AUTHORIZATION_COUNT number comment 'total number or count of transactions which were declined',\n    AUTHORIZED_COUNT number comment 'total number or count of transactions which were authorized',\n    DECLINE_RATE number(30, 6) comment 'rate of declined transactions',\n    CROSS_BORDER_FRAUD_AMOUNT_USD float comment 'total volume or amount of transactions which were identified as fraud and they were done in region different than merchants region',\n    PEER_FRAUD_AMOUNT_USD float comment 'this column contains merchants peer data. total volume or amount of transactions which were identified as fraudulant in USD currency',\n    PEER_CLEARED_USD float comment 'this column contains merchants peer data. total volume or amount of transactions which were successfully cleared or went through in USD currency',\n    PEER_FIRST_CHARGEBACK_AMOUNT_USD float comment 'this column contains merchants peer data. total volume of transactions which were disputed and went through first chargeback process in USD currency',\n    PEER_APPROVAL_RATE number(30, 6) comment 'this column contains merchants peer data. rate of approved transaction',\n    PEER_DECLINED_AUTHORIZATION_COUNT number comment 'this column contains merchants peer data. total number or count of transactions which were declined',\n    PEER_AUTHORIZED_COUNT number comment 'this column contains merchants peer data. total number or count of transactions which were authorized',\n    PEER_DECLINE_RATE number(30, 6) comment 'this column contains merchants peer data. rate of declined transactions',\n    PEER_CROSS_BORDER_FRAUD_AMOUNT_USD float comment 'this column contains merchants peer data. total volume or amount of transactions which were identified as fraud and they were done in region different than peer or competitor region',\n    ALERTS_REPORTED_FRAUD_COUNT INT comment 'total number of fraudulant transactions reported by credit card issuers and sent to the merchant by ethoca \"alerts\" product',\n    ALERTS_REPORTED_DISPUTE_COUNT INT comment 'total number of transactions disputed by card holders and reported by issuers and sent to the merchant by ethoca \"alerts\" product',\n    CLARITY_LOOKUPS_COUNT INT comment 'total number of transactions which were looked up by credit card holder',\n    CLARITY_NEGATING_EVENTS_COUNT INT comment 'total number of transactions which ended up in chargebacks even though they were looked up by credit card holder using ethoca \"clarity\" product',\n    CLARITY_DEFLECTION_COUNT INT comment 'total number of transactions which which were looked up by ethoca clarity product and got deflected a chargeback'\n    )\nCOMMENT='\"merchant_performance\" table has merchants monthly aggregates and KPIs regarding credit card transactions. columns prefixed with \"PEER_\" contains merchant peer KPIs. Columns prefixed with \"ALERTS\" contains \"ethoca alerts\" product KPIs. Columns prefixed with \"CLARITY\" contains \"ethoca clarity\" product KPIs'\n;\n\nif someone asks \"my name\" then refer to PARENT_AGGREGATE_MERCHANT_NAME column\nIf someone asks to compare data with peers then compare respective column with the column prefixed with \"PEER_\".\nIf someone mentions \"performance\" then they really mean \"volume\".\nIf someone ask for \"my chargeback\" or \"my Fraud\" or \"my declined\" then use columns are not prefixed with \"ALERTS_\" or \"CLARITY_\" or \"PEER_\".\ndo not use alias for 'PERIOD_DATE' column\nif group by 'PERIOD_DATE' column then include 'PERIOD_DATE' in the select list\nfor \"fraud volume\" use column alias 'FRAUD_VOLUME'\nfor \"chartback volume\" use column alias 'CB_VOLUME'\nfor \"number of fraudulant transaction\" or \"fraud count\" use column alias 'FRAUD_COUNT'\nfor \"number of chargebacks\" or \"chargeback count\" use column alias 'CB_COUNT'\nprefix the alias with \"PEER_\" for columns prefixed \"PEER_\"\n\nsome examples below\nquestion: what is my name?\nquery: select distinct parent_aggregate_merchant_name as merchant_name from FROM merchant_performance WHERE PARENT_AGGREGATE_MERCHANT_ID=10000111\n\nquestion: what is my name?\nquery: select distinct parent_aggregate_merchant_name as merchant_name from FROM merchant_performance WHERE PARENT_AGGREGATE_MERCHANT_ID=10000111\n\nquestion: show me summary of ethoca performance?\nquery: select top 1 period_date, receipts_lookups, receipts_lookups - (lead(receipts_lookups) over (order by period_date desc)) as receipts_lookups_delta, reported_fraud - (lead(reported_fraud) over (order by period_date desc)) as reported_fraud_delta, reported_disputes - (lead(reported_disputes) over (order by period_date desc)) as reported_disputes_delta, fraud_dispute_not_deflected -(lead(fraud_dispute_not_deflected) over (order by period_date desc)) as fraud_dispute_not_deflected_delta, fraud_dispute_deflected - (lead(fraud_dispute_deflected) over (order by period_date desc)) as fraud_dispute_deflected_delta from ( SELECT PERIOD_DATE, sum(clarity_lookups_count) receipts_lookups,sum(alerts_reported_fraud_count) reported_fraud, sum(alerts_reported_dispute_count) reported_disputes, sum(clarity_negating_events_count) fraud_dispute_not_deflected, sum(clarity_deflection_count) fraud_dispute_deflected FROM merchant_performance WHERE PARENT_AGGREGATE_MERCHANT_ID = 10000111 AND PERIOD_DATE in ('2023-03-31','2023-04-30') GROUP BY PERIOD_DATE ORDER BY PERIOD_DATE DESC);\n\nYou must always output your answer in JSON format with the following key-value pairs:\n- \"input\": input question\n- \"query\": the SQL query that you generated\n- \"error\": an error message if the query is invalid, or null if the query is valid\n- \"text-result\" : SQL query results in natural language\n- \"should-plot\" : \"true\" if input contains the word \"plot\"\n- \"fraudvol_asked\" : \"true\" if input contains \"fraud volume\" else \"false\"\n- \"cbvol_asked\" : \"true\" if input contains \"cb volume\" or \"chargeback volume\" else \"false\"\n- \"fraudcnt_asked\" : \"true\" if input contains \"fraud count\" or \"number of fraudulant transactions\" else \"false\"\n- \"cbvolcnt_asked\" : \"true\" if input contains \"cb count\" or \"number of chargebacks\" else \"false\"\n- \"peerinfo_asked\" : \"true\" if input contains \"peer\" or \"my peer\" else \"false\"\n- \"date_exist\" : \"true\" if SQL query contains \"PERIOD_DATE\" column else \"false\"\n- \"is_summary\" : \"true\" if input contains \"summary\" else \"false\"\n"}]

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
      st.write(raw_response)

      result_string = raw_response.choices[0].message.content
      result_json = json.loads(result_string)
      question = result_json["input"]
      
      st.write(question)
      st.write(result_json)
      
      df = dbconn.query_db(result_json["query"])
      
      st.code(df.columns.values.tolist())

      st.code(df.to_json())
      #st.code(df.to_json(orient='records'))
      #st.code(df.to_json(orient='split'))
      #st.code(df.to_json(orient='index'))
      #st.code(df.to_json(orient='columns'))
      #st.code(df.to_json(orient='values'))

      st.dataframe(df, hide_index=True)
      #st.line_chart(df, x = "PERIOD_DATE", y = ["FRAUD_VOLUME"])
      #st.bar_chart(df, x = "PERIOD_DATE", y = ["FRAUD_VOLUME"])

      if result_json["is_summary"] == "true":
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("RECEIPT LOOKUPS", df["RECEIPTS_LOOKUPS"].iloc[0], df["RECEIPTS_LOOKUPS_DELTA"].iloc[0].astype(np.int32))
            col2.metric("REPORTED FRAUD", df["REPORTED_FRAUD"].iloc[0], df["REPORTED_FRAUD_DELTA"].iloc[0].astype(np.int32))
            col3.metric("REPORTED DISPUTES", df["REPORTED_DISPUTES"].iloc[0], df["REPORTED_DISPUTES_DELTA"].iloc[0].astype(np.int32))
            col4.metric("FRAUD/DISPUTE NOT DEFLECTED", df["FRAUD_DISPUTE_NOT_DEFLECTED"].iloc[0], df["FRAUD_DISPUTE_NOT_DEFLECTED_DELTA"].iloc[0].astype(np.int32))
            col5.metric("FRAUD/DISPUTE DEFLECTED", df["FRAUD_DISPUTE_DEFLECTED"].iloc[0], df["FRAUD_DISPUTE_DEFLECTED_DELTA"].iloc[0].astype(np.int32))

      #pandaai
      #st.write('pandasai')
      #llm = AzureOpenAI(api_token=st.secrets["OPENAI_API_KEY"], api_base="https://mbaig-openai.openai.azure.com/", api_version="2023-07-01-preview", deployment_name="mbaig-gpt4")
      #pandas_ai = PandasAI(llm)
      #st.write(pandas_ai.run(df, prompt=question))

      #sdf = SmartDataframe(df, config={"llm" : llm})
      #st.write(sdf.chat(question))
      #sdf.plot_histogram(column="FRAUD_VOLUME")
