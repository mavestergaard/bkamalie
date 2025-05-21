from bkamalie.database.execute import (
    insert_payment,
    upsert_payments,
    upsert_recorded_fines,
)
from bkamalie.database.model import FineStatus, Payment, RecordedFine
import streamlit as st
from bkamalie.holdsport.api import (
    FINEBOX_ADMIN_MEMBER_ID,
    get_members,
    get_connection as get_holdsport_connection,
)
from datetime import date
import polars as pl
from bkamalie.app.utils import (
    get_fines,
    login,
    render_page_links,
    fines_overview_detail_cols,
    fines_overview_show_cols,
)
from bkamalie.database.utils import get_connection as get_db_connection

holdsport_con = get_holdsport_connection(
    st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"]
)
members = [
    {"id": member.id, "name": member.name, "role": member.role.to_string()}
    for member in get_members(holdsport_con, 5289)
]
df_members = pl.DataFrame(members)
render_page_links()

if not st.session_state.logged_in:
    if st.button("Login", type="primary"):
        login()
    st.stop()

if st.session_state.current_user_id not in [FINEBOX_ADMIN_MEMBER_ID, 1412409]:
    st.warning("You do not have permission to access this page")
    st.stop()


st.title("Bødekassen Admin")


holdsport_con = get_holdsport_connection(
    st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"]
)
db_con = get_db_connection(st.secrets["db"])

members = [
    {"id": member.id, "name": member.name, "role": member.role.to_string()}
    for member in get_members(holdsport_con, 5289)
]
df_members = pl.DataFrame(members)
with st.spinner("Loading data...", show_time=True):
    df_fines = get_fines(db_con)
    df_recorded_fines = pl.read_database_uri(
        query="SELECT * FROM recorded_fines", uri=db_con
    )
    df_payments = pl.read_database_uri(query="SELECT * FROM payments", uri=db_con)

df_payments = df_payments.join(
    df_members, left_on="member_id", right_on="id", how="left", suffix="_member"
)

df_fine_overview = (
    df_recorded_fines.join(df_fines, left_on="fine_id", right_on="id", how="left")
    .join(
        df_members,
        left_on="fined_member_id",
        right_on="id",
        how="left",
        suffix="_member",
    )
    .with_columns(
        (
            pl.col("fixed_amount") * pl.col("fixed_count")
            + pl.col("variable_amount") * pl.col("variable_count")
        ).alias("total_fine"),
        (pl.col("holdbox_amount") * pl.col("holdbox_count")).alias("total_holdboxes"),
    )
)


df_fines_pending = df_fine_overview.filter(fine_status="Pending")


@st.dialog("Opdater Bøder", width="large")
def update_fines(df_fines_pending_current: pl.DataFrame):
    column_config = {
        "Bøde Status": st.column_config.SelectboxColumn(
            options=FineStatus,
            required=True,
        )
    }
    df_fines_edited = st.data_editor(
        df_fines_pending_current.select(fines_overview_show_cols),
        column_config=column_config,
        disabled=[
            col for col in df_fines_pending_current.columns if col != "Bøde Status"
        ],
    )
    if st.button("Submit"):
        df_fines_updated = df_fines_pending_current.filter(
            pl.col("fine_status") != df_fines_edited["Bøde Status"]
        )
        df_fines_updated = df_fines_updated.with_columns(
            fine_status=df_fines_edited["Bøde Status"]
        ).select(list(RecordedFine.model_fields))
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
    st.dataframe(
        df_fines_pending.select(fines_overview_show_cols + extra_cols).sort(
            "Bøde Dato", descending=True
        ),
        use_container_width=True,
    )
    if st.button("Opdater Afventende Bøder"):
        update_fines(df_fines_pending)


@st.dialog("Register Payment")
def register_payment(df_members: pl.DataFrame):
    betaler = st.selectbox("Vælg betaler", df_members["name"])
    betalt_beløb = st.number_input("Beløb", 0)
    betalt_dato = st.date_input("Dato", date.today())
    if st.button("Submit"):
        member_id = df_members.filter(name=betaler)["id"]
        payment = Payment(
            member_id=member_id, amount=betalt_beløb, payment_date=betalt_dato
        )
        try:
            insert_payment(payment)
            st.success("Fines updated")
        except Exception as e:
            st.error(f"Error: {e}")


updated_payments = []
with st.container(border=True):
    st.subheader("Betalinger der afventer godkendelse")
    for row in (
        df_payments.filter(payment_status=FineStatus.PENDING)
        .sort(["payment_date"], descending=True)
        .to_dicts()
    ):
        col1, col2, col3 = st.columns(3)
        col1.text_input("Navn", row["name"], disabled=True, key=f"navn_{row['id']}")
        new_date = col2.date_input(
            "Betalingsdato", row["payment_date"], key=f"date_{row['id']}"
        )
        new_amount = col3.number_input(
            "Beløb betalt", value=row["amount"], key=f"amount_{row['id']}"
        )
        new_status = st.pills(
            "Payment Status",
            FineStatus,
            selection_mode="single",
            default=row["payment_status"],
            key=f"status_{row['id']}",
        )
        if new_status != row["payment_status"]:
            updated_payments.append(
                Payment(
                    id=row["id"],
                    member_id=row["member_id"],
                    amount=new_amount,
                    payment_date=new_date,
                    payment_status=new_status,
                )
            )
        st.divider()
    df_updated_payments = pl.DataFrame(updated_payments)
    if st.button("Opdater Betalinger"):
        try:
            upsert_payments(db_con, df_updated_payments)
            st.success(f"{len(df_updated_payments)} Betalinger opdateret")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


with st.container(border=True):
    st.subheader("Betalinger Accepteret")
    st.dataframe(
        df_payments.filter(payment_status=FineStatus.ACCEPTED).sort(
            "payment_date", descending=True
        )
    )

with st.container(border=True):
    st.subheader("Betalinger Afvist")
    st.dataframe(
        df_payments.filter(payment_status=FineStatus.DECLINED).sort(
            "payment_date", descending=True
        )
    )
