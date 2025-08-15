from datetime import date, datetime
from typing import Any
from bkamalie.database.execute import insert_recorded_fines
from bkamalie.database.model import FineStatus, RecordedFine
import polars as pl
import streamlit as st
from bkamalie.holdsport.api import verify_user
from streamlit_cookies_controller import CookieController
import os

fines_overview_show_cols = [
    pl.col("id"),
    pl.col("name_member").alias("Navn"),
    pl.col("name").alias("Bøde"),
    pl.col("total_fine").alias("Bøde Total"),
    pl.col("total_holdboxes").alias("Holdbox Total"),
    pl.col("fine_status").alias("Bøde Status"),
    pl.col("fine_date").alias("Bøde Dato"),
]

fines_overview_detail_cols = [
    pl.col("fixed_amount").alias("Bødetakst"),
    pl.col("fixed_count").alias("Antal"),
    pl.col("variable_amount").alias("Variable Bødetakst"),
    pl.col("variable_count").alias("Variabelt Antal"),
    pl.col("holdbox_amount").alias("Holdboxe"),
    pl.col("holdbox_count").alias("Holdboxe Antal"),
]


def render_page_links() -> None:
    """Call this as the first function in every app script"""
    headers = st.context.headers
    controller = CookieController()
    login_status = controller.get("logged_in")
    if "localhost" in headers.get("Host"):
        st.session_state.logged_in = True
        st.session_state.current_user_id = 1412409
        st.session_state.current_user_full_name = "Mikkel Vestergaard"
    st.image("bkamalie/graphics/bka_logo.png")
    col1, col2, col3 = st.columns(3)
    col1.page_link("stikkerlinjen.py", label="Stikkerlinjen", icon="🕵️‍♂️")
    col2.page_link("my_fines.py", label="Mine Bøder", icon="🧾")
    col3.page_link(
        "boedekasse.py",
        label="Bødekasse",
        icon="💰",
    )
    col1.page_link("boeder.py", label="Bøder", icon="📜")
    col2.page_link(
        "boedekasse_admin.py", label="Admin", icon="👮‍♂️", use_container_width=True
    )
    col3.page_link("dashboard.py", label="Holdsport", icon="⚽")
    if ("logged_in" not in st.session_state) & (login_status is None):
        st.warning("Please login to proceed")
        st.session_state.logged_in = False
        st.session_state.current_user_id = None
        st.session_state.current_user_full_name = None
    else:
        if login_status:
            st.session_state.logged_in = True
            st.session_state.current_user_id = controller.get("current_user_id")
            st.session_state.current_user_full_name = controller.get(
                "current_user_full_name"
            )
        if st.session_state.logged_in:
            st.info(
                f"Logged in as: {st.session_state.current_user_full_name} ({st.session_state.current_user_id})"
            )
        else:
            st.warning(
                "Please login to proceed. Use your Holdsport credentials when signing in."
            )


@st.dialog("Login")
def login() -> None:
    st.info("Please login using your Holdsport credentials")
    username = st.text_input("Email", autocomplete="email")
    password = st.text_input("Password", type="password")
    controller = CookieController()
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


def replace_id_with_name(
    col_name: str, alias: str, df_members: pl.DataFrame
) -> pl.Expr:
    return (
        pl.col(col_name)
        .replace_strict(old=df_members["id"], new=df_members["name"])
        .alias(alias)
    )


@st.cache_data(ttl=300)
def get_fines(db_con: str, team_id: int = None) -> pl.DataFrame:
    return pl.read_database_uri(
        query=f"SELECT * FROM fine where team_id = {team_id}", uri=db_con
    )


def _suggest_fines(
    db_con: str,
    members: list[str],
    selected_fine: str,
    df_fines: pl.DataFrame,
    count_fixed: int,
    count_variable: int,
    count_holdbox: int,
    df_members: pl.DataFrame,
    suggested_by_user_id: int,
    comment: str,
    team_id: int,
) -> None:
    df_selected_fine = df_fines.filter(name=selected_fine[0])
    fine_id = df_selected_fine["id"][0]
    fixed_amount = df_selected_fine["fixed_amount"][0]
    variable_amount = df_selected_fine["variable_amount"][0]
    total_fine_amount = count_fixed * fixed_amount + count_variable * variable_amount
    member_ids = [df_members.filter(name=member)["id"][0] for member in members]
    updated_at = datetime.now()
    df_recorded_fines = pl.DataFrame(
        [
            RecordedFine(
                id=None,
                fine_id=fine_id,
                fixed_count=count_fixed,
                variable_count=count_variable,
                holdbox_count=count_holdbox,
                fined_member_id=member_id,
                fine_date=date.today(),
                created_by_member_id=suggested_by_user_id,
                fine_status=FineStatus.PENDING,
                updated_at=updated_at,
                updated_by_member_id=suggested_by_user_id,
                total_fine=total_fine_amount,
                comment=comment,
                team_id=team_id,
            )
            for member_id in member_ids
        ]
    )
    try:
        insert_recorded_fines(db_con, df_recorded_fines)
    except Exception as e:
        raise e


def get_secret(secret_name: str) -> Any:
    """Tries to get a secret from either .streamlit/secrets.toml or environment variables."""
    st_secret_type, st_secret_name = secret_name.split("_")
    try:
        return st.secrets[st_secret_type][st_secret_name]
    except KeyError:
        return os.getenv(secret_name, None)
