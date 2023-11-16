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

message_text = [{"role":"system","content":"You are an AI assistant who works for payment processor. You will be helping merchants with their queries regarding fraud, chargeback and decline transactions. answer the question based on the context below. If the question cannot be answered using the information provided answer with \"I don't know\". \nContext: Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer to the input question. \nUnless the user specifies in the question a specific number of examples to obtain, query for at most 5 results using the LIMIT clause as per {dialect}. \nWhenever user ask to calculate ratio then make sure to use DIV0 snowflake function. \nYou can order the results to return the most informative data in the database.\nNever query for all columns from a table. You must query only the columns that are needed to answer the question. \nPay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.\nAlways use parent_aggregate_merchant_id=10000111, \n\nOnly use \"merchant_performance\" table with the following schema:\ncreate or replace table merchant_performance (\n    PARENT_AGGREGATE_MERCHANT_ID number comment 'PARENT_AGGREGATE_MERCHANT_ID uniquely identifies merchant across fraud insights product. This can also be known as \"merchant_id\"',\n    PARENT_AGGREGATE_MERCHANT_NAME varchar comment 'PARENT_AGGREGATE_MERCHANT_NAME is the name of the merchant who is using fraud insights product.',\n    PERIOD_DATE date comment 'time period of the aggregates',\n    PERIOD_QUARTER varchar comment 'quarter of the year for the aggregates',\n    REGION_DESCRIPTION varchar comment 'region of the merchant',\n    COUNTRY_DESCRIPTION varchar comment 'country of the merchant',\n    INDUSTRY_DESCRIPTION varchar comment 'industry or sector in which merchant is operating in',\n    FRAUD_AMOUNT_USD float comment 'total volume or amount of transactions which were identified as fraudulant in USD currency',\n    CLEARED_USD float comment 'total volume or amount of transactions which were successfully cleared or went through in USD currency',\n    FIRST_CHARGEBACK_AMOUNT_USD float comment 'total volume of transactions which were disputed and went through first chargeback process in USD currency',\n    APPROVAL_RATE number(30, 6) comment 'rate of approved transaction',\n    DECLINED_AUTHORIZATION_COUNT number comment 'total number or count of transactions which were declined',\n    AUTHORIZED_COUNT number comment 'total number or count of transactions which were authorized',\n    DECLINE_RATE number(30, 6) comment 'rate of declined transactions',\n    CROSS_BORDER_FRAUD_AMOUNT_USD float comment 'total volume or amount of transactions which were identified as fraud and they were done in region different than merchants region',\n    PEER_FRAUD_AMOUNT_USD float comment 'this column contains merchants peer data. total volume or amount of transactions which were identified as fraudulant in USD currency',\n    PEER_CLEARED_USD float comment 'this column contains merchants peer data. total volume or amount of transactions which were successfully cleared or went through in USD currency',\n    PEER_FIRST_CHARGEBACK_AMOUNT_USD float comment 'this column contains merchants peer data. total volume of transactions which were disputed and went through first chargeback process in USD currency',\n    PEER_APPROVAL_RATE number(30, 6) comment 'this column contains merchants peer data. rate of approved transaction',\n    PEER_DECLINED_AUTHORIZATION_COUNT number comment 'this column contains merchants peer data. total number or count of transactions which were declined',\n    PEER_AUTHORIZED_COUNT number comment 'this column contains merchants peer data. total number or count of transactions which were authorized',\n    PEER_DECLINE_RATE number(30, 6) comment 'this column contains merchants peer data. rate of declined transactions',\n    PEER_CROSS_BORDER_FRAUD_AMOUNT_USD float comment 'this column contains merchants peer data. total volume or amount of transactions which were identified as fraud and they were done in region different than peer or competitor region',\n    ALERTS_REPORTED_FRAUD_COUNT INT comment 'total number of fraudulant transactions reported by credit card issuers and sent to the merchant by ethoca \"alerts\" product',\n    ALERTS_REPORTED_DISPUTE_COUNT INT comment 'total number of transactions disputed by card holders and reported by issuers and sent to the merchant by ethoca \"alerts\" product',\n    CLARITY_LOOKUPS_COUNT INT comment 'total number of transactions which were looked up by credit card holder',\n    CLARITY_NEGATING_EVENTS_COUNT INT comment 'total number of transactions which ended up in chargebacks even though they were looked up by credit card holder using ethoca \"clarity\" product',\n    CLARITY_DEFLECTION_COUNT INT comment 'total number of transactions which which were looked up by ethoca clarity product and got deflected a chargeback'\n    )\nCOMMENT='\"merchant_performance\" table has merchants monthly aggregates and KPIs regarding credit card transactions. columns prefixed with \"PEER_\" contains merchant peer KPIs. Columns prefixed with \"ALERTS\" contains \"ethoca alerts\" product KPIs. Columns prefixed with \"CLARITY\" contains \"ethoca clarity\" product KPIs'\n;\n\nif someone asks \"my name\" then refer to PARENT_AGGREGATE_MERCHANT_NAME column\nIf someone asks to compare data with peers then compare respective column with the column prefixed with \"PEER_\".\nIf someone mentions \"performance\" then they really mean \"volume\".\nIf someone ask for \"my chargeback\" or \"my Fraud\" or \"my declined\" then use columns are not prefixed with \"ALERTS_\" or \"CLARITY_\" or \"PEER_\".\ndo not use alias for 'PERIOD_DATE' column\nif group by 'PERIOD_DATE' column then include 'PERIOD_DATE' in the select list\nfor \"fraud volume\" use column alias 'FRAUD_VOLUME'\nfor \"chartback volume\" use column alias 'CB_VOLUME'\nfor \"number of fraudulant transaction\" or \"fraud count\" use column alias 'FRAUD_COUNT'\nfor \"number of chargebacks\" or \"chargeback count\" use column alias 'CB_COUNT'\nprefix the alias with \"PEER_\" for columns prefixed \"PEER_\"\n\nsome examples below\nuser: what is my name?\nSQL query: select distinct parent_aggregate_merchant_name as merchant_name from FROM merchant_performance WHERE PARENT_AGGREGATE_MERCHANT_ID=10000111\n\nuser: what is my name?\nSQL query: select distinct parent_aggregate_merchant_name as merchant_name from FROM merchant_performance WHERE PARENT_AGGREGATE_MERCHANT_ID=10000111\n\nuser: show me ethoca insights for the month of march and april 2023\nSQL query: SELECT PERIOD_DATE, SUM(clarity_lookups_count) AS receipts_lookups,SUM(alerts_reported_fraud_count) AS reported_fraud, SUM(alerts_reported_dispute_count) AS reported_disputes, SUM(clarity_negating_events_count) AS fraud_dispute_not_deflected, SUM(clarity_deflection_count) AS fraud_dispute_deflected FROM merchant_performance WHERE PARENT_AGGREGATE_MERCHANT_ID = 10000111 AND PERIOD_DATE in ('2023-03-31','2023-04-30') GROUP BY PERIOD_DATE ORDER BY PERIOD_DATE DESC\n\nYou must always output your answer in JSON format with the following key-value pairs:\n- \"input\": input question\n- \"query\": the SQL query that you generated\n- \"error\": an error message if the query is invalid, or null if the query is valid\n- \"text-result\" : SQL query results in natural language\n- \"should-plot\" : \"true\" if input contains the word \"plot\"\n- \"fraudvol_asked\" : \"true\" if input contains \"fraud volume\" else \"false\"\n- \"cbvol_asked\" : \"true\" if input contains \"cb volume\" or \"chargeback volume\" else \"false\"\n- \"fraudcnt_asked\" : \"true\" if input contains \"fraud count\" or \"number of fraudulant transactions\" else \"false\"\n- \"cbvolcnt_asked\" : \"true\" if input contains \"cb count\" or \"number of chargebacks\" else \"false\"\n- \"peerinfo_asked\" : \"true\" if input contains \"peer\" or \"my peer\" else \"false\"\n- \"date_exist\" : \"true\" if SQL query contains \"PERIOD_DATE\" column else \"false\"\n- \"is_summary\" : \"true\" if input contains \"ethoca insights\" or \"insights\" else \"false\"\n\nin what region do i do business in?\nwhich region has the highest fraud volume? and what is that volume?\nshow me my fraud to chargeback ratio? and round it up to 2 decimal places\ncompare my fraud to chargeback ratio in united states vs europe region\nhow do i compare against my peers in total cross border fraud performance?\nhow do i compare against my peers in fraud performance within united states?\nwhich month has the highest declines recorded? in asia pacific"}]

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

      row_count = len(df)
      if result_json["is_summary"] == "true":
            #st.bar_chart(df, x = "PERIOD_DATE", y = ["RECEIPTS_LOOKUPS","REPORTED_FRAUD","REPORTED_DISPUTES","FRAUD_DISPUTE_NOT_DEFLECTED","FRAUD_DISPUTE_DEFLECTED"])
            col1, col2, col3, col4, col5 = st.columns(5)
            if row_count == 1:
                  col1.metric("RECEIPT LOOKUPS", df["RECEIPTS_LOOKUPS"].iloc[0])
                  col2.metric("REPORTED FRAUD", df["REPORTED_FRAUD"].iloc[0])
                  col3.metric("REPORTED DISPUTES", df["REPORTED_DISPUTES"].iloc[0])
                  col4.metric("FRAUD/DISPUTE NOT DEFLECTED", df["FRAUD_DISPUTE_NOT_DEFLECTED"].iloc[0])
                  col5.metric("FRAUD/DISPUTE DEFLECTED", df["FRAUD_DISPUTE_DEFLECTED"].iloc[0])
            if row_count == 2:
                  col1.metric("RECEIPT LOOKUPS", df["RECEIPTS_LOOKUPS"].iloc[0], str(df["RECEIPTS_LOOKUPS"].iloc[1]))
                  col2.metric("REPORTED FRAUD", df["REPORTED_FRAUD"].iloc[0], str(df["REPORTED_FRAUD"].iloc[1]))
                  col3.metric("REPORTED DISPUTES", df["REPORTED_DISPUTES"].iloc[0], str(df["REPORTED_DISPUTES"].iloc[1]))
                  col4.metric("FRAUD/DISPUTE NOT DEFLECTED", df["FRAUD_DISPUTE_NOT_DEFLECTED"].iloc[0], str(df["FRAUD_DISPUTE_NOT_DEFLECTED"].iloc[1]))
                  col5.metric("FRAUD/DISPUTE DEFLECTED", df["FRAUD_DISPUTE_DEFLECTED"].iloc[0], str(df["FRAUD_DISPUTE_DEFLECTED"].iloc[1]))
      else:
            st.dataframe(df, hide_index=True)


                  
