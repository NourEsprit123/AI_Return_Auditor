import streamlit as st


def render_navbar():

    col1, col2, col3 = st.columns(
        [3.5, 3, 1.5]
    )

    with col1:

        st.markdown(
            "### 🤖 AI Return Auditor"
        )

        st.caption(
            "INTELLIGENT RETURN VERIFICATION"
        )

    with col2:

        st.caption(
            "VISION  •  RAG  •  GUARDRAILS"
        )

    with col3:

        st.success(
            "● SYSTEM ONLINE"
        )


def render_navigation():

    pages = [
        ("⌂", "Home"),
        ("▣", "Return Request"),
        ("◈", "AI Analysis"),
        ("✓", "Decision"),
        ("◉", "Human Review"),
    ]

    current_page = st.session_state.get(
        "page",
        "Home"
    )

    cols = st.columns(5)

    for col, (icon, page_name) in zip(
        cols,
        pages
    ):

        with col:

            if current_page == page_name:

                label = f"● {page_name}"

            else:

                label = f"{icon} {page_name}"

            if st.button(
                label,
                key=f"nav_{page_name}",
                use_container_width=True
            ):

                st.session_state.page = page_name
                st.rerun()