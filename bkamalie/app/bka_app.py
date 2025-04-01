import streamlit as st

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


boedekasse_admin = st.Page(
    "boedekasse_admin.py",
    title="Bødekassen - Admin",
    icon="👮‍♂️",
)


pg = st.navigation(
    [stikkerlinjen, boedekasse, boeder, boedekasse_admin, dashboard_page],
    position="hidden",
)
pg.run()
