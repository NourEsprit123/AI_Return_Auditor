import streamlit as st


def navigate(page):

    st.session_state.page = page
    st.rerun()


def render_sidebar():

    with st.sidebar:

        st.markdown("## 🤖 AI Return")
        st.caption("INTELLIGENT RETURN AUDITOR")

        st.divider()

        pages = [
            ("⌂", "Home"),
            ("＋", "Return Request"),
            ("◈", "AI Analysis"),
            ("✓", "Decision"),
            ("◉", "Human Review"),
        ]

        current = st.session_state.page

        for icon, name in pages:

            if current == name:
                label = f"●  {name}"
            else:
                label = f"{icon}  {name}"

            if st.button(
                label,
                key=f"sidebar_{name}",
                use_container_width=True,
            ):
                navigate(name)

        st.divider()

        st.caption("AI WORKFLOW")

        steps = [
            "Request",
            "Vision",
            "Policy RAG",
            "Decision",
            "Review",
        ]

        for index, step in enumerate(steps, start=1):

            if current == "Return Request" and index == 1:
                status = "●"
            elif current == "AI Analysis" and index in [2, 3]:
                status = "●"
            elif current == "Decision" and index == 4:
                status = "●"
            elif current == "Human Review" and index == 5:
                status = "●"
            else:
                status = "○"

            st.caption(
                f"{status}  0{index}  {step}"
            )

        st.divider()

        st.success("● AI SYSTEM ONLINE")
        st.caption("Vision · RAG · Guardrails")