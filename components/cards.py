import streamlit as st


def render_feature_card(
    icon,
    label,
    title,
    description
):

    with st.container(border=True):

        st.markdown(
            f"## {icon}"
        )

        st.caption(
            label
        )

        st.markdown(
            f"### {title}"
        )

        st.write(
            description
        )


def render_metric_card(
    label,
    value,
    color_class="metric-purple"
):

    with st.container(border=True):

        st.caption(
            label
        )

        st.markdown(
            f"# {value}"
        )


def render_agent_card(
    icon,
    name,
    description,
    status="READY",
    status_class="status-processing"
):

    with st.container(border=True):

        col1, col2 = st.columns(
            [1, 4]
        )

        with col1:

            st.markdown(
                f"## {icon}"
            )

        with col2:

            st.markdown(
                f"### {name}"
            )

            st.caption(
                description
            )

            if status == "READY":

                st.success(
                    "READY"
                )

            elif status == "PROCESSING":

                st.info(
                    "PROCESSING"
                )

            elif status == "COMPLETED":

                st.success(
                    "COMPLETED"
                )

            else:

                st.warning(
                    status
                )


def render_result_card(
    approved,
    confidence,
    title=None,
    description=None
):

    if approved:

        title = (
            title
            or "Return Approved"
        )

        description = (
            description
            or "Your return request "
               "meets the verification criteria."
        )

        st.success(
            f"### ✓ {title}\n\n"
            f"{description}"
        )

    else:

        title = (
            title
            or "Human Review Required"
        )

        description = (
            description
            or "The claim requires "
               "additional verification."
        )

        st.warning(
            f"### ⚠️ {title}\n\n"
            f"{description}"
        )

    st.metric(
        "AI CONFIDENCE",
        f"{confidence * 100:.0f}%"
    )