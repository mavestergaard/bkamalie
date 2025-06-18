from bkamalie.database.execute import (
    insert_payment,
    upsert_payments,
    upsert_recorded_fines,
    upsert_recorded_fines_from_basemodel,
)
from bkamalie.database.model import FineStatus, Payment, RecordedFine
import streamlit as st
from bkamalie.holdsport.api import (
    FINEBOX_ADMIN_MEMBER_ID,
    get_members,
    get_connection as get_holdsport_connection,
)
from datetime import date, datetime
import polars as pl
from bkamalie.app.utils import (
    get_fines,
    login,
    render_page_links,
    fines_overview_detail_cols,
    fines_overview_show_cols,
)
from bkamalie.database.utils import get_connection as get_db_connection
import polars.selectors as cs

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
        ),
        "id": None,
    }
    df_fines_edited = st.data_editor(
        df_fines_pending_current,
        column_config=column_config,
        disabled=[
            col for col in df_fines_pending_current.columns if col != "Bøde Status"
        ],
    )
    if st.button("Submit"):
        df_fines_updated = df_fines_edited.filter(
            pl.col("Bøde Status") != df_fines_pending_current["Bøde Status"]
        )
        fines_overview_show_cols_reversed = [
            pl.col(expr.meta.output_name()).alias(expr.meta.root_names()[0])
            for expr in fines_overview_show_cols
        ]

        df_fines_updated = df_fines_updated.select(
            fines_overview_show_cols_reversed
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


def update_fine(recorded_fine: RecordedFine, new_status: FineStatus):
    """Update a single fine's status"""
    if new_status != recorded_fine.fine_status:
        recorded_fine.fine_status = new_status
        recorded_fine.updated_at = datetime.now()
        recorded_fine.updated_by_member_id = st.session_state.current_user_id
        return recorded_fine


@st.dialog("Opdater Bøder", width="large")
def update_fines_new(
    recorded_fines: list[RecordedFine], df_members, df_fines, session_state_prefix: str
):
    members_dict = {row.get("id"): row.get("name") for row in df_members.to_dicts()}
    fines_dict = {row.get("id"): row.get("name") for row in df_fines.to_dicts()}
    status_chars = {
        "Accepted": ":green[A]",
        "Pending": ":orange[P]",
        "Declined": ":red[D]",
    }
    for fine in recorded_fines:
        (
            col_fine_name,
            col_member_name,
            col_fine_counts,
            col_fine_amount,
            col_fine_status,
        ) = st.columns([0.35, 0.25, 0.1, 0.1, 0.2])
        member_name = members_dict.get(fine.fined_member_id).strip()
        fine_name = fines_dict.get(fine.fine_id)
        col_fine_name.badge(f"**{fine_name}**", color="primary")
        col_member_name.badge(f"**{member_name}**", color="primary")
        col_fine_counts.badge(
            f"F:{fine.fixed_count} V:{fine.variable_count}", color="primary"
        )
        col_fine_amount.badge(f"{fine.total_fine:,} kr.", color="primary")
        col_fine_status.pills(
            "Fine Status",
            FineStatus,
            format_func=lambda status: f"{status_chars[status]}",
            selection_mode="single",
            default=fine.fine_status,
            label_visibility="collapsed",
            key=f"{session_state_prefix}_{fine.id}",
        )
        st.markdown(
            """<hr style="margin: 2px 0; border: none; border-top: 1px solid #CCC;">""",
            unsafe_allow_html=True,
        )

    if st.button("Submit", key="upsert_fines_new"):
        updated_fines = [
            updated_fine
            for recorded_fine in recorded_fines
            if (
                updated_fine := update_fine(
                    recorded_fine,
                    st.session_state[f"{session_state_prefix}_{recorded_fine.id}"],
                )
            )
            is not None
        ]
        st.write(len(updated_fines))
        if len(updated_fines) == 0:
            st.info("No changes made")
        else:
            try:
                upsert_recorded_fines_from_basemodel(db_con, updated_fines)
                st.success("Fines updated")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


with st.container(border=True):
    recorded_fines = [RecordedFine(**row) for row in df_fines_pending.to_dicts()]
    show_details = st.toggle("Show Details", False)
    extra_cols = fines_overview_detail_cols if show_details else []
    df_fines_pending = df_fines_pending.select(
        fines_overview_show_cols + extra_cols
    ).sort("Bøde Dato", descending=True)
    st.dataframe(
        df_fines_pending,
        column_config={"id": None},
        use_container_width=True,
    )
    if st.button("Opdater Afventende Bøder Ny"):
        update_fines_new(recorded_fines, df_members, df_fines, "updated_fine_status")

with st.container(border=True):
    st.subheader("Opdater Bøde Status")
    selected_member = st.multiselect(
        "Vælg Medlem",
        options=df_members["name"].to_list(),
        max_selections=1,
    )
    if selected_member:
        df_fines_member = df_fine_overview.filter(
            pl.col("name_member").is_in(selected_member)
        ).sort("fine_date", descending=True)
        st.dataframe(
            df_fines_member.select(fines_overview_show_cols + extra_cols).sort(
                "Bøde Dato", descending=True
            ),
            use_container_width=True,
        )
        if st.button("Opdater Bøde Status"):
            update_fines(df_fines_member)
    else:
        st.warning("Vælg et medlem for at opdatere bøder")


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


with st.container(border=True):
    st.subheader("Medlemsoversigt - bøder vs betalinger")
    df_payments_grouped = df_payments.group_by("member_id", "name").agg(
        amount_pending=pl.when(pl.col("payment_status") == FineStatus.PENDING)
        .then(pl.col("amount"))
        .otherwise(0)
        .sum(),
        amount_paid=pl.when(pl.col("payment_status") == FineStatus.ACCEPTED)
        .then(pl.col("amount"))
        .otherwise(0)
        .sum(),
    )
    df_fines_summed = df_fine_overview.group_by("fined_member_id", "name_member").agg(
        amount_fined_pending=pl.when(pl.col("fine_status") == FineStatus.PENDING)
        .then(pl.col("total_fine"))
        .otherwise(0)
        .sum(),
        amount_fined=pl.when(pl.col("fine_status") == FineStatus.ACCEPTED)
        .then(pl.col("total_fine"))
        .otherwise(0)
        .sum(),
    )
    df_overview = df_fines_summed.join(
        df_payments_grouped,
        left_on=["fined_member_id", "name_member"],
        right_on=["member_id", "name"],
        how="outer",
        coalesce=True,
    ).with_columns(cs.numeric().fill_null(0))
    df_overview = df_overview.with_columns(
        amount_due=pl.col("amount_paid") - pl.col("amount_fined")
    ).sort("amount_due")

    bødesum_accepteret = df_overview["amount_fined"].sum()
    bødesum_til_godkendelse = df_overview["amount_fined_pending"].sum()
    indbetalinger_accepteret = df_overview["amount_paid"].sum()
    indbetalinger_til_godkendelse = df_overview["amount_pending"].sum()

    col1, col2 = st.columns(2)
    col1.metric("Bødesum - Accepted", str(bødesum_accepteret) + " DKK", border=True)
    col2.metric(
        "Bødesum - Til Godkendelse", str(bødesum_til_godkendelse) + " DKK", border=True
    )
    col1.metric(
        "Indbetalinger - Accepted", str(indbetalinger_accepteret) + " DKK", border=True
    )
    col2.metric(
        "Indebetalinger - Til Godkendelse",
        str(indbetalinger_til_godkendelse) + " DKK",
        border=True,
    )

    st.dataframe(df_overview)
