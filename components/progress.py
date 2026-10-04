import streamlit as st


def render_progress(
    value,
    text="Processing..."
):
    """
    Affiche une barre de progression personnalisée.
    """

    value = max(
        0,
        min(100, value)
    )

    st.markdown(
        f"""
        <div style="
            margin-top:15px;
            margin-bottom:10px;
        ">

            <div style="
                display:flex;
                justify-content:space-between;
                align-items:center;
                margin-bottom:7px;
            ">

                <span style="
                    color:#94a3b8;
                    font-size:12px;
                ">
                    {text}
                </span>

                <span style="
                    color:#67e8f9;
                    font-size:12px;
                    font-weight:700;
                ">
                    {value}%
                </span>

            </div>

            <div class="progress-container">

                <div
                    class="progress-bar"
                    style="width:{value}%;">
                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


def render_agent_progress(
    agent_name,
    value
):
    """
    Affiche la progression d'un agent.
    """

    render_progress(
        value,
        f"Running {agent_name}"
    )