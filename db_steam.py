import streamlit as st

conn = st.connection("my_database")  # sqlalchemy 설치 필요.
df = conn.query("SELECT * FROM trades")
st.dataframe(df)
