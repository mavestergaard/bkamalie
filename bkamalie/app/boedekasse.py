import streamlit as st
from bkamalie.holdsport.api import (
    MENS_TEAM_ID,
    FINEBOX_ADMIN_MEMBER_ID,
    get_members,
    get_connection as get_holdsport_connection,
)
import polars as pl
from bkamalie.app.utils import (
    get_fines,
    login,
    render_page_links,
)
from bkamalie.database.utils import get_connection as get_db_connection
import plotly.express as px
from millify import millify


holdsport_con = get_holdsport_connection(
    st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"]
)
members = [
    {"id": member.id, "name": member.name, "role": member.role.to_string()}
    for member in get_members(holdsport_con, 5289)
]
df_members = pl.DataFrame(members)
render_page_links(df_members)


st.title("Bødekassen")

if not st.session_state.logged_in:
    if st.button("Login", type="primary"):
        login()
    st.stop()

db_config = st.secrets["db"]
db_con = get_db_connection(db_config)
with st.spinner("Loading data...", show_time=True):
    df_fines = get_fines(db_con)
    df_recorded_fines = pl.read_database_uri(
        query="SELECT * FROM recorded_fines", uri=db_con
    )
    df_payments = pl.read_database_uri(query="SELECT * FROM payment", uri=db_con)
    holdsport_con = get_holdsport_connection(
        st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"]
    )
    members = [
        {"id": member.id, "name": member.name, "role": member.role.to_string()}
        for member in get_members(holdsport_con, MENS_TEAM_ID)
    ]
    df_members = pl.DataFrame(members)


# df_fines_issued = pl.read_csv('database/fines_issued.csv')
df_fine_overview = df_recorded_fines.join(
    df_fines, left_on="fine_id", right_on="id", how="left"
).join(
    df_members, left_on="fined_member_id", right_on="id", how="left", suffix="_member"
)
df_fine_overview = df_fine_overview.with_columns(
    (
        pl.col("fixed_amount") * pl.col("fixed_count")
        + pl.col("variable_amount") * pl.col("variable_count")
    ).alias("total_fine"),
    (pl.col("holdbox_amount") * pl.col("holdbox_count")).alias("total_holdboxes"),
)


col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Bøder", str(df_fine_overview["total_fine"].sum()) + " DKK")
with col2:
    st.metric(
        "Total Holdboxe",
        df_fine_overview["total_holdboxes"].sum(),
    )
with col3:
    st.metric("Bøder Betalt", millify(df_payments["amount"].sum(), precision=2))


df_accepted_fines = df_fine_overview.filter(fine_status="Accepted")

df_fines_leaderboard = (
    df_accepted_fines.group_by("name_member")
    .agg(
        pl.sum("total_fine").alias("Bødesum"),
        pl.len().alias("Antal Bøder"),
        pl.sum("total_holdboxes").alias("Holdbox Sum"),
    )
    .sort("Bødesum", descending=True)
    .select(pl.col("name_member").alias("Navn"), "Bødesum", "Antal Bøder")
)

df_fines_popularity = (
    df_accepted_fines.group_by("name")
    .agg(
        pl.sum("total_fine").alias("Bødesum"),
        pl.len().alias("Antal Bøder"),
        pl.sum("total_holdboxes").alias("Holdbox Sum"),
    )
    .sort("Bødesum", descending=True)
    .select(pl.col("name").alias("Bøde"), "Bødesum", "Antal Bøder")
)

df_fines_stikkerlinjen = (
    df_accepted_fines.filter(pl.col("created_by_member_id") != FINEBOX_ADMIN_MEMBER_ID)
    .group_by("created_by_member_id")
    .agg(
        pl.sum("total_fine").alias("Bødesum"),
        pl.len().alias("Antal Bøder"),
        pl.sum("total_holdboxes").alias("Holdbox Sum"),
    )
    .sort("Bødesum", descending=True)
)
df_fines_stikkerlinjen = df_fines_stikkerlinjen.join(
    df_members,
    left_on="created_by_member_id",
    right_on="id",
    how="left",
    suffix="_member",
).select(pl.col("name").alias("Navn"), "Bødesum", "Antal Bøder")

st.subheader("Fines Leaderboard", divider=True)

fig = px.bar(
    df_fines_leaderboard,
    x="Navn",
    y="Bødesum",
    title="Bødesum Leaderboard",
    color_discrete_sequence=["#560E29"],
)
st.plotly_chart(fig)

st.dataframe(
    df_fines_leaderboard,
    column_config={
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
    },
)

st.subheader("Fines Popularity", divider=True)

fig = px.bar(
    df_fines_popularity,
    x="Bøde",
    y="Bødesum",
    title="Bødesum Leaderboard",
    color_discrete_sequence=["#560E29"],
)
st.plotly_chart(fig)

st.dataframe(
    df_fines_popularity,
    column_config={
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
    },
)


st.subheader("Stikkerlinjen", divider=True)

with st.expander("Bøder til godkendelse"):
    st.dataframe(df_recorded_fines.filter(fine_status="Pending"))

with st.expander("Bøder Afvist"):
    st.dataframe(df_recorded_fines.filter(fine_status="Declined"))


fig = px.bar(
    df_fines_stikkerlinjen,
    x="Navn",
    y="Bødesum",
    title="Klubbens Bedste Stikkere",
    color_discrete_sequence=["#560E29"],
)
st.plotly_chart(fig)

st.dataframe(
    df_fines_stikkerlinjen,
    column_config={
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
    },
)

with st.expander("Bøde Oversigt"):
    st.dataframe(df_fines)
