from bkamalie.app.utils import get_fines, login, render_page_links
import streamlit as st
import polars as pl
from bkamalie.database.utils import get_connection as get_db_connection
from bkamalie.holdsport.api import (
    get_members,
    get_connection as get_holdsport_connection,
)

holdsport_con = get_holdsport_connection(
    st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"]
)
members = [
    {"id": member.id, "name": member.name, "role": member.role.to_string()}
    for member in get_members(holdsport_con, 5289)
]
df_members = pl.DataFrame(members)
render_page_links()

db_config = st.secrets["db"]
db_con = get_db_connection(db_config)

st.title("Bøde Oversigt")

if not st.session_state.logged_in:
    if st.button("Login", type="primary"):
        login()
    st.stop()

df_fines = get_fines(db_con)


st.dataframe(df_fines)
