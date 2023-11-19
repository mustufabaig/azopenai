#Note: The openai-python library support for Azure OpenAI is in preview.
      #Note: This code sample requires OpenAI Python library version 0.28.1 or lower.
import os
import openai
import streamlit as st
import json
import db as dbconn
import pandas as pd
import numpy as np
import time

from st_pages import Page, show_pages, add_page_title 
from pandasai import PandasAI
from pandasai.llm.openai import OpenAI
from pandasai.llm import AzureOpenAI
from pandasai import SmartDataframe
from pandasai.responses.streamlit_response import StreamlitResponse


st.set_page_config(layout="wide", page_title="Home")
show_pages([ Page("streamlit_app.py", "Merchant"), Page("pages/about.py", "About", in_section=False)])
st.title('Fraud Insights - Merchant')

openai.api_type = "azure"
openai.api_base = "https://mbaig-openai.openai.azure.com/"
openai.api_version = "2023-07-01-preview"
openai.api_key = st.secrets["OPENAI_API_KEY"]

message_text = [{"role":"system","content":"You are an AI assistant who works for payment processor. You will help answer questions from merchants regarding fraud, chargeback and decline transactions. If the question cannot be answered using the information provided answer with \"I don't know\". \nContext: Given an input question, create a snowflake query based on the following table schema and sample data provided below.\n\ncreate or replace table merchant_performance (\n    PARENT_AGGREGATE_MERCHANT_ID number comment 'PARENT_AGGREGATE_MERCHANT_ID uniquely identifies merchant across fraud insights product. This can also be known as \"merchant_id\"',\n    PARENT_AGGREGATE_MERCHANT_NAME varchar comment 'PARENT_AGGREGATE_MERCHANT_NAME is the name of the merchant who is using fraud insights product.',\n    PERIOD_DATE date comment 'time period of the aggregates',\n    PERIOD_QUARTER varchar comment 'quarter of the year for the aggregates',\n    REGION_DESCRIPTION varchar comment 'region of the merchant',\n    COUNTRY_DESCRIPTION varchar comment 'country of the merchant',\n    INDUSTRY_DESCRIPTION varchar comment 'industry or sector in which merchant is operating in',\n    FRAUD_AMOUNT_USD float comment 'total volume or amount of transactions which were identified as fraudulant in USD currency',\n    CLEARED_USD float comment 'total volume or amount of transactions which were successfully cleared or went through in USD currency',\n    FIRST_CHARGEBACK_AMOUNT_USD float comment 'total volume of transactions which were disputed and went through first chargeback process in USD currency',\n    APPROVAL_RATE number(30, 6) comment 'rate of approved transaction',\n    DECLINED_AUTHORIZATION_COUNT number comment 'total number or count of transactions which were declined',\n    AUTHORIZED_COUNT number comment 'total number or count of transactions which were authorized',\n    DECLINE_RATE number(30, 6) comment 'rate of declined transactions',\n    CROSS_BORDER_FRAUD_AMOUNT_USD float comment 'total volume or amount of transactions which were identified as fraud and they were done in region different than merchants region',\n    PEER_FRAUD_AMOUNT_USD float comment 'this column contains merchants peer data. total volume or amount of transactions which were identified as fraudulant in USD currency',\n    PEER_CLEARED_USD float comment 'this column contains merchants peer data. total volume or amount of transactions which were successfully cleared or went through in USD currency',\n    PEER_FIRST_CHARGEBACK_AMOUNT_USD float comment 'this column contains merchants peer data. total volume of transactions which were disputed and went through first chargeback process in USD currency',\n    PEER_APPROVAL_RATE number(30, 6) comment 'this column contains merchants peer data. rate of approved transaction',\n    PEER_DECLINED_AUTHORIZATION_COUNT number comment 'this column contains merchants peer data. total number or count of transactions which were declined',\n    PEER_AUTHORIZED_COUNT number comment 'this column contains merchants peer data. total number or count of transactions which were authorized',\n    PEER_DECLINE_RATE number(30, 6) comment 'this column contains merchants peer data. rate of declined transactions',\n    PEER_CROSS_BORDER_FRAUD_AMOUNT_USD float comment 'this column contains merchants peer data. total volume or amount of transactions which were identified as fraud and they were done in region different than peer or competitor region',\n    ALERTS_REPORTED_FRAUD_COUNT INT comment 'total number of fraudulant transactions reported by credit card issuers and sent to the merchant by ethoca \"alerts\" product',\n    ALERTS_REPORTED_DISPUTE_COUNT INT comment 'total number of transactions disputed by card holders and reported by issuers and sent to the merchant by ethoca \"alerts\" product',\n    CLARITY_LOOKUPS_COUNT INT comment 'total number of transactions which were looked up by credit card holder',\n    CLARITY_NEGATING_EVENTS_COUNT INT comment 'total number of transactions which ended up in chargebacks even though they were looked up by credit card holder using ethoca \"clarity\" product',\n    CLARITY_DEFLECTION_COUNT INT comment 'total number of transactions which which were looked up by ethoca clarity product and got deflected a chargeback'\n    )\nCOMMENT='\"merchant_performance\" table has merchants monthly aggregates and KPIs regarding credit card transactions. columns prefixed with \"PEER_\" contains merchant peer KPIs. Columns prefixed with \"ALERTS\" contains \"ethoca alerts\" product KPIs. Columns prefixed with \"CLARITY\" contains \"ethoca clarity\" product KPIs'\n\n/* 10 rows from merchant_performance table\nPARENT_AGGREGATE_MERCHANT_ID\tPARENT_AGGREGATE_MERCHANT_NAME\tPERIOD_DATE\tPERIOD_QUARTER\tREGION_DESCRIPTION\tCOUNTRY_DESCRIPTION\tINDUSTRY_DESCRIPTION\tFRAUD_AMOUNT_USD\tCLEARED_USD\tFIRST_CHARGEBACK_AMOUNT_USD\tAPPROVAL_RATE\tDECLINED_AUTHORIZATION_COUNT\tAUTHORIZED_COUNT\tDECLINE_RATE\tCROSS_BORDER_FRAUD_AMOUNT_USD\tPEER_FRAUD_AMOUNT_USD\tPEER_CLEARED_USD\tPEER_FIRST_CHARGEBACK_AMOUNT_USD\tPEER_APPROVAL_RATE\tPEER_DECLINED_AUTHORIZATION_COUNT\tPEER_AUTHORIZED_COUNT\tPEER_DECLINE_RATE\tPEER_CROSS_BORDER_FRAUD_AMOUNT_USD\tALERTS_REPORTED_FRAUD_COUNT\tALERTS_REPORTED_DISPUTE_COUNT\tCLARITY_LOOKUPS_COUNT\tCLARITY_NEGATING_EVENTS_COUNT\tCLARITY_DEFLECTION_COUNT\n10000111\tABC WHOLESALE CORPORATION\t2023-05-31\tQ2 2023\tEUROPE\tSPAIN\tAutomotive Fuel\t0\t351786.650000001\t0\t94.833000\t345\t6677\t5.167000\t0\t8.72\t2059510.28\t0\t95.317207\t2596\t55437\t4.682793\t3.49\t0\t0\t0\t0\t0\n10000111\tABC WHOLESALE CORPORATION\t2023-05-31\tQ2 2023\tLATIN AMERICA\tMEXICO\tAutomotive Fuel\t71.46\t1274537.52\t0\t96.200200\t1467\t38607\t3.799800\t23.58\t68.33\t256302.25\t0\t96.607955\t701\t20666\t3.392045\t27.33\t24\t0\t24\t0\t-6\n10000111\tABC WHOLESALE CORPORATION\t2023-05-31\tQ2 2023\tASIA/PACIFIC\tJAPAN\tWholesale Clubs\t69.95\t124096912.47\t0\t96.969600\t45773\t1510481\t3.030400\t23.08\t145355\t1508746971.87\t55761.46\t95.636428\t1251911\t28690048\t4.363572\t58142\t23\t0\t23\t0\t-5\n10000111\tABC WHOLESALE CORPORATION\t2023-05-31\tQ2 2023\tEUROPE\tUNITED KINGDOM\tAutomotive Fuel\t323.34\t52677366.78\t0\t98.875900\t8685\t772615\t1.124100\t106.7\t3576.25\t127226605.2\t49.05\t95.657320\t196905\t4534182\t4.342680\t1430.5\t108\t0\t108\t1\t-25\n10000111\tABC WHOLESALE CORPORATION\t2023-05-31\tQ2 2023\tEUROPE\tUNITED KINGDOM\tWholesale Clubs\t346.11\t174474820.48\t0\t96.444500\t62929\t1769908\t3.555500\t114.22\t145355\t1508746971.87\t55761.46\t95.636428\t1251911\t28690048\t4.363572\t58142\t115\t0\t115\t1\t-27\n10000111\tABC WHOLESALE CORPORATION\t2023-05-31\tQ2 2023\tASIA/PACIFIC\tKOREA, REPUBLIC OF\tWholesale Clubs\t0\t38585.15\t0\t95.729500\t12\t281\t4.270500\t0\t145355\t1508746971.87\t55761.46\t95.636428\t1251911\t28690048\t4.363572\t58142\t0\t0\t0\t0\t0\n10000111\tABC WHOLESALE CORPORATION\t2023-05-31\tQ2 2023\tEUROPE\tSWEDEN\tWholesale Clubs\t0\t20200.22\t0\t96.735400\t38\t1164\t3.264600\t0\t145355\t1508746971.87\t55761.46\t95.636428\t1251911\t28690048\t4.363572\t58142\t0\t0\t0\t0\t0\n10000111\tABC WHOLESALE CORPORATION\t2023-05-31\tQ2 2023\tEUROPE\tSPAIN\tWholesale Clubs\t0\t1723722.57\t0\t86.508800\t3469\t25713\t13.491200\t0\t145355\t1508746971.87\t55761.46\t95.636428\t1251911\t28690048\t4.363572\t58142\t0\t0\t0\t0\t0\n10000111\tABC WHOLESALE CORPORATION\t2023-05-31\tQ2 2023\tASIA/PACIFIC\tMALDIVES\tWholesale Clubs\t0\t155.42\t0\t100.000000\t0\t29\t0.000000\t0\t145355\t1508746971.87\t55761.46\t95.636428\t1251911\t28690048\t4.363572\t58142\t0\t0\t0\t0\t0\n10000111\tABC WHOLESALE CORPORATION\t2023-05-31\tQ2 2023\tUNITED STATES\tUNITED STATES\tAutomotive Fuel\t20\t120557648.55\t6.59\t97.116600\t77739\t2696116\t2.883400\t6.6\t201703.65\t655547673.08\t121687.17\t97.681269\t491099\t21179644\t2.318731\t80681.46\t7\t2\t9\t0\t0\n*/\n\nUnless the user specifies in the question always limit the results of the SQL query to 5. \nWhenever user ask to calculate ratio then make sure to use DIV0 snowflake function. \nYou must query only the columns that are needed to answer the question. \nAlways use parent_aggregate_merchant_id=10000111\nif someone asks \"my name\" then refer to PARENT_AGGREGATE_MERCHANT_NAME column\nIf someone asks to compare data with peers then compare respective column with the column prefixed with \"PEER_\".\nIf someone mentions \"performance\" then they really mean \"volume\".\nIf someone ask for \"my chargeback\" or \"my Fraud\" or \"my declined\" then use columns are not prefixed with \"ALERTS_\" or \"CLARITY_\" or \"PEER_\".\ndo not use alias for 'PERIOD_DATE' column\nif group by 'PERIOD_DATE' column then include 'PERIOD_DATE' in the select list\nfor \"fraud volume\" column is used in the resultant SQL query then use column alias 'FRAUD_VOLUME'\nfor \"chartback volume\" column is used in the resultant SQL query then use column alias 'CB_VOLUME'\nfor \"number of fraudulant transaction\" or \"fraud count\" use column alias 'FRAUD_COUNT'\nfor \"number of chargebacks\" or \"chargeback count\" use column alias 'CB_COUNT'\nprefix the alias with \"PEER_\" for columns prefixed \"PEER_\"\n\nsome examples below\nuser: what is my name?\nSQL query: select distinct parent_aggregate_merchant_name as merchant_name from FROM merchant_performance WHERE PARENT_AGGREGATE_MERCHANT_ID=10000111\n\nuser: how do i compare against my peers in total cross border fraud performance?\nSQL query: SELECT top 12 period_date, sum(cross_border_fraud_amount_usd) as cross_border_fraud_amount_usd, sum(peer_cross_border_fraud_amount_usd) peer_cross_border_fraud_amount_usd FROM merchant_performance WHERE parent_aggregate_merchant_id = 10000111 GROUP BY PERIOD_DATE ORDER BY PERIOD_DATE DESC\n\nuser: how do i compare against my peers in fraud performance within united states?\nSQL query: SELECT top 12 period_date, sum(fraud_amount_usd) as fraud_amount_usd, sum(peer_fraud_amount_usd) peer_fraud_amount_usd FROM merchant_performance WHERE parent_aggregate_merchant_id = 10000111 and region_description = 'UNITED STATES' GROUP BY PERIOD_DATE ORDER BY PERIOD_DATE DESC\n\nuser: show me ethoca insights for the month of march and april 2023\nSQL query: SELECT PERIOD_DATE, SUM(clarity_lookups_count) AS receipts_lookups,SUM(alerts_reported_fraud_count) AS reported_fraud, SUM(alerts_reported_dispute_count) AS reported_disputes, SUM(clarity_negating_events_count) AS fraud_dispute_not_deflected, SUM(clarity_deflection_count) AS fraud_dispute_deflected FROM merchant_performance WHERE PARENT_AGGREGATE_MERCHANT_ID = 10000111 AND PERIOD_DATE in ('2023-03-31','2023-04-30') GROUP BY PERIOD_DATE ORDER BY PERIOD_DATE DESC\n\nYou must always output your answer in JSON format with the following key-value pairs:\n- \"input\": input question\n- \"query\": the SQL query that you generated\n- \"error\": an error message if the query is invalid, or null if the query is valid\n- \"text-result\" : describe input and the generated SQL query in your own words or in natural language without using the word \"SQL\" or \"query\". address user as \"you\". do not include ID information\n- \"fraudvol_asked\" : \"true\" if input contains \"fraud volume\" else \"false\"\n- \"cbvol_asked\" : \"true\" if input contains \"cb volume\" or \"chargeback volume\" else \"false\"\n- \"fraudcnt_asked\" : \"true\" if input contains \"fraud count\" or \"number of fraudulant transactions\" else \"false\"\n- \"cbvolcnt_asked\" : \"true\" if input contains \"cb count\" or \"number of chargebacks\" else \"false\"\n- \"peerinfo_asked\" : \"true\" if input contains \"peer\" or \"my peer\" else \"false\"\n- \"date_exist\" : \"true\" if SQL query contains \"PERIOD_DATE\" column else \"false\"\n- \"is_summary\" : \"true\" if input contains \"ethoca insights\" or \"insights\" else \"false\"\n"}]

question = st.chat_input("How can I help you?")
if question:
      with st.spinner("In progress..."):
            message_text.append({"role":"user","content":question})
            # record the time before the request is sent
            start_time = time.time()
            response = openai.ChatCompletion.create(
              engine="mbaig-gpt4",
              messages = message_text,
              temperature=0.7,
              max_tokens=800,
              top_p=0.95,
              frequency_penalty=0,
              presence_penalty=0,
              stop=None
              #stream=True
            )

            raw_response = response;
            result_string = raw_response.choices[0].message.content
            result_json = json.loads(result_string)
            
            question = result_json["input"]
            sql_query = result_json["query"]
            text_result = result_json["text-result"]

            st.write(text_result)
            
            expander = st.expander("Inspect")
            expander.write(raw_response)
            expander.write(result_json)

            df = dbconn.query_db(sql_query)
            st.write("Preparing output...")
            
            expander.code(df.columns.values.tolist())
            expander.code(df.to_json())
            
            row_count = len(df)
            col_count = len(df.columns)
            if result_json["is_summary"] == "true":
                  #st.bar_chart(df, x = "PERIOD_DATE", y = ["RECEIPTS_LOOKUPS","REPORTED_FRAUD","REPORTED_DISPUTES","FRAUD_DISPUTE_NOT_DEFLECTED","FRAUD_DISPUTE_DEFLECTED"])
                  col1, col2, col3, col4, col5 = st.columns(5)
                  if row_count == 1:
                        col1.metric("RECEIPT LOOKUPS", df["RECEIPTS_LOOKUPS"].iloc[0])
                        col2.metric("REPORTED FRAUD", df["REPORTED_FRAUD"].iloc[0])
                        col3.metric("REPORTED DISPUTES", df["REPORTED_DISPUTES"].iloc[0])
                        col4.metric("FRAUD/DISPUTE NOT DEFLECTED", df["FRAUD_DISPUTE_NOT_DEFLECTED"].iloc[0])
                        col5.metric("FRAUD/DISPUTE DEFLECTED", df["FRAUD_DISPUTE_DEFLECTED"].iloc[0])
                  elif row_count == 2:
                        col1.metric("RECEIPT LOOKUPS", df["RECEIPTS_LOOKUPS"].iloc[0], str(df["RECEIPTS_LOOKUPS"].iloc[0]-df["RECEIPTS_LOOKUPS"].iloc[1]))
                        col2.metric("REPORTED FRAUD", df["REPORTED_FRAUD"].iloc[0], str(df["REPORTED_FRAUD"].iloc[0]-df["REPORTED_FRAUD"].iloc[1]))
                        col3.metric("REPORTED DISPUTES", df["REPORTED_DISPUTES"].iloc[0], str(df["REPORTED_DISPUTES"].iloc[0]-df["REPORTED_DISPUTES"].iloc[1]))
                        col4.metric("FRAUD/DISPUTE NOT DEFLECTED", df["FRAUD_DISPUTE_NOT_DEFLECTED"].iloc[0], str(df["FRAUD_DISPUTE_NOT_DEFLECTED"].iloc[0]-df["FRAUD_DISPUTE_NOT_DEFLECTED"].iloc[1]))
                        col5.metric("FRAUD/DISPUTE DEFLECTED", df["FRAUD_DISPUTE_DEFLECTED"].iloc[0], str(df["FRAUD_DISPUTE_DEFLECTED"].iloc[0]-df["FRAUD_DISPUTE_DEFLECTED"].iloc[1]))
                  else:
                        st.line_chart(df, x = "PERIOD_DATE", y = ["RECEIPTS_LOOKUPS","REPORTED_FRAUD","REPORTED_DISPUTES","FRAUD_DISPUTE_NOT_DEFLECTED","FRAUD_DISPUTE_DEFLECTED"])
                        st.dataframe(df, hide_index=True)
            else:
                  st.dataframe(df, hide_index=True)
