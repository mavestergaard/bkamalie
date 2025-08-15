from typing import Any
from bkamalie.holdsport.api import get_available_teams, verify_user
import streamlit as st
from streamlit_cookies_controller import CookieController
from time import sleep
from streamlit import session_state as ss

controller = CookieController()
sleep(0.5)


def set_session_state_from_cookies(cookies: dict[str, Any]) -> None:
    ss.logged_in = cookies.get("logged_in")
    ss.current_user_id = cookies.get("current_user_id")
    ss.current_user_full_name = cookies.get("current_user_full_name")
    ss.available_teams = cookies.get("available_teams")


def set_cookies(
    logged_in: bool,
    current_user_id: int,
    current_user_full_name: str,
    available_teams: dict[str, int],
) -> dict:
    cookies = CookieController()
    cookies.set("logged_in", logged_in)
    cookies.set("current_user_id", current_user_id)
    cookies.set("current_user_full_name", current_user_full_name)
    cookies.set("available_teams", available_teams)
    return cookies


@st.dialog("Login")
def login() -> None:
    current_cookies = CookieController()
    if current_cookies.get("logged_in"):
        set_session_state_from_cookies(current_cookies)
    else:
        st.info("Please login using your Holdsport credentials")
        username = st.text_input("Email", autocomplete="email")
        password = st.text_input("Password", type="password")
        if st.button("Submit"):
            current_user = verify_user(username, password)
            if current_user:
                available_teams = get_available_teams(username, password)
                available_teams_dict = {team.name: team.id for team in available_teams}
                st.success("Login successful")
                updated_cookies = set_cookies(
                    logged_in=True,
                    current_user_id=current_user.id,
                    current_user_full_name=current_user.full_name,
                    available_teams=available_teams_dict,
                )
                set_session_state_from_cookies(updated_cookies)
            else:
                st.error("Login failed")
            st.rerun()


def logout():
    if st.button("Log out"):
        st.session_state.logged_in = False
        controller.remove("logged_in")
        controller.remove("current_user_id")
        controller.remove("current_user_full_name")
        controller.remove("available_teams")
        st.success("Logged out successfully")
        st.rerun()


login_page = st.Page(login, title="Log in", icon=":material/login:")
logout_page = st.Page(logout, title="Log out", icon=":material/logout:")

dashboard_page = st.Page(
    "dashboard.py",
    title="Holdsport Dashboard",
    icon="⚽",
)

boedekasse = st.Page(
    "boedekasse.py",
    title="Bødekassen",
    icon="💰",
)

stikkerlinjen = st.Page(
    "stikkerlinjen.py",
    title="Stikkerlinjen",
    icon="🕵️‍♂️",
)

boeder = st.Page(
    "boeder.py",
    title="Bøde Oversigt",
    icon="📜",
)

my_fines = st.Page(
    "my_fines.py",
    title="Mine Bøder",
    icon="🏃‍♂️",
)


boedekasse_admin = st.Page(
    "boedekasse_admin.py",
    title="Bødekassen - Admin",
    icon="👮‍♂️",
)

if controller.get("logged_in"):
    set_session_state_from_cookies(controller)
    selected_team = st.sidebar.selectbox(
        "Vælg Hold", list(ss.available_teams.keys()), key="selected_team"
    )
    st.sidebar.write("Logged in as:", ss.current_user_full_name)
    st.sidebar.write("User ID:", ss.current_user_id)
    ss.selected_team_id = ss.available_teams.get(selected_team, None)
    pg = st.navigation(
        {
            "Fines": [stikkerlinjen, my_fines, boedekasse, boeder],
            "Tools": [boedekasse_admin],
            "Holdsport": [dashboard_page],
            "Account": [logout_page],
        }
    )
else:
    pg = st.navigation([login_page])

pg.run()
