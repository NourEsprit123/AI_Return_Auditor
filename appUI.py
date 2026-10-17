import base64
import hashlib
import html
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
BACKEND_URL = os.getenv("AUDIT_BACKEND_URL", "http://127.0.0.1:8000")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/return-claim")
LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "audit_log.json"))
REQUEST_TIMEOUT = 1800
AUDIT_STAGES = (
    ("input", "Claim received", "Checking the provided order details, description, and photo."),
    ("vision", "Photo review", "Comparing the product photo with your description."),
    ("rag", "Policy match", "Finding the return policies that apply to your case."),
    ("decision", "Recommendation", "Checking the evidence and reviewing for policy conflicts."),
)
STAGE_PROGRESS_COPY = {
    "vision": {
        "running": "Comparing your photo with the description you provided.",
        "complete": "Photo review is ready.",
        "failed": "We couldn't complete the photo review.",
    },
    "rag": {
        "running": "Finding return policy information related to your case.",
        "complete": "The matching policy information is ready.",
        "failed": "We couldn't complete the policy check.",
    },
    "decision": {
        "running": "Reviewing the evidence and checking the recommendation for policy conflicts.",
        "complete": "Your request's final review is complete.",
        "failed": "We couldn't complete the final review.",
    },
}

st.set_page_config(
    page_title="Return Auditor",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

.stApp, .stApp p, .stApp label, .stApp button, .stApp input,
.stApp textarea, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
    font-family: 'Manrope', sans-serif;
}
.stApp {
    background:
      radial-gradient(ellipse at 12% 0%, rgba(88, 101, 242, .11), transparent 34%),
      radial-gradient(ellipse at 90% 8%, rgba(20, 184, 166, .10), transparent 30%),
      #F5F7FC;
    color: #17233F;
}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
.block-container { padding: 1.5rem 2rem 4rem; max-width: 1160px; }
h1 { font-weight: 800; letter-spacing: -0.045em; color: #101A34; }
h2, h3 { font-weight: 750; letter-spacing: -0.025em; color: #17233F; }
[data-testid="stMetric"], [data-testid="stForm"], [data-testid="stFileUploader"],
[data-testid="stExpander"], [data-testid="stTabs"] [data-baseweb="tab-list"] {
    border: 1px solid rgba(129, 145, 180, .20);
    border-radius: 16px;
    background: rgba(255, 255, 255, .78);
    box-shadow: 0 12px 35px rgba(30, 47, 87, .055);
}
[data-testid="stMetric"] { padding: 1rem 1.15rem; }
[data-testid="stForm"], [data-testid="stFileUploader"] { padding: 1rem; }
[data-testid="stBaseButton-primary"] {
    border: 0;
    background: linear-gradient(105deg, #5266F2, #7357E8 55%, #168DAB);
    box-shadow: 0 8px 20px rgba(82, 102, 242, .22);
}
[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.06); }
[data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, #5266F2, #18A9A1); }
.brand-mark {
    display: inline-flex; align-items: center; gap: .65rem; margin: .1rem 0 1rem;
    color: #27385F; font-size: .9rem; font-weight: 800; letter-spacing: .09em;
    text-transform: uppercase;
}
.brand-dot {
    width: .7rem; height: .7rem; border-radius: 50%;
    background: #14B8A6; box-shadow: 0 0 16px rgba(20, 184, 166, .8);
}
.hero {
    position: relative; overflow: hidden; padding: clamp(1.6rem, 5vw, 3.5rem);
    border: 1px solid rgba(138, 153, 190, .22); border-radius: 24px;
    background: linear-gradient(125deg, rgba(255,255,255,.95), rgba(239,244,255,.88) 55%, rgba(231,250,248,.82));
    box-shadow: 0 20px 55px rgba(30, 47, 87, .08);
}
.hero h1 { max-width: 760px; font-size: clamp(2.2rem, 5vw, 3.6rem); line-height: 1.05; margin: .35rem 0 1rem; }
.hero-copy { max-width: 650px; color: #5C6883; font-size: 1.08rem; line-height: 1.75; }
.eyebrow { color: #5266D8; font-size: .75rem; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; }
.process-card {
    min-height: 155px; padding: 1.25rem; border: 1px solid rgba(129, 145, 180, .2);
    border-radius: 17px; background: rgba(255, 255, 255, .78);
    box-shadow: 0 12px 35px rgba(30, 47, 87, .05);
}
.process-number {
    display: inline-grid; place-items: center; width: 2rem; height: 2rem; margin-bottom: .9rem;
    border-radius: 10px; color: #5266D8; font-size: .85rem; font-weight: 800;
    background: #EEF0FF;
}
.process-title { font-weight: 800; color: #1A294B; }
.process-copy { color: #68748E; font-size: .9rem; line-height: 1.55; margin-top: .35rem; }
.section-kicker { color: #64718C; font-size: .92rem; line-height: 1.65; }

.banner {
    display: flex; justify-content: space-between; align-items: center;
    gap: 1rem; padding: 1.35rem 1.5rem; margin-bottom: 1rem;
    border-radius: 18px; border: 1px solid var(--bd);
    border-left: 6px solid var(--fg); background: var(--bg);
    box-shadow: 0 12px 32px rgba(30, 47, 87, .06);
}
.banner.approve { --fg: #087E75; --bg: #E9F8F5; --bd: #BCE8DE; }
.banner.review  { --fg: #A65B08; --bg: #FFF6E8; --bd: #F2D7A9; }
.banner.reject  { --fg: #B42336; --bg: #FFF0F1; --bd: #F3C7CB; }
.banner.unknown { --fg: #475467; --bg: #F0F3F8; --bd: #D9DFEA; }
.b-label { font-size: 1.8rem; font-weight: 800; color: var(--fg); letter-spacing: -0.02em; }
.b-meta { display: flex; gap: 1.25rem; flex-wrap: wrap; color: #475467; font-size: .9rem; margin-top: .3rem; }
.b-side { font-weight: 700; color: var(--fg); text-align: right; }

.pill {
    display: inline-block; padding: .2rem .7rem; margin: 0 .4rem .4rem 0;
    border-radius: 999px; font-size: .8rem; font-weight: 600;
    border: 1px solid #DDE2EA; background: rgba(255,255,255,.85); color: #667085;
}
.pill.ok  { color: #0F766E; border-color: #B7DDD6; background: #E6F4F1; }
.pill.bad { color: #B42318; border-color: #F3C2BD; background: #FDECEA; }

.quote {
    border-left: 4px solid #5266F2; background: rgba(255,255,255,.86); border-radius: 0 12px 12px 0;
    padding: .9rem 1.2rem; color: #14213D; line-height: 1.6; max-width: 72ch;
}
.audit-step {
    display: grid; grid-template-columns: 2.5rem 1fr; gap: .8rem;
    align-items: start; padding: .9rem .3rem; border-bottom: 1px solid #EAECF0;
}
.audit-step:last-child { border-bottom: 0; }
.audit-step-icon {
    display: grid; place-items: center; width: 2rem; height: 2rem; border-radius: 10px;
    font-size: .95rem; font-weight: 800; background: #EEF0F5; color: #77829A;
}
.audit-step-title { font-weight: 800; color: #1A294B; }
.audit-step-detail { color: #68748E; font-size: .9rem; margin-top: .15rem; }
.audit-step.done .audit-step-icon { color: #087E75; background: #E2F6F0; }
.audit-step.running .audit-step-icon { color: #5266F2; background: #ECEEFF; box-shadow: 0 0 0 4px rgba(82,102,242,.08); }
.audit-step.failed .audit-step-icon { color: #B42318; background: #FDECEA; }
@media (max-width: 700px) {
    .block-container { padding: 1rem 1rem 3rem; }
    .banner { align-items: flex-start; flex-direction: column; }
    .b-side { text-align: left; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def new_order_id() -> str:
    return f"ORD-{datetime.now():%y%m%d}-{uuid.uuid4().hex[:4].upper()}"


def tone(decision: str) -> str:
    d = (decision or "").upper()
    if "ESCALATE" in d or "HUMAN" in d:
        return "review"
    if "REJECT" in d or "DENY" in d or "DECLINE" in d:
        return "reject"
    if "APPROVE" in d or "REFUND" in d:
        return "approve"
    return "unknown"


def pretty(decision: str) -> str:
    return {
        "APPROVE_REFUND": "Refund approved",
        "APPROVE_RETURN": "Return approved",
        "REJECT": "Request not approved",
        "ESCALATE_HUMAN": "Specialist review",
    }.get((decision or "").upper(), "Update available")


def customer_status(status: str, routed: str) -> str:
    if routed == "human":
        return "Awaiting specialist review"
    if status.upper() == "COMPLETED":
        return "Review complete"
    return "Being reviewed"


def load_history() -> list:
    try:
        return json.loads(LOG_PATH.read_text())
    except (OSError, ValueError):
        return []


def save_history() -> None:
    try:
        LOG_PATH.write_text(json.dumps(st.session_state.history, indent=2, default=str))
    except OSError:
        pass  # Persistence is a convenience, never a blocker.


def get_record(case_id: str):
    return next((r for r in st.session_state.history if r["id"] == case_id), None)


def final_outcome(r: dict) -> str:
    if r.get("review"):
        return "Specialist review complete"
    if r["routed"] == "human":
        return "Specialist review in progress"
    return {
        "approve": "Recommendation ready",
        "reject": "Recommendation ready",
    }.get(tone(r["decision"]), "Update available")


def go(page: str) -> None:
    st.session_state.page = page


# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
ss = st.session_state
ss.setdefault("page", "Home")
ss.setdefault("claim", {})
ss.setdefault("pipeline_result", None)  # kept for compatibility with the old app
ss.setdefault("history", load_history())
ss.setdefault("images", {})
ss.setdefault("active_id", None)
ss.setdefault("uploader_n", 0)
ss.setdefault("last_error", None)
ss.setdefault("last_run_sig", None)
ss.setdefault("f_order", new_order_id())
ss.setdefault("f_product", "")
ss.setdefault("f_value", 0.0)
ss.setdefault("f_desc", "")
ss.setdefault("s_threshold", 500.0)

# Streamlit drops widget state when a widget isn't rendered on a page. Re-assigning
# the values keeps the form and settings intact while you move between pages.
for _key in ("f_order", "f_product", "f_value", "f_desc", "s_threshold"):
    ss[_key] = ss[_key]


# ----------------------------------------------------------------------------
# Audit pipeline (API call, retry, routing)
# ----------------------------------------------------------------------------
class AuditError(Exception):
    pass


def render_audit_progress(container, progress_bar, states: dict, current_message: str) -> None:
    completed = sum(state["state"] == "complete" for state in states.values())
    active = next(
        (state for state in states.values() if state["state"] == "running"),
        None,
    )
    progress_bar.progress(
        completed / len(AUDIT_STAGES),
        text=active["message"] if active else current_message,
    )

    icons = {"pending": "○", "running": "●", "complete": "✓", "failed": "×"}
    step_html = []
    for stage_id, title, detail in AUDIT_STAGES:
        stage = states[stage_id]
        message = stage["message"] or detail
        step_html.append(
            f'<div class="audit-step {stage["state"]}">'
            f'<div class="audit-step-icon">{icons[stage["state"]]}</div>'
            f'<div><div class="audit-step-title">{esc(title)}</div>'
            f'<div class="audit-step-detail">{esc(message)}</div></div></div>'
        )
    container.markdown("".join(step_html), unsafe_allow_html=True)


def call_audit_api(snapshot: dict, request_id: str, on_progress=None) -> dict:
    payload = {
        "request_id": request_id,
        "order_id": snapshot["order_id"],
        "product_name": snapshot["product_name"],
        "item_value": snapshot["item_value"],
        "user_description": snapshot["user_statement"],
        "image_base64": base64.b64encode(snapshot["image_bytes"]).decode("ascii"),
    }

    def submit_claim() -> dict:
        try:
            response = requests.post(
                N8N_WEBHOOK_URL,
                json=payload,
                timeout=(10, REQUEST_TIMEOUT),
            )
        except requests.RequestException as exc:
            raise AuditError(f"Could not reach the n8n workflow at {N8N_WEBHOOK_URL}: {exc}") from exc
        try:
            result = response.json()
        except ValueError as exc:
            raise AuditError(
                f"The n8n workflow returned a non-JSON response ({response.status_code}): {response.text}"
            ) from exc
        if response.status_code >= 400:
            detail = result.get("detail", result.get("message", result)) if isinstance(result, dict) else result
            if response.status_code == 404 and "webhook" in str(detail).lower():
                raise AuditError(
                    "n8n did not register the return-claim webhook. For normal use, activate "
                    "the imported workflow and keep N8N_WEBHOOK_URL set to "
                    "http://127.0.0.1:5678/webhook/return-claim. For a temporary editor test, "
                    "click 'Listen for test event' in n8n and set N8N_WEBHOOK_URL to "
                    "http://127.0.0.1:5678/webhook-test/return-claim, then submit the request "
                    "while n8n is listening."
                )
            if response.status_code == 500 and str(detail).strip().lower() == "error in workflow":
                raise AuditError(
                    "n8n failed while running the workflow. Open the latest execution in n8n "
                    "to see which node failed. If n8n is running in Docker Desktop, re-import "
                    "the updated n8n/workflow.json so its backend URLs use "
                    "host.docker.internal:8000 instead of 127.0.0.1:8000."
                )
            raise AuditError(f"The n8n workflow returned {response.status_code}: {detail}")
        if not isinstance(result, dict) or not isinstance(result.get("pipeline_trace"), dict):
            raise AuditError("The n8n workflow completed without a valid pipeline result.")
        return result

    progress_warning_shown = False
    with ThreadPoolExecutor(max_workers=1) as executor:
        submission = executor.submit(submit_claim)
        while not submission.done():
            try:
                response = requests.get(
                    f"{BACKEND_URL.rstrip('/')}/api/audit-progress/{request_id}",
                    timeout=2,
                )
                response.raise_for_status()
                stages = response.json().get("stages", {})
            except (requests.RequestException, ValueError):
                if not progress_warning_shown and on_progress:
                    on_progress(
                        {
                            "stage": "vision",
                            "state": "pending",
                            "message": "The workflow is running; live stage updates are temporarily unavailable.",
                        }
                    )
                    progress_warning_shown = True
            else:
                for stage_id, stage in stages.items():
                    if on_progress:
                        on_progress(
                            {
                                "stage": stage_id,
                                "state": stage.get("state", "pending"),
                                "message": stage.get("message", ""),
                            }
                        )
            time.sleep(0.4)

        result = submission.result()

    for stage_id, message in (
        ("vision", "Visual observations are ready for policy matching."),
        ("rag", "Policy passages have been retrieved."),
        ("decision", "The final decision is ready."),
    ):
        if on_progress:
            on_progress({"stage": stage_id, "state": "complete", "message": message})
    return result


def build_record(snapshot: dict, result: dict) -> dict:
    trace = result.get("pipeline_trace", {})
    out = trace.get("decision_output", {})
    decision = out.get("decision", "UNKNOWN")
    confidence = out.get("confidence") or 0.0
    if confidence > 1:
        confidence = confidence / 100

    routed, reason = "auto", "Resolved automatically."
    if tone(decision) == "review":
        routed, reason = "human", "The model asked for human review."
    elif tone(decision) == "approve" and snapshot["item_value"] >= ss.s_threshold:
        routed = "human"
        reason = f"Refund of ${snapshot['item_value']:,.2f} is above the ${ss.s_threshold:,.0f} auto-approval limit."

    return {
        "id": uuid.uuid4().hex[:8],
        "created": datetime.now().isoformat(timespec="seconds"),
        "order_id": snapshot["order_id"],
        "product_name": snapshot["product_name"],
        "item_value": snapshot["item_value"],
        "user_statement": snapshot["user_statement"],
        "decision": decision,
        "confidence": float(confidence),
        "status": out.get("status", result.get("status", "UNKNOWN")),
        "reasoning": out.get("reasoning_summary"),
        "customer_message": out.get("customer_message"),
        "routed": routed,
        "route_reason": reason,
        "review": None,
        "trace": result,
    }


def run_audit(signature: str) -> None:
    upload = ss.get(f"f_image_{ss.uploader_n}")
    if upload is None:
        ss.last_error = "Please upload a product photo before starting the audit."
        return

    ss.last_run_sig = signature
    ss.last_error = None
    snapshot = {
        "order_id": ss.f_order.strip(),
        "product_name": ss.f_product.strip(),
        "item_value": float(ss.f_value),
        "user_statement": ss.f_desc.strip(),
        "image_name": upload.name,
        "image_bytes": upload.getvalue(),
        "image_type": upload.type,
    }

    states = {
        stage_id: {"state": "pending", "message": ""}
        for stage_id, _, _ in AUDIT_STAGES
    }
    states["input"] = {
        "state": "complete",
        "message": "The claim details and uploaded photo are ready.",
    }

    with st.status("Reviewing your return claim", expanded=True) as status:
        progress_bar = st.progress(0.25, text="Preparing the claim for review.")
        timeline = st.empty()
        render_audit_progress(
            timeline,
            progress_bar,
            states,
            "Preparing the claim for review.",
        )

        def update_progress(event: dict) -> None:
            stage_id = event.get("stage")
            if stage_id not in states:
                return
            stage_state = str(event.get("state") or "running")
            states[stage_id] = {
                "state": stage_state,
                "message": STAGE_PROGRESS_COPY.get(stage_id, {}).get(
                    stage_state,
                    str(event.get("message") or ""),
                ),
            }
            render_audit_progress(
                timeline,
                progress_bar,
                states,
                event.get("message", "Processing claim."),
            )

        try:
            result = call_audit_api(
                snapshot,
                uuid.uuid4().hex,
                on_progress=update_progress,
            )
        except AuditError as exc:
            for stage in states.values():
                if stage["state"] == "running":
                    stage["state"] = "failed"
                    stage["message"] = str(exc)
                    break
            render_audit_progress(timeline, progress_bar, states, str(exc))
            status.update(label="Audit failed", state="error")
            ss.last_error = str(exc)
            st.error(f"The audit could not be completed: {exc}")
            return
        record = build_record(snapshot, result)
        ss.history.insert(0, record)
        ss.images[record["id"]] = snapshot["image_bytes"]
        save_history()
        status.update(label="Audit complete", state="complete")

    # Keep old keys populated so any downstream code that reads them still works.
    ss.claim = {k: snapshot[k] for k in ("order_id", "product_name", "item_value", "user_statement")}
    ss.claim["image_file"] = snapshot["image_bytes"]
    ss.pipeline_result = result
    ss.active_id = record["id"]
    ss.page = "AI Analysis"
    st.rerun()


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
def render_top_navigation() -> None:
    st.markdown(
        '<div class="brand-mark"><span class="brand-dot"></span> Return care</div>',
        unsafe_allow_html=True,
    )
    labels = [
        ("Home", "How it works"),
        ("Return Request", "Start a return"),
        ("AI Analysis", "Your update"),
    ]
    columns = st.columns(3)
    for column, (page, label) in zip(columns, labels):
        column.button(
            label,
            key=f"top_nav_{page}",
            type="primary" if ss.page == page else "secondary",
            on_click=go,
            args=(page,),
            use_container_width=True,
        )
    st.divider()


# ----------------------------------------------------------------------------
# Shared components
# ----------------------------------------------------------------------------
def banner(r: dict) -> None:
    t = tone(r["decision"])
    st.markdown(
        f"""
        <div class="banner {t}">
          <div>
            <div class="b-label">{esc(pretty(r["decision"]))}</div>
            <div class="b-meta">
              <span>{esc(r["order_id"])}</span>
              <span>{esc(r["product_name"] or "Unnamed product")}</span>
              <span>${r["item_value"]:,.2f}</span>
            </div>
          </div>
          <div class="b-side">{esc(final_outcome(r))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# View: Home
# ----------------------------------------------------------------------------
def show_home() -> None:
    st.markdown(
        """
        <section class="hero">
          <div class="eyebrow">A clearer way to resolve returns</div>
          <h1>Your return, reviewed with care.</h1>
          <div class="hero-copy">
            Share what happened and a photo of your item. We’ll check the details
            against the return policy and keep you updated at every step.
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    st.button("Start a return", type="primary", on_click=go, args=("Return Request",))
    st.write("")
    st.subheader("What happens next")
    st.markdown(
        '<div class="section-kicker">A transparent review from your first photo to a clear next step.</div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(3, gap="medium")
    process = (
        ("01", "We review your photo", "Your image is compared with the details you share about the item."),
        ("02", "We check the policy", "The relevant return information is matched to your situation."),
        ("03", "You get a clear update", "We provide a recommendation—or let you know if a specialist needs to review it."),
    )
    for column, (number, title, detail) in zip(columns, process):
        column.markdown(
            f'<div class="process-card"><div class="process-number">{number}</div>'
            f'<div class="process-title">{esc(title)}</div>'
            f'<div class="process-copy">{esc(detail)}</div></div>',
            unsafe_allow_html=True,
        )


# ----------------------------------------------------------------------------
# View: Return request
# ----------------------------------------------------------------------------
def reset_form() -> None:
    ss.f_order = new_order_id()
    ss.f_product = ""
    ss.f_value = 0.0
    ss.f_desc = ""
    ss.uploader_n += 1
    ss.last_error = None
    ss.last_run_sig = None


def start_another_audit() -> None:
    reset_form()
    go("Return Request")


def show_return_request() -> None:
    st.title("Tell us about your return")
    st.markdown(
        '<div class="section-kicker">Add your order details, describe what went wrong, and upload a clear photo. '
        'We’ll show you each step as your request is reviewed.</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 2], gap="large")
    with left:
        c1, c2 = st.columns(2)
        c1.text_input("Order number", key="f_order")
        c2.text_input("Item name", key="f_product")
        st.number_input("Item price ($)", min_value=0.0, step=1.0, format="%.2f", key="f_value")
        st.text_area(
            "What happened to the item?",
            key="f_desc",
            height=140,
            placeholder="Share when you noticed the issue and describe what is wrong.",
        )
    with right:
        upload = st.file_uploader(
            "Add a photo of the item",
            type=["png", "jpg", "jpeg"],
            key=f"f_image_{ss.uploader_n}",
        )
        if upload is not None:
            st.image(upload, caption="Your uploaded photo", width=300)

    has_order = bool(ss.f_order.strip())
    has_desc = bool(ss.f_desc.strip())
    has_photo = upload is not None
    ready = has_order and has_desc and has_photo

    st.markdown(
        "".join(
            f'<span class="pill {"ok" if ok else ""}">{label} {"ready" if ok else "still needed"}</span>'
            for label, ok in (("Order number", has_order), ("Description", has_desc), ("Photo", has_photo))
        ),
        unsafe_allow_html=True,
    )

    if ss.last_error:
        st.error(ss.last_error)

    signature = ""
    if ready:
        if upload is None:
            st.error("Please upload a product photo before starting the audit.")
            return
        signature = hashlib.md5(
            f"{ss.f_order}|{ss.f_product}|{ss.f_value}|{ss.f_desc}|{upload.name}|{upload.size}".encode()
        ).hexdigest()

    clicked = st.button("Submit return request", type="primary", disabled=not ready)
    if ready and clicked:
        run_audit(signature)


# ----------------------------------------------------------------------------
# View: AI analysis
# ----------------------------------------------------------------------------
def show_ai_analysis() -> None:
    st.title("Your return update")
    if not ss.active_id:
        st.info("Your update will appear here after you submit a return request.")
        st.button("Start a return", type="primary", on_click=go, args=("Return Request",))
        return

    r = get_record(ss.active_id)
    if r is None:
        st.error("This return update is no longer available in this session.")
        return
    trace = r["trace"].get("pipeline_trace", {})
    vision = trace.get("vision_agent", {})
    rag_result = trace.get("rag_agent", {})
    policies = (
        rag_result.get("applicable_policy", rag_result.get("chunks", []))
        if isinstance(rag_result, dict)
        else rag_result
    )
    if not isinstance(policies, list):
        policies = []

    banner(r)
    if r["routed"] == "human" and not r.get("review"):
        st.warning("Your request needs an additional specialist review. We’ll share an update when it’s complete.")
    elif r["routed"] == "human" and r.get("review"):
        note = r["review"].get("note")
        st.info(f"Your request was reviewed on {r['review']['at'].replace('T', ' ')}." + (f" Note: {note}" if note else ""))

    m1, m2, m3 = st.columns(3)
    m1.metric("Assessment confidence", f'{r["confidence"] * 100:.1f}%')
    m2.metric("Request status", customer_status(r["status"], r["routed"]))
    m3.metric("Item value", f'${r["item_value"]:,.2f}')
    st.progress(min(max(r["confidence"], 0.0), 1.0))
    st.caption("Confidence describes how consistently the evidence supported this recommendation; it is not a guarantee.")

    st.subheader("Message for the customer")
    st.markdown(f'<div class="quote">{esc(r["customer_message"] or "No message was returned.")}</div>', unsafe_allow_html=True)

    with st.expander("How we reviewed your request", expanded=True):
        st.markdown("**1. Photo review**")
        st.write(
            f"{vision.get('visual_evidence') or 'Your photo was reviewed alongside your description.'} "
            f"Your description and photo: {vision.get('description_consistency', 'compared')}."
        )
        st.markdown("**2. Return policy check**")
        if policies:
            st.write(
                f"We found {len(policies)} relevant policy passage(s). "
                "You can review the matching information in the Policy check section below."
            )
        else:
            st.write("No matching policy information was returned for this request.")
        st.markdown("**3. Recommendation**")
        st.write(
            r["reasoning"]
            or "Your request was reviewed using the photo, description, and available policy information."
        )

    st.write("")
    tab1, tab2, tab3 = st.tabs(["Photo & findings", "Policy check", "Recommendation details"])

    with tab1:
        img_col, findings_col = st.columns([1, 1.5])
        with img_col:
            image = ss.images.get(r["id"])
            if image:
                st.image(image, caption="Your photo", use_container_width=True)
            else:
                st.caption("The photo preview is no longer available in this session.")
        with findings_col:
            st.markdown("**What we observed**")
            st.write(vision.get("visual_evidence") or "No visual summary was returned.")
            st.markdown("**How it compares with your description**")
            st.write(vision.get("description_consistency") or "No comparison summary was returned.")
            if vision.get("uncertainty"):
                st.info(f"Something to note: {vision['uncertainty']}")

    with tab2:
        if policies:
            for p in policies:
                with st.container(border=True):
                    title = p.get("title") or p.get("policy_id") or "Relevant return information"
                    st.markdown(f"**{esc(title)}**")
                    st.write(p.get("rule") or p.get("text") or "Policy details were not included.")
        else:
            st.write("No matching policy information was returned.")

    with tab3:
        st.write(r["reasoning"] or "Your request was assessed using the details and policy information shown above.")
        st.markdown("**What you told us**")
        st.write(r["user_statement"])

    st.button("Submit another return", type="primary", on_click=start_another_audit)


# ----------------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------------
render_top_navigation()

PAGES = {
    "Home": show_home,
    "Return Request": show_return_request,
    "AI Analysis": show_ai_analysis,
}
PAGES.get(ss.page, show_home)()