from bkamalie.database.model import RecordedFine, FineStatus
from bkamalie.database.execute import insert_recorded_fines
import streamlit as st
from bkamalie.holdsport.api import MENS_TEAM_ID, FINEBOX_ADMIN_MEMBER_ID, get_members, get_connection as get_holdsport_connection
from datetime import date, datetime
import polars as pl
from bkamalie.app.utils import fines_overview_show_cols, login, render_page_links, fines_overview_detail_cols, replace_id_with_name
from bkamalie.database.utils import get_connection as get_db_connection
import plotly.express as px
from millify import millify


holdsport_con = get_holdsport_connection(st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"])
members = [{"id":member.id, "name":member.name, "role":member.role.to_string()} for member in get_members(holdsport_con, 5289)]
df_members = pl.DataFrame(members)
render_page_links(df_members)

if st.button("Login", type="primary"):
    login()

st.title("Bødekassen")

if not st.session_state.logged_in:
    st.stop()

db_config = st.secrets["db"]
db_con = get_db_connection(db_config)
with st.spinner("Loading data...", show_time=True):
    df_fines = pl.read_database_uri(query="SELECT * FROM fine", uri=db_con)
    df_recorded_fines = pl.read_database_uri(query="SELECT * FROM recorded_fines", uri=db_con)
    df_payments = pl.read_database_uri(query="SELECT * FROM payment", uri=db_con)
    holdsport_con = get_holdsport_connection(st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"])
    members = [{"id":member.id, "name":member.name, "role":member.role.to_string()} for member in get_members(holdsport_con, MENS_TEAM_ID)]
    df_members = pl.DataFrame(members)


# df_fines_issued = pl.read_csv('database/fines_issued.csv')
df_fine_overview = df_recorded_fines.join(df_fines, left_on="fine_id", right_on="id", how='left').join(df_members, left_on="fined_member_id", right_on="id", how='left', suffix="_member")
df_fine_overview = df_fine_overview.with_columns(
    (pl.col("fixed_amount") * pl.col("fixed_count") + pl.col("variable_amount") * pl.col("variable_count")).alias("total_fine"),
    (pl.col("holdbox_amount") * pl.col("holdbox_count")).alias("total_holdboxes"),
)


@st.dialog("Tip Bødekassemesteren")
def suggest_fine():
    selected_member = st.multiselect("Vælg Synder", df_members['name'], max_selections=1)
    selected_fine = st.multiselect("Vælg Bøde", df_fines['name'], max_selections=1)
    df_selected_fine = df_fines.filter(name=selected_fine[0]) if selected_fine else df_fines.head(0)
    coll, col2, col3 = st.columns(3)

    number_of_fines_fixed = coll.number_input("Antal", value=1, key="fixed")
    fixed_amount = df_selected_fine['fixed_amount'].item() if selected_fine else 0
    coll.metric("Fixed Amount", fixed_amount)

    number_of_fines_variable = col2.number_input("Antal", value=0, key="variable")
    variable_amount = df_selected_fine['variable_amount'].item() if selected_fine else 0
    col2.metric("Varaible Amount", variable_amount)
    
    number_of_holdboxe = col3.number_input("Antal", value=0, key="holdbox")
    holdbox_amount = df_selected_fine['holdbox_amount'] if selected_fine else 0
    col3.metric("Holdboxe", holdbox_amount)
    if st.button("Suggest fine"):
        total_fine_amount = number_of_fines_fixed * fixed_amount + number_of_fines_variable * variable_amount
        recorded_fine = RecordedFine(
            id=None,
            fine_id=df_selected_fine['id'].item(),
            fixed_count=number_of_fines_fixed,
            variable_count=number_of_fines_variable,
            holdbox_count=number_of_holdboxe,
            fined_member_id=df_members.filter(name=selected_member[0])['id'].item(),
            fine_date=date.today(),
            created_by_member_id=st.session_state.current_user_id,
            fine_status=FineStatus.PENDING,
            updated_at=datetime.now(),
            updated_by_member_id=st.session_state.current_user_id,
            total_fine=total_fine_amount,
        )
        try:
            df_recorded_fine = pl.DataFrame([recorded_fine])
            insert_recorded_fines(db_con, df_recorded_fine)
            st.success("Fine suggested")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
        
        
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Bøder", millify(df_fine_overview['total_fine'].sum(), precision=2))
with col2:
    st.metric("Total Holdboxe", millify(df_fine_overview['total_holdboxes'].sum(), precision=2))
with col3:
    st.metric("Bøder Betalt", millify(df_payments['amount'].sum(), precision=2))

if st.button("Tip Bødekassemesteren", type="primary"):
    suggest_fine()

# create_tables(db_con)

st.subheader("Udstedte bøder", divider=True)
show_details = st.toggle("Show Details", False)
extra_cols = fines_overview_detail_cols + [replace_id_with_name("created_by_member_id", "Oprettet af", df_members).alias("Oprettet Af")] if show_details else []
st.dataframe(df_fine_overview.select(fines_overview_show_cols + extra_cols).sort("Bøde Dato", descending=True), use_container_width=True)

df_accepted_fines = df_fine_overview.filter(fine_status="Accepted")

df_fines_leaderboard = df_accepted_fines.group_by('name_member').agg(pl.sum('total_fine').alias('Bødesum'), pl.len().alias("Antal Bøder"),pl.sum('total_holdboxes').alias('Holdbox Sum')).sort('Bødesum', descending=True).select(pl.col("name_member").alias("Navn"), "Bødesum", "Antal Bøder")

df_fines_popularity = df_accepted_fines.group_by('name').agg(pl.sum('total_fine').alias('Bødesum'), pl.len().alias("Antal Bøder"),pl.sum('total_holdboxes').alias('Holdbox Sum')).sort('Bødesum', descending=True).select(pl.col("name").alias("Bøde"), "Bødesum", "Antal Bøder")

df_fines_stikkerlinjen = df_accepted_fines.filter(pl.col("created_by_member_id")!=FINEBOX_ADMIN_MEMBER_ID).group_by('created_by_member_id').agg(pl.sum('total_fine').alias('Bødesum'), pl.len().alias("Antal Bøder"),pl.sum('total_holdboxes').alias('Holdbox Sum')).sort('Bødesum', descending=True)
df_fines_stikkerlinjen = df_fines_stikkerlinjen.join(df_members, left_on="created_by_member_id", right_on="id", how='left', suffix="_member").select(pl.col("name").alias("Navn"), "Bødesum", "Antal Bøder")

st.subheader("Fines Leaderboard", divider=True)

fig = px.bar(df_fines_leaderboard, x='Navn', y='Bødesum', title='Bødesum Leaderboard', color_discrete_sequence=["#560E29"])
st.plotly_chart(fig)

st.dataframe(df_fines_leaderboard,column_config={
        
        "Bødesum": st.column_config.ProgressColumn(
            format="%.0f kr.",
            min_value=0,
            max_value=df_fines_leaderboard["Bødesum"].max(),
        ),
        "Antal Bøder": st.column_config.ProgressColumn(
            format="%.0f",
            min_value=0,
            max_value=df_fines_leaderboard["Antal Bøder"].max(),
        ),
} )

st.subheader("Fines Popularity", divider=True)

fig = px.bar(df_fines_popularity, x='Bøde', y='Bødesum', title='Bødesum Leaderboard', color_discrete_sequence=["#560E29"])
st.plotly_chart(fig)

st.dataframe(df_fines_popularity,column_config={
        
        "Bødesum": st.column_config.ProgressColumn(
            format="%.0f kr.",
            min_value=0,
            max_value=df_fines_popularity["Bødesum"].max(),
        ),
        "Antal Bøder": st.column_config.ProgressColumn(
            format="%.0f",
            min_value=0,
            max_value=df_fines_popularity["Antal Bøder"].max(),
        ),
}    
)


st.subheader("Stikkerlinjen", divider=True)

with st.expander("Bøder til godkendelse"):
    st.dataframe(df_recorded_fines.filter(fine_status="Pending"))

with st.expander("Bøder Afvist"):
    st.dataframe(df_recorded_fines.filter(fine_status="Declined"))


fig = px.bar(df_fines_stikkerlinjen, x='Navn', y='Bødesum', title='Klubbens Bedste Stikkere', color_discrete_sequence=["#560E29"])
st.plotly_chart(fig)

st.dataframe(df_fines_stikkerlinjen,column_config={
        "Bødesum": st.column_config.ProgressColumn(
            format="%.0f kr.",
            min_value=0,
            max_value=df_fines_stikkerlinjen["Bødesum"].max(),
        ),
        "Antal Bøder": st.column_config.ProgressColumn(
            format="%.0f",
            min_value=0,
            max_value=df_fines_stikkerlinjen["Antal Bøder"].max(),
        ),
}    
)

with st.expander("Bøde Oversigt"):
    st.dataframe(df_fines)


    