from bkamalie.database.model import FineStatus
import streamlit as st
from bkamalie.holdsport.api import (
    get_members,
    get_connection as get_holdsport_connection,
)
import polars as pl
from bkamalie.app.utils import _suggest_fines, get_fines
from bkamalie.database.utils import get_connection as get_db_connection

st.logo("bkamalie/graphics/bka_logo.png")

holdsport_con = get_holdsport_connection(
    st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"]
)
members = [
    {"id": member.id, "name": member.name, "role": member.role.to_string()}
    for member in get_members(holdsport_con, 5289)
]
df_members = pl.DataFrame(members)


st.header("Stikkerlinjen", divider=True)

holdsport_con = get_holdsport_connection(
    st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"]
)
db_con = get_db_connection(st.secrets["db"])
df_fines = get_fines(db_con)
df_recorded_fines = pl.read_database_uri(
    query="SELECT * FROM recorded_fines", uri=db_con
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
    .join(
        df_members,
        left_on="created_by_member_id",
        right_on="id",
        how="left",
        suffix="_stikker",
    )
)


@st.dialog("Tip Bødekassemesteren")
def suggest_fines(db_con, df_members, df_fines):
    selected_members = st.multiselect("Vælg Synder", df_members["name"])
    selected_fine = st.multiselect("Vælg Bøde", df_fines["name"], max_selections=1)
    df_selected_fine = (
        df_fines.filter(name=selected_fine[0]) if selected_fine else df_fines.head(0)
    )
    coll, col2, col3 = st.columns(3)

    fixed_amount = df_selected_fine["fixed_amount"].item() if selected_fine else 0
    coll.metric("Fixed Amount", fixed_amount)
    number_of_fines_fixed = coll.number_input("Antal", value=1, key="fixed")

    variable_amount = df_selected_fine["variable_amount"].item() if selected_fine else 0
    col2.metric("Varaible Amount", variable_amount)
    number_of_fines_variable = col2.number_input("Antal", value=0, key="variable")

    holdbox_amount = df_selected_fine["holdbox_amount"] if selected_fine else 0
    col3.metric("Holdboxe", holdbox_amount)
    number_of_holdboxe = col3.number_input("Antal", value=0, key="holdbox")

    comment = st.text_input("Tilføj kommentar", None)
    if st.button("Suggest fine"):
        try:
            _suggest_fines(
                db_con=db_con,
                members=selected_members,
                selected_fine=selected_fine,
                df_fines=df_fines,
                count_fixed=number_of_fines_fixed,
                count_variable=number_of_fines_variable,
                count_holdbox=number_of_holdboxe,
                df_members=df_members,
                suggested_by_user_id=st.session_state.current_user_id,
                comment=comment,
            )
            st.success("Fine suggested")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


if st.button("Tip Bødekassemesteren", type="primary"):
    suggest_fines(db_con, df_members, df_fines)

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
