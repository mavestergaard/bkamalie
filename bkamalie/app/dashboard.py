from bkamalie.app.utils import login, render_page_links
import streamlit as st
from bkamalie.holdsport.api import get_current_week_activities, get_teams, PlayerStatus, get_connection

from datetime import date
import polars as pl

render_page_links()

if st.button("Login", type="primary"):
    login()

st.title("BK Amalie Dashboard")

if not st.session_state.logged_in:
    st.stop()



holdsport_con = get_connection(st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"])
current_week_activities = get_current_week_activities(holdsport_con, 5289)

cols = st.columns(len(current_week_activities), gap="small", vertical_alignment="top", border=True)

for col_i, activity in enumerate(current_week_activities):
    col1, col2, col3, col4 = cols[col_i].columns(4)
    col1.metric("Type",activity.name, border=True)
    col2.metric("Date",str(activity.date_of_activity), border=True)
    col3.metric("Location",activity.location, border=True)
    col4.metric("Team",activity.team_level, border=True)
    df_players = pl.DataFrame(activity.players)
    for player_status in PlayerStatus:
        match player_status:
            case PlayerStatus.ATTENDING:
                divider_color = "green"
            case PlayerStatus.NOT_ATTENDING:
                divider_color = "red"
            case PlayerStatus.UNKNOWN:
                divider_color = "orange"
        cols[col_i].subheader(player_status, divider=divider_color)
        cols[col_i].dataframe(df_players.filter(status=player_status))
    


