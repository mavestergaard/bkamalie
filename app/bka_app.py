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

boedekasse_admin = st.Page(
    "boedekasse_admin.py",
    title="Bødekassen - Admin",
    icon="👮‍♂️",
)


pg = st.navigation([dashboard_page, boedekasse, boedekasse_admin], position="hidden")
pg.run()
