import streamlit as st

st.set_page_config(page_title="Test UI", page_icon="🔎", layout="centered", initial_sidebar_state="collapsed")

st.title("🔎 Página de prueba")
st.markdown("Esta es una página vacía para aislar problemas de UI.")
st.info("Si aquí aparece la caja fantasma, el problema es global. Si no aparece, es local del Login.")
