import base64
import polars as pl
import streamlit as st
from bkamalie.holdsport.api import verify_user

fines_overview_show_cols = [
    pl.col("name_member").alias("Navn"),
    pl.col("name").alias("Bøde"),
    pl.col("total_fine").alias("Bøde Total"),
    pl.col("total_holdboxes").alias("Holdbox Total"),
    pl.col("fine_status").alias("Bøde Status"),
    pl.col("fine_date").alias("Bøde Dato"),
]

fines_overview_detail_cols = [
    pl.col("fixed_amount").alias("Bødetakst"),
    pl.col("fixed_count").alias("Antal"),
    pl.col("variable_amount").alias("Variable Bødetakst"),
    pl.col("variable_count").alias("Variabelt Antal"),
    pl.col("holdbox_amount").alias("Holdboxe"),
    pl.col("holdbox_count").alias("Holdboxe Antal"),
]

def render_page_links()->None:
    """Call this as the first function in every app script"""
    headers = st.context.headers
    if "localhost" in headers.get("Host"):
        st.session_state.logged_in = True
        st.session_state.current_user_id = 1412409
    st.image("bkamalie/graphics/bka_logo.png")
    col1, col2, col3 = st.columns(3, border=True)
    col1.page_link("dashboard.py", label="Holdsport Dashboard", icon="⚽")
    col2.page_link("boedekasse.py", label="Bødekasse", icon="💰")
    col3.page_link("boedekasse_admin.py", label="Bødekasse Admin", icon="👮‍♂️")
    if "logged_in" not in st.session_state:
        st.warning("Please login to proceed")
        st.session_state.logged_in = False
    else:
        if st.session_state.logged_in:
            st.info(f"Logged in as {st.session_state.current_user_id}")
        else:
            st.warning("Please login to proceed")
        
        
@st.dialog("Login")
def login() -> None:
    st.info("Please login using your Holdsport credentials")
    username = st.text_input("Email", autocomplete="email")
    password = st.text_input("Password", type="password")
    if st.button("Submit"):
        current_user_id = verify_user(username, password)
        if current_user_id:
            st.success("Login successful")
            st.session_state.logged_in = True
            st.session_state.current_user_id = current_user_id
        else:
            st.error("Login failed")
        
        st.rerun()
    

def replace_id_with_name(col_name:str, alias:str, df_members: pl.DataFrame) -> pl.Expr:
    return pl.col(col_name).replace_strict(old=df_members["id"], new=df_members["name"]).alias(alias)