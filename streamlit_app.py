"""
Market Research Agent - Competitor Analysis (Project 3A)
Simple Streamlit front-end for the n8n multi-agent workflow.

Run:
    pip install -r requirements.txt
    streamlit run streamlit_app.py

The app just POSTs a company name to your n8n webhook and renders the
JSON the workflow returns: { company_name, competitor_profiles, briefing_markdown, generated_at }
"""

import json
import time
from datetime import datetime

import requests
import urllib3
import streamlit as st

st.set_page_config(page_title="Competitor Research Agent", page_icon="🔎", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar - configuration (no secrets are hard-coded; user supplies the URL)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    default_url = "https://workoutagent.app.n8n.cloud/webhook/market-research"
    webhook_url = st.text_input(
        "n8n Webhook URL",
        value=st.session_state.get("webhook_url", default_url),
        help="Production webhook URL for the 'Webhook - Start Research' node "
             "in n8n_market_research_agent.json. Use /webhook-test/... while "
             "testing in the n8n editor, /webhook/... once the workflow is Active.",
    )
    st.session_state["webhook_url"] = webhook_url
    timeout_s = st.slider("Request timeout (seconds)", 30, 300, 120, step=10)

    skip_ssl_verify = st.checkbox(
        "Skip SSL verification (corporate network workaround)",
        value=False,
        help="Turn this on only if you get a 'self signed certificate in "
             "certificate chain' error — that means your corporate network's "
             "SSL inspection proxy isn't trusted by Python. The proper fix is "
             "`python -m pip install pip-system-certs` (then restart this app); "
             "use this checkbox only if that isn't possible on your machine. "
             "Skips certificate validation for this app's requests only.",
    )
    if skip_ssl_verify:
        st.caption("⚠️ Certificate validation is OFF — only use this on a network you trust.")

    st.caption(
        "This UI has no autonomous write actions — it only calls the "
        "workflow and displays what comes back. Nothing is sent, saved, "
        "or published without you clicking a button below."
    )

st.title("🔎 Market Research Agent — Competitor Analysis")
st.caption(
    "Type a company name. The agent discovers its top 3 competitors, gathers "
    "fresh web & news data, extracts pricing/features/positioning/news, and "
    "compiles a structured briefing."
)

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
col1, col2 = st.columns([4, 1])
with col1:
    company_name = st.text_input("Company to research", placeholder="e.g. Notion, Figma, Ramp...")
with col2:
    st.write("")
    st.write("")
    run_clicked = st.button("Run Research", type="primary", use_container_width=True)

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

# ---------------------------------------------------------------------------
# Call the n8n workflow
# ---------------------------------------------------------------------------
if run_clicked:
    if not company_name.strip():
        st.warning("Enter a company name first.")
    else:
        start = time.time()
        with st.spinner(f"Researching {company_name}... this can take 30-90s (3 competitors x 2 searches + 3 LLM calls)."):
            try:
                if skip_ssl_verify:
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                resp = requests.post(
                    webhook_url,
                    json={"company_name": company_name.strip()},
                    timeout=timeout_s,
                    verify=not skip_ssl_verify,
                )
                elapsed = time.time() - start
                if resp.status_code == 200:
                    st.session_state["last_result"] = resp.json()
                    st.session_state["last_elapsed"] = elapsed
                    st.session_state["last_error"] = None
                else:
                    try:
                        err = resp.json().get("error", resp.text)
                    except Exception:
                        err = resp.text
                    st.session_state["last_result"] = None
                    st.session_state["last_error"] = f"({resp.status_code}) {err}"
            except requests.exceptions.RequestException as e:
                st.session_state["last_result"] = None
                st.session_state["last_error"] = (
                    f"Could not reach the n8n webhook at {webhook_url}. "
                    f"Is the workflow Active and n8n running? Details: {e}"
                )

# ---------------------------------------------------------------------------
# Error state
# ---------------------------------------------------------------------------
if st.session_state.get("last_error"):
    st.error(st.session_state["last_error"])

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
result = st.session_state.get("last_result")
if result:
    elapsed = st.session_state.get("last_elapsed")
    st.success(
        f"Briefing generated for **{result.get('company_name', company_name)}**"
        + (f" in {elapsed:.1f}s" if elapsed else "")
    )

    tab_briefing, tab_table, tab_raw = st.tabs(["📄 Briefing", "📊 Comparison table", "🧾 Raw JSON"])

    with tab_briefing:
        st.markdown(result.get("briefing_markdown", "_No briefing text returned._"))
        st.download_button(
            "Download briefing (.md)",
            data=result.get("briefing_markdown", ""),
            file_name=f"{result.get('company_name','company')}_competitor_briefing.md",
            mime="text/markdown",
        )

    with tab_table:
        profiles = result.get("competitor_profiles", [])
        if profiles:
            rows = []
            for p in profiles:
                rows.append({
                    "Competitor": p.get("competitor_name", "?"),
                    "Pricing": p.get("pricing", "-"),
                    "Positioning": p.get("market_positioning", "-"),
                    "Data issue?": "⚠️ yes" if p.get("extraction_error") else "",
                })
            st.dataframe(rows, use_container_width=True)
            for p in profiles:
                with st.expander(f"Details — {p.get('competitor_name', '?')}"):
                    st.write("**Core features:**", p.get("core_features"))
                    st.write("**Recent news:**", p.get("recent_news"))
        else:
            st.info("No structured competitor profiles in the response.")

    with tab_raw:
        st.json(result)
        st.download_button(
            "Download raw JSON",
            data=json.dumps(result, indent=2),
            file_name=f"{result.get('company_name','company')}_research_{datetime.now():%Y%m%d_%H%M}.json",
            mime="application/json",
        )
else:
    st.info("Enter a company above and click **Run Research** to generate a briefing.")
