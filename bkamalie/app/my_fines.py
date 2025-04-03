from bkamalie.database.model import FineStatus
import streamlit as st
from bkamalie.holdsport.api import get_members, get_connection as get_holdsport_connection
import polars as pl
from bkamalie.app.utils import _suggest_fines, get_fines, login, render_page_links
from bkamalie.database.utils import get_connection as get_db_connection

holdsport_con = get_holdsport_connection(st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"])
members = [{"id":member.id, "name":member.name, "role":member.role.to_string()} for member in get_members(holdsport_con, 5289)]
df_members = pl.DataFrame(members)
render_page_links(df_members)

st.title("Mine Bøder")

if not st.session_state.logged_in:
    if st.button("Login", type="primary"):
        login()
    st.stop()



holdsport_con = get_holdsport_connection(st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"])
db_con = get_db_connection(st.secrets["db"])
df_fines = get_fines(db_con)
df_recorded_fines = pl.read_database_uri(
        query="SELECT * FROM recorded_fines", uri=db_con
    )
df_payments = pl.read_database_uri(query="SELECT * FROM payment", uri=db_con).filter(member_id=st.session_state.current_user_id)

df_fine_overview = df_recorded_fines.join(
    df_fines, left_on="fine_id", right_on="id", how="left"
).join(
    df_members, left_on="fined_member_id", right_on="id", how="left", suffix="_member"
).join(
    df_members,
    left_on="created_by_member_id",
    right_on="id",
    how="left",
    suffix="_stikker",
).filter(
    fined_member_id=st.session_state.current_user_id,
    )

df_fines_accepted = df_fine_overview.filter(
    fine_status=FineStatus.ACCEPTED,
)

bøde_sum = df_fines_accepted["total_fine"].sum()
betalt_sum = df_payments["amount"].sum()
total_udestående = bøde_sum - betalt_sum
col1, col2, col3  = st.columns(3)
col1.metric("Total Bøder", str(bøde_sum) + " DKK", border=True)
col2.metric("Total Betalt", str(betalt_sum) + " DKK", border=True)
col3.metric("Total Udestående", str(total_udestående) + " DKK", border=True)

phone_number = "50485676"  # Replace with your MobilePay number

mobilepay_link = f"https://qr.mobilepay.dk/box/8aef8321-e717-4f09-bb62-aaff8fef69f1/pay-in"

st.link_button("Betal med MobilePay","https://qr.mobilepay.dk/box/8aef8321-e717-4f09-bb62-aaff8fef69f1/pay-in", type="primary")

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
        "pending" if row["fine_status"] == "Pending"
        else "declined" if row["fine_status"] == "Declined"
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
for row in df_fine_overview.sort(["fine_date", "updated_at"], descending=True).to_dicts():
    st.markdown(create_fine_cards(row), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)