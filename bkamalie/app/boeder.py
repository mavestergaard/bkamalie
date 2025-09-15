from bkamalie.app.utils import get_fines, get_secret
from bkamalie.database.execute import insert_fines
from bkamalie.database.model import FineCategory
import streamlit as st
import polars as pl
from bkamalie.database.utils import (
    get_connection as get_db_connection,
    get_db_config_from_secrets,
)
from bkamalie.holdsport.api import (
    get_members,
    get_connection as get_holdsport_connection,
)
from streamlit import session_state as ss

st.logo("bkamalie/graphics/bka_logo.png")

holdsport_con = get_holdsport_connection(
    get_secret("holdsport_username"), get_secret("holdsport_password")
)
members = [
    {"id": member.id, "name": member.name, "role": member.role.to_string()}
    for member in get_members(holdsport_con, ss.selected_team_id)
]
df_members = pl.DataFrame(members)

db_config = get_db_config_from_secrets()
db_con = get_db_connection(db_config)

st.header("Bøde Oversigt", divider=True)

df_fines = get_fines(db_con, ss.selected_team_id)

st.dataframe(df_fines)


@st.dialog("Upload New Fines")
def upload_new_fines(db_con) -> None:
    uploaded_file = st.file_uploader("Upload CSV file with fines", type="csv")
    df_new_fines = (
        pl.read_csv(uploaded_file) if uploaded_file is not None else pl.DataFrame()
    )
    st.dataframe(df_new_fines)
    if st.button("Upload nye bøder", type="primary"):
        try:
            insert_fines(db_con, df_new_fines)
            st.success("Nye bøder uploaded", icon="✅")
            st.rerun()
        except Exception as e:
            raise e


if st.button("Upload New Fines", type="primary"):
    # add some validation here
    upload_new_fines(db_con)


@st.dialog("Upload New Fines")
def create_new_fine(db_con) -> None:
    fine_name = st.text_input("Bøde Navn")
    fixed_amount = st.number_input("Fast Beløb", value=0)
    variable_amount = st.number_input("Variabelt Beløb", value=0)
    description = st.text_area("Beskrivelse", value=None)
    category = st.selectbox("Kategori", options=FineCategory)
    df_new_fines = pl.DataFrame(
        [
            {
                "name": fine_name,
                "fixed_amount": fixed_amount,
                "variable_amount": variable_amount,
                "holdbox_amount": 0,
                "description": description,
                "category": category,
                "team_id": ss.selected_team_id,
            }
        ]
    )
    if st.button("Upload nye bøder", type="primary"):
        try:
            insert_fines(db_con, df_new_fines)
            st.success("Nye bøder uploaded", icon="✅")
            st.rerun()
        except Exception as e:
            raise e


if st.button("Create New Fine", type="primary"):
    create_new_fine(db_con)
