import streamlit as st
import json
import pandas as pd
from sqlalchemy import create_engine

#loading secrets
username = st.secrets["username"]
password = st.secrets["password"]
warehouse = st.secrets["warehouse"]
role = st.secrets["role"]
snowflake_account = st.secrets["account"]
database = st.secrets["database"]
schema = st.secrets["schema"]
        
#dbsetup
def get_conn():
  snowflake_url = f"snowflake://{username}:{password}@{snowflake_account}/{database}/{schema}?warehouse={warehouse}&role={role}"
  db = create_engine(snowflake_url)
  return db
#query and return dataframe
def query_db(sql):
  conn = get_conn()
  df = pd.read_sql_query(sql, conn)
  #df.columns = df.columns.str.upper()
  return df    



