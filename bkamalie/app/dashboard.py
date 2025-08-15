import streamlit as st
from bkamalie.holdsport.api import (
    get_current_week_activities,
    get_members,
    PlayerStatus,
    get_connection as get_holdsport_connection,
)

import polars as pl
from streamlit import session_state as ss


st.logo("bkamalie/graphics/bka_logo.png")


holdsport_con = get_holdsport_connection(
    st.secrets["holdsport"]["username"], st.secrets["holdsport"]["password"]
)
members = [
    {"id": member.id, "name": member.name, "role": member.role.to_string()}
    for member in get_members(holdsport_con, ss.selected_team_id)
]
df_members = pl.DataFrame(members)

st.header("BK Amalie Dashboard", divider=True)

current_week_activities = get_current_week_activities(
    holdsport_con, ss.selected_team_id
)

for activity in current_week_activities:
    default_location = (
        "Ingen lokation angivet" if not activity.location else activity.location
    )
    with st.expander(
        f"{activity.name} - {activity.date_of_activity.strftime('%Y-%m-%d')} - {default_location} - {activity.team_level}",
        expanded=True,
    ):
        # st.write(activity.description)
        # st.image(activity.image_url, use_column_width=True)
        cols = st.columns(3)
        df_players = pl.DataFrame(activity.players)
        for col_i, player_status in enumerate(PlayerStatus):
            match player_status:
                case PlayerStatus.ATTENDING:
                    divider_color = "green"
                case PlayerStatus.NOT_ATTENDING:
                    divider_color = "red"
                case PlayerStatus.UNKNOWN:
                    divider_color = "orange"
            with cols[col_i].expander(player_status, expanded=False):
                # cols[col_i].subheader(player_status, divider=divider_color)
                players_filtered = df_players.filter(status=player_status).to_dicts()
                for player in players_filtered:
                    st.write(player["name"])
