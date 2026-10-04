import streamlit as st


def render_header(title, subtitle=None):

    col1, col2 = st.columns(
        [5, 1],
        vertical_alignment="center",
    )

    with col1:

        st.caption("AI RETURN AUDITOR")

        st.markdown(
            f"# {title}"
        )

        if subtitle:
            st.write(subtitle)

    with col2:

        st.success(
            "● ONLINE"
        )