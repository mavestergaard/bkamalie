from bkamalie.database.execute import insert_payment
from bkamalie.database.model import FineStatus, Payment
import streamlit as st
from streamlit import session_state as ss
from bkamalie.holdsport.api import (
    FINEBOX_ADMIN_MEMBER_ID,
    get_members,
    get_connection as get_holdsport_connection,
)
import polars as pl
from bkamalie.app.utils import get_fines, get_secret
from bkamalie.database.utils import (
    get_connection as get_db_connection,
    get_db_config_from_secrets,
)
from datetime import datetime
from bkamalie.css_styles.payment_card import (
    get_payment_card_style,
    get_payment_card_html,
)
from bkamalie.app.model import DisplayPayment


st.logo("bkamalie/graphics/bka_logo.png")


holdsport_con = get_holdsport_connection(
    get_secret("holdsport_username"), get_secret("holdsport_password")
)
db_config = get_db_config_from_secrets()
db_con = get_db_connection(db_config)

members = [
    {"id": member.id, "name": member.name, "role": member.role.to_string()}
    for member in get_members(holdsport_con, ss.selected_team_id)
]
df_members = pl.DataFrame(members)

st.header("Mine Bøder", divider=True)

df_fines = get_fines(db_con, ss.selected_team_id)
df_recorded_fines = pl.read_database_uri(
    query=f"SELECT * FROM recorded_fines where team_id = {ss.selected_team_id}",
    uri=db_con,
)
df_payments = (
    pl.read_database_uri(
        query=f"SELECT * FROM payments where team_id = {ss.selected_team_id}",
        uri=db_con,
    )
    .filter(member_id=ss.current_user_id)
    .join(df_members, left_on="member_id", right_on="id", how="left", suffix="_member")
    .rename({"name": "member_name"})
)

df_payments_paid = df_payments.filter(payment_status=FineStatus.ACCEPTED)

df_fine_overview = (
    df_recorded_fines.join(df_fines, left_on="fine_id", right_on="id", how="left")
    .join(
        df_members,
        left_on="fined_member_id",
        right_on="id",
        how="left",
        suffix="_member",
    )
    .join(
        df_members,
        left_on="created_by_member_id",
        right_on="id",
        how="left",
        suffix="_stikker",
    )
    .filter(
        fined_member_id=ss.current_user_id,
    )
)

df_fines_accepted = df_fine_overview.filter(
    fine_status=FineStatus.ACCEPTED,
)

bøde_sum = df_fines_accepted["total_fine"].sum()
betalt_sum = df_payments_paid["amount"].sum()
amount_pending = df_payments.filter(payment_status=FineStatus.PENDING)["amount"].sum()
total_udestående = bøde_sum - betalt_sum
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Bøder", str(bøde_sum) + " DKK", border=True)
col2.metric("Total Betalt", str(betalt_sum) + " DKK", border=True)
col3.metric("Afventer Godkendelse", str(amount_pending) + " DKK", border=True)
col4.metric("Total Udestående", str(total_udestående) + " DKK", border=True)

phone_number = "50485676"  # Replace with your MobilePay number

mobilepay_link = (
    "https://qr.mobilepay.dk/box/8aef8321-e717-4f09-bb62-aaff8fef69f1/pay-in"
)


@st.dialog("Betal Udestående")
def pay_fines(db_con, total_udestående, df_members):
    st.link_button(
        "Link til MobilePay",
        "https://qr.mobilepay.dk/box/8aef8321-e717-4f09-bb62-aaff8fef69f1/pay-in",
        type="primary",
        use_container_width=True,
    )
    st.metric("Nuværende Udestående", value=total_udestående, border=True)
    disabled = (
        False if ss.current_user_id in [FINEBOX_ADMIN_MEMBER_ID, 1412409] else True
    )
    selected_member = st.multiselect(
        "Navn",
        options=df_members["name"],
        default=ss.current_user_full_name,
        disabled=disabled,
        max_selections=1,
    )
    payment_date = st.date_input("Betalingsdato", datetime.now())
    amount_paid = st.number_input("Beløb Overført", value=total_udestående)
    if not selected_member:
        st.warning("Vælg et medlem for at registrere betaling")
        st.stop()
    selected_member_id = df_members.filter(name=selected_member[0])["id"][0]
    payments_details = Payment(
        id=None,
        member_id=selected_member_id,
        amount=amount_paid,
        payment_date=payment_date,
        payment_status=FineStatus.PENDING,
        team_id=ss.selected_team_id,
    )
    if st.button("Bekræft betaling", type="primary"):
        try:
            insert_payment(db_con, payments_details)
            st.success("Betaling registreret", icon="✅")
            st.rerun()
        except Exception as e:
            raise e


if st.button("Betal Udestående", type="primary"):
    pay_fines(db_con, total_udestående, df_members)

with st.expander("Betalingshistorik", expanded=False):
    st.markdown(f"{get_payment_card_style()}", unsafe_allow_html=True)

    for row in df_payments.sort(["payment_date"], descending=True).to_dicts():
        payment = DisplayPayment(**row)
        payment_html = get_payment_card_html(payment)
        st.markdown(payment_html, unsafe_allow_html=True)


st.markdown(
    """
    <style>
        .card-container {
            display: flex;
            flex-direction: column;
            width: 100%;
        }
        .fine-card {
            width: 100%;
            padding: 10px 15px;
            margin-bottom: 5px;
            background: #f9f9f9;
            border-left: 6px solid #28A745; /* Default green for accepted */
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 14px;
        }
        .fine-card.pending {
            border-left-color: orange;
        }
        .fine-card.declined {
            border-left-color: red;
        }
        .fine-left {
            flex: 2;
            text-align: left;
        }
        .fine-middle {
            flex: 2;
            text-align: center;
            color: #555;
        }
        .fine-right {
            flex: 1;
            text-align: right;
            color: #555;
        }
        .fine-title {
            font-weight: bold;
        }
        .fine-name {
            font-weight: bold;
            display: block;
        }
        .fine-amount {
            font-weight: bold;
            color: #000;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# Generate flat, wide cards for fines
def create_fine_cards(row: dict[str, str]):
    status_class = (
        "pending"
        if row["fine_status"] == "Pending"
        else "declined"
        if row["fine_status"] == "Declined"
        else "accepted"
    )
    fixed_amount_total = row["fixed_amount"] * row["fixed_count"]
    variable_amount_total = row["variable_amount"] * row["variable_count"]
    html = f"""
    <div class="fine-card {status_class}">
        <div class="fine-left">
            <div class="fine-title">{row['name_member']}</div>
            <div>{row['fine_date'].strftime('%d %b %Y')}</div>
            <div class="fine-name">{row['name']}</div>
        </div>
        <div class="fine-middle">
            Suggested by: {row['name_stikker']} <br>
            Updated at: {row['updated_at'].strftime('%d %b %Y, %H:%M:%S')} <br>
            Comment: {row['comment']}
        </div>
        <div class="fine-right">
            <div>Fixed: {fixed_amount_total} DKK | Variable: {variable_amount_total} DKK </div>
            <div class="fine-amount">{row['total_fine']} DKK</div>
        </div>
    </div>
    """
    return html


st.markdown("<div class='card-container'>", unsafe_allow_html=True)

selection = st.pills("Fine Status", FineStatus, selection_mode="multi")
if selection:
    df_fine_overview = df_fine_overview.filter(pl.col("fine_status").is_in(selection))
for row in df_fine_overview.sort(
    ["fine_date", "updated_at"], descending=True
).to_dicts():
    st.markdown(create_fine_cards(row), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
