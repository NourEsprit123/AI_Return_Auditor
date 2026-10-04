import streamlit as st

from views.home import show_home
from views.return_request import show_return_request
from views.ai_analysis import show_ai_analysis
from views.decision import show_decision
from views.human_review import show_human_review


st.set_page_config(
    page_title="AI Return Auditor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


if "page" not in st.session_state:
    st.session_state.page = "Home"

if "claim" not in st.session_state:
    st.session_state.claim = {
        "order_id": "",
        "product": "",
        "category": "",
        "price": "",
        "description": "",
        "image": None,
    }

if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if "decision" not in st.session_state:
    st.session_state.decision = None


PAGES = {
    "Home": show_home,
    "Return Request": show_return_request,
    "AI Analysis": show_ai_analysis,
    "Decision": show_decision,
    "Human Review": show_human_review,
}


PAGES[st.session_state.page]()