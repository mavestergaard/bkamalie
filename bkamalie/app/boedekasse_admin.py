from bkamalie.database.execute import insert_payment, upsert_recorded_fines
from bkamalie.database.model import FineStatus, Payment, RecordedFine
import streamlit as st
from bkamalie.holdsport.api import FINEBOX_ADMIN_MEMBER_ID, get_members, get_connection as get_holdsport_connection
from datetime import datetime, date
import polars as pl
from bkamalie.app.utils import login, render_page_links, fines_overview_detail_cols, fines_overview_show_cols
from bkamalie.database.utils import get_connection as get_db_connection

render_page_links()

if st.button("Login", type="primary"):
    login()

st.title("Bødekassen Admin")

if (not st.session_state.logged_in) & (st.session_state.current_user_id in [FINEBOX_ADMIN_MEMBER_ID, 1412409]):
    st.stop()


holdsport_con = get_holdsport_connection(st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"])
db_con = get_db_connection(st.secrets["db"])

members = [{"id":member.id, "name":member.name, "role":member.role.to_string()} for member in get_members(holdsport_con, 5289)]
df_members = pl.DataFrame(members)

df_fines = pl.read_database_uri(query="SELECT * FROM fine", uri=db_con)
df_recorded_fines = pl.read_database_uri(query="SELECT * FROM recorded_fines", uri=db_con)
df_payments = pl.read_database_uri(query="SELECT * FROM payment", uri=db_con)

df_fine_overview = df_recorded_fines.join(df_fines, left_on="fine_id", right_on="id", how='left').join(df_members, left_on="fined_member_id", right_on="id", how='left', suffix="_member").with_columns(
    (pl.col("fixed_amount") * pl.col("fixed_count") + pl.col("variable_amount") * pl.col("variable_count")).alias("total_fine"),
    (pl.col("holdbox_amount") * pl.col("holdbox_count")).alias("total_holdboxes"),
)


df_fines_pending = df_fine_overview.filter(fine_status="Pending")

@st.dialog("Opdater Bøder", width="large")
def update_fines(df_fines_pending_current: pl.DataFrame):
    column_config={
        "Bøde Status": st.column_config.SelectboxColumn(
            options=FineStatus,
            required=True,
        )
    }
    df_fines_edited = st.data_editor(
        df_fines_pending_current.select(fines_overview_show_cols),
        column_config=column_config,
        disabled=[col for col in df_fines_pending_current.columns if col != "Bøde Status"]
    )
    if st.button("Submit"):
        df_fines_updated = df_fines_pending_current.filter(pl.col("fine_status")!=df_fines_edited['Bøde Status'])
        df_fines_updated = df_fines_updated.with_columns(fine_status=df_fines_edited['Bøde Status']).select(list(RecordedFine.model_fields))
        if len(df_fines_updated) == 0:
            st.info("No changes made")
        else:
            try:
                upsert_recorded_fines(db_con, df_fines_updated)
                st.success("Fines updated")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

with st.container(border=True):
    st.subheader("Afventende Bøder")
    show_details = st.toggle("Show Details", False)
    extra_cols = fines_overview_detail_cols if show_details else []
    st.dataframe(df_fines_pending.select(fines_overview_show_cols + extra_cols).sort("Bøde Dato", descending=True), use_container_width=True)
    if st.button("Opdater Afventende Bøder"):
        update_fines(df_fines_pending)


@st.dialog("Register Payment")
def register_payment(df_members:pl.DataFrame):
    betaler = st.selectbox("Vælg betaler", df_members['name'])
    betalt_beløb = st.number_input("Beløb", 0)
    betalt_dato = st.date_input("Dato", date.today())
    if st.button("Submit"):
        member_id = df_members.filter(name=betaler)['id']
        payment = Payment(
            member_id=member_id,
            amount=betalt_beløb,
            payment_date=betalt_dato
        )
        try:
            insert_payment(payment)
            st.success("Fines updated")
        except Exception as e:
            st.error(f"Error: {e}")


with st.container(border=True):
    st.subheader("Betalinger Modtaget")
    st.dataframe(df_payments.sort("payment_date", descending=True))
    if st.button("Register Betaling"):
        register_payment(df_members)
