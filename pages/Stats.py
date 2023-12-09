import streamlit as st


clean = st.session_state['clean']
st.dataframe(clean)
