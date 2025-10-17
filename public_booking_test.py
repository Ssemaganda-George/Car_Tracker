"""
Simple test to check if public booking URL works
Run this to test the URL parameter handling
"""

import streamlit as st

st.write("## URL Parameter Test")
st.write("Current URL parameters:", st.query_params)

if st.query_params.get("page") == "booking":
    st.success("✅ Public booking page detected!")
else:
    st.info("Regular page - add ?page=booking to URL to test")
    st.code("Example: https://your-app.streamlit.app/?page=booking")
