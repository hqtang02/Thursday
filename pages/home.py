import streamlit as st

st.title("💧 RainWise")
st.markdown("### Smart rainwater planning for your household")

st.write(
    "RainWise turns local rainfall and household water demand into a "
    "practical daily allocation plan."
)

st.markdown(
    """
**What you can do**

- **Check water availability** from local rainfall, roof area, tank capacity,
  and collection efficiency.
- **Allocate water by priority** across garden, lawn, and toilet uses.
- **Improve the plan** with clear recommendations for shortage and overflow.
"""
)

if st.button("Enter RainWise", type="primary"):
    st.switch_page("pages/location.py")

st.caption("INT6181 Applied Programming with Python — Group 6")
