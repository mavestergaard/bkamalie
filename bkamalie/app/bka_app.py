from bkamalie.holdsport.api import verify_user
import streamlit as st
from streamlit_cookies_controller import CookieController
from time import sleep

controller = CookieController()
sleep(1)
login_status = controller.get("logged_in")

if login_status:
    st.session_state.logged_in = True
else:
    st.session_state.logged_in = False


@st.dialog("Login")
def login() -> None:
    if login_status:
        st.session_state.logged_in = True
        st.session_state.current_user_id = controller.get("current_user_id")
        st.session_state.current_user_full_name = controller.get(
            "current_user_full_name"
        )
    else:
        st.info("Please login using your Holdsport credentials")
        username = st.text_input("Email", autocomplete="email")
        password = st.text_input("Password", type="password")
        if st.button("Submit"):
            current_user = verify_user(username, password)
            if current_user:
                st.success("Login successful")
                st.session_state.logged_in = True
                st.session_state.current_user_id = current_user.id
                st.session_state.current_user_full_name = current_user.full_name
                controller.set("current_user_id", current_user.id)
                controller.set("current_user_full_name", current_user.full_name)
                controller.set("logged_in", True)
            else:
                st.error("Login failed")

            st.rerun()


def logout():
    if st.button("Log out"):
        st.session_state.logged_in = False
        controller.remove("logged_in")
        controller.remove("current_user_id")
        controller.remove("current_user_full_name")
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

if st.session_state.logged_in:
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
