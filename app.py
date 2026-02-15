"""
╔══════════════════════════════════════════════════╗
║  CRYPTIX SAR  –  AML Intelligence Platform       ║
║  LLM : Groq · Llama 3.3 70B                      ║
║  Data: Mockaroo API  (fallback: local generator)  ║
║  DB  : SQLite (swap → PostgreSQL in prod)         ║
╚══════════════════════════════════════════════════╝
"""
import os
import json
import html
import random
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

from database import (
    init_db, insert_customer, get_customer,
    insert_transactions, get_transactions,
    create_sar, update_sar, get_sar, list_sars,
    log_audit, get_audit_trail, get_dashboard_stats,
)
from risk_engine import (
    compute_risk, generate_sar_narrative,
    fetch_mockaroo_customers, fetch_mockaroo_transactions,
    REPORTING_THRESHOLD, RISK_LABELS, get_risk_label,
    GROQ_MODEL,
)

# ── Bootstrap DB ─────────────────────────────────────────────────────
init_db()

# ── Page Config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="CRYPTIX SAR Platform",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@400;500;600;700&display=swap');

:root{
  --bg:#0a0f1e; --bg2:#111827; --bg3:#1a2235;
  --teal:#00c9b1; --purple:#7c6ff7; --orange:#f59e0b;
  --red:#ef4444; --green:#22c55e;
  --text:#e2e8f0; --muted:#64748b; --border:rgba(0,201,177,0.15);
}
            /* Completely remove Streamlit header */
header[data-testid="stHeader"] {
    display: none;
    height: 0px;
}

/* Remove toolbar (Deploy + three dots) */
div[data-testid="stToolbar"] {
    display: none;
}

/* Remove main menu */
#MainMenu {
    visibility: hidden;
}

/* Remove extra top spacing */
.block-container {
    padding-top: 0rem !important;
}

.stApp{background:var(--bg)!important;color:var(--text)!important;font-family:'Inter',sans-serif;}
.block-container{padding-top:1rem!important;max-width:1400px!important;}
[data-testid="stSidebar"],[data-testid="stSidebarContent"]{background:var(--bg2)!important;border-right:1px solid var(--border)!important;}
.stTextInput input,.stNumberInput input,.stTextArea textarea,.stSelectbox>div>div{
  background:var(--bg3)!important;border:1px solid var(--border)!important;
  color:var(--text)!important;border-radius:6px!important;font-size:0.85rem!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--teal)!important;box-shadow:0 0 0 2px rgba(0,201,177,0.15)!important;}
label{color:#94a3b8!important;font-size:0.78rem!important;font-weight:500!important;text-transform:uppercase;letter-spacing:.5px;}
.stButton>button{border:1px solid var(--teal)!important;background:transparent!important;color:var(--teal)!important;
  border-radius:6px!important;font-size:.8rem!important;font-weight:600!important;letter-spacing:.5px!important;transition:all .2s!important;}
.stButton>button:hover{background:rgba(0,201,177,.1)!important;box-shadow:0 0 12px rgba(0,201,177,.2)!important;}
.stButton>button[kind="primary"]{background:var(--teal)!important;color:#0a0f1e!important;font-weight:700!important;}
.stButton>button[kind="primary"]:hover{background:#00e5cf!important;box-shadow:0 0 18px rgba(0,201,177,.35)!important;}
.stTabs [data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid var(--border)!important;}
.stTabs [data-baseweb="tab"]{color:var(--muted)!important;font-size:.8rem!important;font-weight:500!important;padding:8px 18px!important;}
.stTabs [data-baseweb="tab"][aria-selected="true"]{color:var(--teal)!important;background:rgba(0,201,177,.07)!important;}
.stTabs [data-baseweb="tab-highlight"]{background:var(--teal)!important;height:2px!important;}
.stSuccess{background:rgba(34,197,94,.08)!important;border:1px solid rgba(34,197,94,.3)!important;border-radius:6px!important;}
.stError{background:rgba(239,68,68,.08)!important;border:1px solid rgba(239,68,68,.3)!important;border-radius:6px!important;}
.stWarning{background:rgba(245,158,11,.08)!important;border:1px solid rgba(245,158,11,.3)!important;border-radius:6px!important;}
.stInfo{background:rgba(0,201,177,.06)!important;border:1px solid rgba(0,201,177,.2)!important;border-radius:6px!important;}
[data-testid="stMetric"]{background:var(--bg3)!important;border:1px solid var(--border)!important;border-radius:8px!important;padding:14px!important;}
[data-testid="stMetricValue"]{color:var(--teal)!important;font-family:'Share Tech Mono',monospace!important;font-size:1.6rem!important;}
[data-testid="stMetricLabel"]{color:var(--muted)!important;font-size:.7rem!important;text-transform:uppercase;}
[data-testid="stExpander"]{background:var(--bg2)!important;border:1px solid var(--border)!important;border-radius:8px!important;}
::-webkit-scrollbar{width:4px;} ::-webkit-scrollbar-track{background:var(--bg);} ::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px;}

.cryptix-header{background:linear-gradient(135deg,#0d1428 0%,#111827 60%,#0d1428 100%);
  border:1px solid var(--border);border-top:2px solid var(--teal);border-radius:8px;
  padding:20px 28px;margin-bottom:18px;display:flex;align-items:center;gap:16px;}
.cryptix-logo{font-family:'Share Tech Mono',monospace;font-size:2rem;color:var(--teal);line-height:1;}
.cryptix-title{font-size:1.4rem;font-weight:700;color:var(--text);}
.cryptix-sub{font-size:.72rem;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin-top:3px;}

.api-badge{display:inline-flex;align-items:center;gap:6px;font-family:'Share Tech Mono',monospace;
  font-size:.6rem;letter-spacing:1.5px;padding:3px 10px;border-radius:3px;text-transform:uppercase;}
.api-ok{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);color:#22c55e;}
.api-missing{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#ef4444;}

.rule-box{border-radius:6px;padding:12px 16px;margin:6px 0;border-left:3px solid;position:relative;}
.rule-triggered{border-left-color:#ef4444;background:rgba(239,68,68,.05);}
.rule-clear{border-left-color:#22c55e;background:rgba(34,197,94,.04);}
.rule-label{font-family:'Share Tech Mono',monospace;font-size:.7rem;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;}
.rule-detail{font-size:.8rem;color:#94a3b8;}
.rule-score{font-family:'Share Tech Mono',monospace;font-size:.78rem;float:right;}

.risk-banner{border-radius:8px;padding:16px 20px;display:flex;align-items:center;gap:14px;margin:12px 0;}

.nar-box{background:#0d1428;border:1px solid rgba(0,201,177,.18);border-left:3px solid var(--teal);
  border-radius:6px;padding:20px 24px;font-family:'Share Tech Mono',monospace;font-size:.78rem;
  line-height:1.85;color:#cbd5e1;white-space:pre-wrap;position:relative;}
.nar-box::before{content:'LLAMA 3.3 70B — PENDING ANALYST REVIEW';position:absolute;top:10px;right:14px;
  font-size:.52rem;letter-spacing:2px;color:#f59e0b;opacity:.8;}

.audit-row{background:var(--bg2);border:1px solid rgba(255,255,255,.05);border-radius:5px;
  padding:10px 14px;margin:4px 0;display:grid;grid-template-columns:80px 28px 1fr 120px;
  gap:10px;align-items:start;font-size:.78rem;}
.audit-ts{font-family:'Share Tech Mono',monospace;color:var(--muted);font-size:.65rem;}
.audit-body{color:#94a3b8;line-height:1.4;}
.audit-who{font-family:'Share Tech Mono',monospace;font-size:.62rem;color:var(--muted);text-align:right;}

.pill{display:inline-block;border-radius:3px;padding:2px 10px;font-size:.6rem;letter-spacing:1.5px;
  font-weight:600;font-family:'Share Tech Mono',monospace;text-transform:uppercase;}
.pill-open{background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.4);color:#f59e0b;}
.pill-approved{background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.4);color:#22c55e;}
.pill-closed{background:rgba(100,116,139,.15);border:1px solid rgba(100,116,139,.4);color:#64748b;}
.pill-review{background:rgba(124,111,247,.12);border:1px solid rgba(124,111,247,.4);color:#7c6ff7;}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────
def status_pill(s):
    cls = {"OPEN":"open","APPROVED":"approved","CLOSED":"closed","UNDER REVIEW":"review"}.get(s,"open")
    return f'<span class="pill pill-{cls}">{s}</span>'

def risk_color(score):
    if score >= 80: return "#ef4444"
    if score >= 60: return "#f97316"
    if score >= 40: return "#f59e0b"
    if score >= 20: return "#22c55e"
    return "#3b82f6"

def api_badge(label, key_name):
    present = bool(os.environ.get(key_name, ""))
    cls  = "api-ok"      if present else "api-missing"
    icon = "● CONNECTED" if present else "○ KEY MISSING"
    return f'<span class="api-badge {cls}">{label}: {icon}</span>'


# ── Session state ──────────────────────────────────────────────────────
for k, v in {
    "page": "Dashboard",
    "current_case_id": None,
    "risk_result": None,
    "narrative": "",
    "edit_narrative": False,
    "_cust_id": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:12px 0 16px;'>
      <div style='font-family:"Share Tech Mono",monospace;font-size:1.6rem;color:#00c9b1;'>⬡ CRYPTIX</div>
      <div style='font-size:.58rem;color:#64748b;letter-spacing:3px;text-transform:uppercase;margin-top:4px;'>SAR Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)

    for p in ["🏠 Dashboard", "➕ New Case", "📋 All Cases", "🔍 Audit Trail"]:
        label  = p.split(" ", 1)[1]
        active = st.session_state.page == label
        if st.button(p, use_container_width=True, type="primary" if active else "secondary"):
            st.session_state.page = label
            st.rerun()

    st.markdown("---")

    # API Status Panel
    st.markdown('<div style="font-size:.6rem;color:#64748b;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">API STATUS</div>', unsafe_allow_html=True)
    st.markdown(api_badge("GROQ / LLAMA", "GROQ_API_KEY"),       unsafe_allow_html=True)
    st.markdown("<div style='height:4px;'></div>",                unsafe_allow_html=True)
    st.markdown(api_badge("MOCKAROO DATA", "MOCKAROO_API_KEY"),   unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"""
    <div style='font-family:"Share Tech Mono",monospace;font-size:.6rem;color:#64748b;line-height:2;text-align:center;'>
      <div>STACK: STREAMLIT + SQLITE</div>
      <div>LLM: {GROQ_MODEL}</div>
      <div style='color:#00c9b1;margin-top:6px;'>TEAM CRYPTIX 🔐</div>
    </div>
    """, unsafe_allow_html=True)

page = st.session_state.page


# ══════════════════════════════════════════════════════════════════════
# PAGE — DASHBOARD
# ══════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    st.markdown("""
    <div class="cryptix-header">
      <div class="cryptix-logo">⬡</div>
      <div>
        <div class="cryptix-title">CRYPTIX SAR Platform</div>
        <div class="cryptix-sub">AML Intelligence · Groq Llama 3.3 70B · Mockaroo Data · Hackathon Demo</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    stats = get_dashboard_stats()
    sars  = list_sars()

    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: st.metric("Total Cases",  stats["total_cases"])
    with k2: st.metric("Open Cases",   stats["open_cases"])
    with k3: st.metric("Approved",     stats["approved"])
    with k4: st.metric("Customers",    stats["customers"])
    with k5: st.metric("Audit Logs",   stats["audit_count"])

    st.markdown("---")
    ch1, ch2, ch3 = st.columns(3)

    with ch1:
        st.markdown("**Risk Distribution**")
        if stats["by_risk"]:
            df_r = pd.DataFrame(stats["by_risk"])
            cmap = {"IMMEDIATE ACTION REQUIRED":"#ef4444","ESCALATE FOR REVIEW":"#f97316",
                    "ENHANCED DUE DILIGENCE":"#f59e0b","STANDARD MONITORING":"#22c55e",
                    "ROUTINE SURVEILLANCE":"#3b82f6"}
            fig = px.pie(df_r, names="risk_level", values="cnt",
                         color="risk_level", color_discrete_map=cmap, hole=0.55)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#94a3b8", margin=dict(t=10,b=10,l=10,r=10), height=240)
            st.plotly_chart(fig, use_container_width=True, key="dash_risk_donut")
        else:
            st.info("No cases yet")

    with ch2:
        st.markdown("**Monthly SAR Trend**")
        if stats["monthly"]:
            df_m = pd.DataFrame(stats["monthly"])
            fig2 = go.Figure(go.Bar(x=df_m["month"], y=df_m["cnt"],
                                    marker_color="#00c9b1", text=df_m["cnt"], textposition="outside"))
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font_color="#94a3b8", xaxis=dict(showgrid=False),
                               yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                               margin=dict(t=10,b=30,l=30,r=10), height=240)
            st.plotly_chart(fig2, use_container_width=True, key="dash_monthly_trend")
        else:
            st.info("No data yet")

    with ch3:
        st.markdown("**Case Status**")
        if stats["by_status"]:
            df_s = pd.DataFrame(stats["by_status"])
            cmap2 = {"OPEN":"#f59e0b","APPROVED":"#22c55e","CLOSED":"#64748b","UNDER REVIEW":"#7c6ff7"}
            fig3 = px.bar(df_s, x="status", y="cnt", color="status",
                          color_discrete_map=cmap2, text="cnt")
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font_color="#94a3b8", showlegend=False,
                               xaxis=dict(showgrid=False),
                               yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                               margin=dict(t=10,b=30,l=30,r=10), height=240)
            fig3.update_traces(textposition="outside")
            st.plotly_chart(fig3, use_container_width=True, key="dash_status_bar")
        else:
            st.info("No data yet")

    st.markdown("---")
    if sars:
        df_all = pd.DataFrame(sars)
        if len(df_all) >= 2:
            fig_s = px.scatter(df_all, x="created_at", y="risk_score",
                               color="risk_level", hover_name="case_number",
                               hover_data=["customer_name","status"],
                               title="Risk Score Over Time",
                               color_discrete_map={"IMMEDIATE ACTION REQUIRED":"#ef4444",
                                                   "ESCALATE FOR REVIEW":"#f97316",
                                                   "ENHANCED DUE DILIGENCE":"#f59e0b",
                                                   "STANDARD MONITORING":"#22c55e"})
            fig_s.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                font_color="#94a3b8", margin=dict(t=40,b=30,l=40,r=20), height=240,
                                title_font_size=12, title_font_color="#94a3b8")
            st.plotly_chart(fig_s, use_container_width=True, key="dash_scatter")

        st.markdown("**Recent Cases**")
        for s in sars[:8]:
            rc   = risk_color(s.get("risk_score", 0))
            pill = status_pill(s.get("status","OPEN"))
            ca, cb, cc, cd, ce = st.columns([2,2,1,1,1])
            with ca: st.markdown(f"**{s['case_number']}**")
            with cb: st.markdown(f"`{s.get('customer_name','N/A')}`")
            with cc: st.markdown(f"<span style='color:{rc};font-weight:700;font-size:1.1rem;'>{s.get('risk_score',0):.0f}</span>/100", unsafe_allow_html=True)
            with cd: st.markdown(pill, unsafe_allow_html=True)
            with ce:
                if st.button("View", key=f"v_{s['id']}"):
                    st.session_state.current_case_id = s["id"]
                    st.session_state.page = "All Cases"
                    st.rerun()
            st.markdown("<hr style='margin:2px 0;border-color:rgba(255,255,255,0.04);'>", unsafe_allow_html=True)
    else:
        st.info("No SAR cases yet. Click **➕ New Case** to get started.")


# ══════════════════════════════════════════════════════════════════════
# PAGE — NEW CASE
# ══════════════════════════════════════════════════════════════════════
elif page == "New Case":
    st.markdown("""
    <div class="cryptix-header">
      <div class="cryptix-logo">＋</div>
      <div>
        <div class="cryptix-title">New SAR Case</div>
        <div class="cryptix-sub">Mockaroo Data → Risk Engine → Llama 3.3 Narrative → Audit Trail</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab_cust, tab_txn, tab_risk, tab_nar, tab_submit = st.tabs([
        " Customer Data",
        " Transaction Input",
        " Risk Analysis",
        " SAR Narrative",
        " Submit",
    ])

    # ── TAB 1: Customer ──────────────────────────────────────────────
    with tab_cust:
        st.markdown("##### Customer KYC Information")

        # Mockaroo auto-fill button
        mck1, mck2 = st.columns([1, 4])
        with mck1:
            if st.button(" Auto-fill ", use_container_width=True):
                with st.spinner("Fetching…"):
                    records = fetch_mockaroo_customers(1)
                    if records:
                        r = records[0]
                        st.session_state["_mck_name"]    = r.get("name","")
                        st.session_state["_mck_profile"] = r.get("profile_type","Retail")
                        st.session_state["_mck_income"]  = int(r.get("monthly_income", 45000))
                        st.session_state["_mck_status"]  = r.get("account_status","Active")
                        st.session_state["_mck_kyc"]     = r.get("kyc_risk","Medium")
                        st.session_state["_mck_inactive"]= int(r.get("inactive_days", 0))
                        st.session_state["_mck_account"] = r.get("account_number","")
                        if os.environ.get("MOCKAROO_API_KEY"):
                            st.success("✓ Fields populated")
                        else:
                            st.info("ℹ️ MOCKAROO_API_KEY not set — used local fallback data")

        c1, c2, c3 = st.columns(3)
        with c1:
            cust_name    = st.text_input("Full Name",
                value=st.session_state.get("_mck_name", "Rajesh Kumar Verma"))
            profile_type = st.selectbox("Profile Type",
                ["Retail","SME","Corporate","HNI","PEP"],
                index=["Retail","SME","Corporate","HNI","PEP"].index(
                    st.session_state.get("_mck_profile","Retail")))
            account_no   = st.text_input("Account Number",
                value=st.session_state.get("_mck_account","HDFC4082917364"))
        with c2:
            monthly_inc  = st.number_input("Declared Monthly Income (₹)",
                value=int(st.session_state.get("_mck_income", 45000)), step=5000)
            acct_status  = st.selectbox("Account Status",
                ["Active","Dormant","Restricted","Under Review"],
                index=["Active","Dormant","Restricted","Under Review"].index(
                    st.session_state.get("_mck_status","Active")))
            kyc_risk     = st.selectbox("KYC Risk Category",
                ["Low","Medium","High","PEP","Sanctioned"],
                index=["Low","Medium","High","PEP","Sanctioned"].index(
                    st.session_state.get("_mck_kyc","Medium")))
        with c3:
            inactive_d   = st.number_input("Days Since Last Activity",
                value=int(st.session_state.get("_mck_inactive", 210)),
                min_value=0, max_value=3650)
            analyst_name = st.text_input("Analyst Name", value="Priya Sharma")
            analyst_role = st.selectbox("Role",
                ["Senior AML Analyst","AML Analyst","Compliance Officer","Team Lead"])

        if st.button("💾 Save Customer", type="primary"):
            last_active = (datetime.now() - timedelta(days=inactive_d)).strftime("%Y-%m-%d")
            cid = insert_customer({
                "name": cust_name, "profile_type": profile_type,
                "monthly_income": monthly_inc, "account_status": acct_status,
                "kyc_risk": kyc_risk, "last_active_date": last_active,
                "inactive_days": inactive_d, "account_number": account_no,
            })
            st.session_state.update({
                "_cust_id": cid, "_cust_name": cust_name,
                "_profile_type": profile_type, "_monthly_inc": monthly_inc,
                "_inactive_d": inactive_d, "_account_no": account_no,
                "_analyst_name": analyst_name, "_analyst_role": analyst_role,
            })
            log_audit(None, cid, "CUSTOMER_CREATED", analyst_name, analyst_role,
                      f"Customer profile created for {cust_name}",
                      {"profile": profile_type, "income": monthly_inc, "kyc": kyc_risk})
            st.success(f"✓ Customer saved — ID: `{cid}` → proceed to Transaction Input")

    # ── TAB 2: Transactions ──────────────────────────────────────────
    with tab_txn:
        st.markdown("##### Transaction Alert Data")

        t1, t2, t3 = st.columns(3)
        with t1:
            txn_amount    = st.number_input("High-Value Transaction Amount (₹)", value=980000, step=10000)
            avg_per_day   = st.number_input("Historical Avg Transactions/Day",   value=1.2, step=0.1, format="%.1f")
        with t2:
            current_count = st.number_input("Transactions Today (Count)",        value=17, min_value=0)
            near_thresh   = st.number_input("Near-Threshold Txns (Last 7 Days)", value=5,  min_value=0)
        with t3:
            st.metric("Reporting Threshold",  f"₹{REPORTING_THRESHOLD:,.0f}")
            st.metric("Near-Threshold Range", f"₹{REPORTING_THRESHOLD*0.85:,.0f} – ₹{REPORTING_THRESHOLD*0.99:,.0f}")

        # Mockaroo fetch transactions button
        mbt1, mbt2 = st.columns([1,4])
        with mbt1:
            fetch_txn_btn = st.button("🎲 Fetch Txns ", use_container_width=True)

        if fetch_txn_btn:
            cid = st.session_state.get("_cust_id")
            if not cid:
                st.error("Save Customer Data first!")
            else:
                with st.spinner("Fetching transactions.."):
                    txns = fetch_mockaroo_transactions(
                        cid, count=current_count,
                        txn_amount=txn_amount,
                        near_threshold=near_thresh,
                    )
                insert_transactions(txns)
                st.session_state["_txns_loaded"] = True
                if os.environ.get("MOCKAROO_API_KEY"):
                    st.success(f"✓ {len(txns)} transactions fetched ")
                else:
                    st.info(f"ℹ️ {len(txns)} transactions generated locally (set MOCKAROO_API_KEY to use API)")

        if st.button("⚡ Run Risk Analysis", type="primary"):
            cid = st.session_state.get("_cust_id")
            if not cid:
                st.error("Save Customer Data first!")
            else:
                # If transactions not fetched yet, generate locally
                if not st.session_state.get("_txns_loaded"):
                    txns = fetch_mockaroo_transactions(
                        cid, count=current_count,
                        txn_amount=txn_amount, near_threshold=near_thresh,
                    )
                    insert_transactions(txns)

                rr = compute_risk(
                    st.session_state.get("_inactive_d", 0), txn_amount,
                    avg_per_day, current_count,
                    st.session_state.get("_monthly_inc", 1),
                    st.session_state.get("_profile_type","Retail"), near_thresh,
                )
                st.session_state.update({
                    "risk_result":   rr,
                    "_txn_amount":   txn_amount,
                    "_avg_per_day":  avg_per_day,
                    "_curr_count":   current_count,
                    "_near_thresh":  near_thresh,
                })
                log_audit(None, cid, "RISK_COMPUTED",
                          st.session_state.get("_analyst_name","System"),
                          st.session_state.get("_analyst_role","System"),
                          f"Risk score: {rr['risk_score']}/100 — {rr['risk_level']}",
                          {"score": rr["risk_score"]}, rr["triggered_rules"])
                st.success(f"✓ Risk computed: **{rr['risk_score']}/100** — {rr['risk_icon']} {rr['risk_level']}")
                st.info("Proceed to **⚠️ Risk Analysis** tab")

    # ── TAB 3: Risk Analysis ─────────────────────────────────────────
    with tab_risk:
        rr = st.session_state.get("risk_result")
        if not rr:
            st.info("Run Risk Analysis in the Transaction Input tab first.")
        else:
            rc = rr["risk_color"]
            st.markdown(f"""
            <div class="risk-banner" style="background:rgba(0,0,0,0.3);border:1px solid {rc}40;border-left:4px solid {rc};">
              <div style="font-size:2.2rem;">{rr['risk_icon']}</div>
              <div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:.65rem;color:#64748b;letter-spacing:2px;text-transform:uppercase;">COMPOSITE RISK SCORE</div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:2.5rem;font-weight:700;color:{rc};line-height:1.1;">{rr['risk_score']}<span style="font-size:1rem;color:#64748b;">/100</span></div>
                <div style="font-size:.9rem;font-weight:600;color:{rc};">{rr['risk_level']}</div>
              </div>
              <div style="margin-left:auto;text-align:right;">
                <div style="font-size:.7rem;color:#64748b;text-transform:uppercase;letter-spacing:1px;">Rules Triggered</div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:1.5rem;color:{rc};">{len(rr['triggered_rules'])}/4</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Score breakdown chart
            bd      = rr["score_breakdown"]
            weights = [30, 25, 25, 20]
            colors  = ["#00c9b1","#7c6ff7","#f59e0b","#ef4444"]
            fig_bd  = go.Figure()
            for i, (rule, val) in enumerate(zip(bd.keys(), bd.values())):
                fig_bd.add_trace(go.Bar(
                    name=rule, x=[rule], y=[val],
                    marker_color=colors[i], width=0.5,
                    text=[f"{val:.1f}/{weights[i]}"], textposition="outside",
                ))
            fig_bd.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#94a3b8", showlegend=False, barmode="group",
                xaxis=dict(showgrid=False, tickfont_size=9),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", title="Points"),
                margin=dict(t=20,b=30,l=40,r=20), height=240,
                title=dict(text="Score Breakdown by Rule (Weighted)", font_size=11, font_color="#94a3b8"),
            )
            st.plotly_chart(fig_bd, use_container_width=True, key="risk_breakdown_bar")

            # Radar + Rule cards
            col_radar, col_rules = st.columns([1,1])
            with col_radar:
                st.markdown("**Risk Radar**")
                vals_r = [rr["rules"][k]["score"] for k in ["dormant","frequency","profile","structuring"]]
                labels_r = ["Dormant Activation","Frequency Spike","Profile Mismatch","Near-Threshold Structuring"]
                fig_r = go.Figure(go.Scatterpolar(
                    r=vals_r + [vals_r[0]], theta=labels_r + [labels_r[0]],
                    fill="toself", line_color="#00c9b1", fillcolor="rgba(0,201,177,0.15)",
                ))
                fig_r.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0,100], tickfont_size=8,
                                              gridcolor="rgba(255,255,255,0.08)"),
                               angularaxis=dict(tickfont_size=9, gridcolor="rgba(255,255,255,0.08)"),
                               bgcolor="rgba(0,0,0,0)"),
                    paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8",
                    margin=dict(t=30,b=30,l=60,r=60), height=280, showlegend=False,
                )
                st.plotly_chart(fig_r, use_container_width=True, key="risk_radar")

            with col_rules:
                st.markdown("**Rule Assessment**")
                rules_meta = [
                    ("dormant",     "🔵","#00c9b1","DORMANT ACTIVATION",          30),
                    ("frequency",   "🟣","#7c6ff7","FREQUENCY SPIKE",             25),
                    ("profile",     "🟡","#f59e0b","PROFILE MISMATCH",            25),
                    ("structuring", "🔴","#ef4444","NEAR-THRESHOLD STRUCTURING",  20),
                ]
                for key, emoji, col, label, wt in rules_meta:
                    r      = rr["rules"][key]
                    cls    = "rule-triggered" if r["triggered"] else "rule-clear"
                    badge  = f"<span style='color:{'#ef4444' if r['triggered'] else '#22c55e'};font-weight:700;'>{'● TRIGGERED' if r['triggered'] else '○ CLEAR'}</span>"
                    score_str = f"<span class='rule-score' style='color:{col};'>{r['contribution']:.1f}/{wt}pts</span>"
                    st.markdown(f"""
                    <div class="rule-box {cls}">
                      <div class="rule-label" style="color:{col};">{emoji} {label} {badge} {score_str}</div>
                      <div class="rule-detail">{r['detail']}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # Transaction table
            cid = st.session_state.get("_cust_id")
            if cid:
                txns_db = get_transactions(cid)
                if txns_db:
                    st.markdown("**Flagged Transactions**")
                    df_t = pd.DataFrame(txns_db)[["txn_date","txn_type","amount","counterparty","channel","flag_reason"]]
                    df_t = df_t[df_t["amount"] > 0].head(15)
                    df_t["amount"] = df_t["amount"].apply(lambda x: f"₹{x:,.0f}")
                    st.dataframe(df_t, use_container_width=True, hide_index=True)

    # ── TAB 4: SAR Narrative ─────────────────────────────────────────
    with tab_nar:
        rr = st.session_state.get("risk_result")
        if not rr:
            st.info("Complete Risk Analysis first.")
        else:
            # Show which model will be used
            groq_ok = bool(os.environ.get("GROQ_API_KEY",""))
            st.markdown(
                f'Using: <span class="api-badge {"api-ok" if groq_ok else "api-missing"}">'
                f'{"● " if groq_ok else "○ "}{GROQ_MODEL}</span>'
                + (" — key found ✓" if groq_ok else " — set GROQ_API_KEY to enable"),
                unsafe_allow_html=True
            )
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            gc1, gc2 = st.columns([1,1])
            with gc1:
                gen_btn = st.button("⚡ Generate SAR via Llama 3.3 70B", type="primary", use_container_width=True)
            with gc2:
                if st.session_state.narrative:
                    if st.button("✏️ Toggle Edit Mode", use_container_width=True):
                        st.session_state.edit_narrative = not st.session_state.edit_narrative
                        st.rerun()

            if gen_btn:
                if not groq_ok:
                    st.error("❌ GROQ_API_KEY not set!\n\nIn your terminal run:\n```\n$env:GROQ_API_KEY='gsk_your_key_here'\n```\nthen restart Streamlit.")
                else:
                    cid      = st.session_state.get("_cust_id")
                    customer = get_customer(cid) if cid else {}
                    if not customer:
                        customer = {
                            "name":           st.session_state.get("_cust_name",""),
                            "profile_type":   st.session_state.get("_profile_type",""),
                            "monthly_income": st.session_state.get("_monthly_inc", 0),
                            "account_status": "Active",
                            "kyc_risk":       "High",
                            "inactive_days":  st.session_state.get("_inactive_d", 0),
                            "account_number": st.session_state.get("_account_no",""),
                        }
                    try:
                        with st.spinner(f"🦙 Llama 3.3 70B (Groq) is drafting the SAR narrative…"):
                            narrative_text, model_used = generate_sar_narrative(
                                customer, rr,
                                st.session_state.get("_txn_amount", 0),
                                st.session_state.get("_near_thresh", 0),
                                st.session_state.get("_avg_per_day", 1.0),
                                st.session_state.get("_curr_count", 0),
                            )
                        st.session_state.narrative = narrative_text
                        st.session_state.edit_narrative = False
                        log_audit(None, cid, "NARRATIVE_GENERATED",
                                  model_used, "AI Engine",
                                  f"SAR narrative generated — {len(narrative_text)} chars",
                                  {"model": model_used}, rr["triggered_rules"])
                        st.success(f"✓ Narrative generated by {model_used} → Proceed to Submit")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Groq API error: {e}")
                        log_audit(None, cid, "NARRATIVE_ERROR", "System","AI Engine", str(e)[:120])

            if st.session_state.narrative:
                if st.session_state.edit_narrative:
                    st.markdown("**✏️ Edit Mode — tracked in audit trail**")
                    edited = st.text_area("Edit Narrative",
                                         value=st.session_state.narrative, height=500)
                    s1, s2 = st.columns(2)
                    with s1:
                        if st.button("💾 Save Edits", type="primary"):
                            old_len = len(st.session_state.narrative)
                            st.session_state.narrative = edited
                            st.session_state.edit_narrative = False
                            log_audit(None, st.session_state.get("_cust_id"),
                                      "NARRATIVE_EDITED",
                                      st.session_state.get("_analyst_name","Analyst"),
                                      st.session_state.get("_analyst_role",""),
                                      f"Narrative edited: {old_len}→{len(edited)} chars")
                            st.rerun()
                    with s2:
                        if st.button("✕ Discard"):
                            st.session_state.edit_narrative = False
                            st.rerun()
                else:
                    safe_nar = html.escape(st.session_state.narrative)
                    st.markdown(f'<div class="nar-box">{safe_nar}</div>', unsafe_allow_html=True)

    # ── TAB 5: Submit ────────────────────────────────────────────────
    with tab_submit:
        rr = st.session_state.get("risk_result")
        if not rr or not st.session_state.narrative:
            st.info("Complete Risk Analysis and generate Narrative before submitting.")
        else:
            st.markdown("##### Final Review & Submission")
            cid      = st.session_state.get("_cust_id")
            analyst  = st.session_state.get("_analyst_name","")
            role     = st.session_state.get("_analyst_role","")

            cs1, cs2 = st.columns([2,1])
            with cs1:
                st.markdown(f"""
                **Case Summary**
                - **Customer:** {st.session_state.get('_cust_name','')}
                - **Account:** `{st.session_state.get('_account_no','')}`
                - **Risk Score:** `{rr['risk_score']}/100` — {rr['risk_icon']} {rr['risk_level']}
                - **Triggered Rules:** `{', '.join(rr['triggered_rules']) or 'None'}`
                - **Analyst:** {analyst} ({role})
                - **LLM Used:** `{GROQ_MODEL}`
                """)
            with cs2:
                analyst_notes = st.text_area("Final Notes",
                    placeholder="Justification / escalation notes…", height=100)
                decision = st.radio("Decision", [
                    "APPROVE & FILE",
                    "RETURN FOR REVISION",
                    "CLOSE — NO ACTION",
                ])

            if st.button("📤 Submit SAR Case", type="primary", use_container_width=True):
                status_map = {
                    "APPROVE & FILE":       "APPROVED",
                    "RETURN FOR REVISION":  "UNDER REVIEW",
                    "CLOSE — NO ACTION":    "CLOSED",
                }
                status = status_map.get(decision, "OPEN")
                sid, case_num = create_sar({
                    "customer_id":      cid,
                    "risk_score":       rr["risk_score"],
                    "risk_level":       rr["risk_level"],
                    "status":           status,
                    "dormant_score":    rr["rules"]["dormant"]["contribution"],
                    "frequency_score":  rr["rules"]["frequency"]["contribution"],
                    "profile_score":    rr["rules"]["profile"]["contribution"],
                    "structuring_score":rr["rules"]["structuring"]["contribution"],
                    "triggered_rules":  rr["triggered_rules"],
                    "narrative":        st.session_state.narrative,
                    "created_by":       analyst,
                    "assigned_to":      analyst,
                })
                log_audit(sid, cid, f"SAR_{status}", analyst, role,
                          f"SAR {case_num} submitted — {decision}. {analyst_notes[:80]}",
                          {"case_num": case_num, "risk": rr["risk_score"]},
                          rr["triggered_rules"])
                st.success(f"✓ SAR **{case_num}** submitted — status: **{status}**")
                # Reset case state
                for k in ["risk_result","narrative","edit_narrative","_cust_id",
                          "_txns_loaded","_mck_name","_mck_profile","_mck_income",
                          "_mck_status","_mck_kyc","_mck_inactive","_mck_account"]:
                    st.session_state.pop(k, None)


# ══════════════════════════════════════════════════════════════════════
# PAGE — ALL CASES
# ══════════════════════════════════════════════════════════════════════
elif page == "All Cases":
    st.markdown("""
    <div class="cryptix-header">
      <div class="cryptix-logo">📋</div>
      <div>
        <div class="cryptix-title">SAR Case Registry</div>
        <div class="cryptix-sub">All cases · Search · Detail view · Status updates</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    sars = list_sars()
    if not sars:
        st.info("No cases yet. Create one using ➕ New Case.")
    else:
        f1,f2,f3 = st.columns(3)
        with f1: fstatus = st.selectbox("Status",   ["All","OPEN","APPROVED","UNDER REVIEW","CLOSED"])
        with f2: frisk   = st.selectbox("Risk Level",["All","IMMEDIATE ACTION REQUIRED","ESCALATE FOR REVIEW","ENHANCED DUE DILIGENCE","STANDARD MONITORING"])
        with f3: fsearch = st.text_input("Search customer / case #","")

        filtered = sars
        if fstatus != "All": filtered = [s for s in filtered if s.get("status")==fstatus]
        if frisk   != "All": filtered = [s for s in filtered if s.get("risk_level")==frisk]
        if fsearch:          filtered = [s for s in filtered if fsearch.lower() in s.get("customer_name","").lower() or fsearch in s.get("case_number","")]

        st.markdown(f"**{len(filtered)} case(s) found**")
        selected = st.session_state.current_case_id

        for s in filtered:
            rc   = risk_color(s.get("risk_score",0))
            pill = status_pill(s.get("status","OPEN"))
            with st.expander(f"🔐 {s['case_number']}  |  {s.get('customer_name','?')}  |  Risk: {s.get('risk_score',0):.0f}/100", expanded=(s["id"]==selected)):
                d1,d2,d3 = st.columns(3)
                with d1:
                    st.markdown(f"**Case #:** `{s['case_number']}`")
                    st.markdown(f"**Customer:** {s.get('customer_name','')}")
                    st.markdown(f"**Account:** `{s.get('account_number','')}`")
                with d2:
                    st.markdown(f"**Risk Score:** <span style='color:{rc};font-size:1.3rem;font-weight:700;'>{s.get('risk_score',0):.0f}/100</span>", unsafe_allow_html=True)
                    st.markdown(f"**Risk Level:** {s.get('risk_level','')}")
                    st.markdown(f"**Status:** {pill}", unsafe_allow_html=True)
                with d3:
                    st.markdown(f"**Created By:** {s.get('created_by','')}")
                    st.markdown(f"**Created At:** {s.get('created_at','')[:16]}")
                    rules = json.loads(s.get("triggered_rules","[]"))
                    st.markdown(f"**Rules:** `{', '.join(rules) or 'None'}`")

                # Mini score breakdown chart
                df_bd = pd.DataFrame({
                    "Rule":  ["Dormant","Frequency","Profile","Structuring"],
                    "Score": [s.get("dormant_score",0), s.get("frequency_score",0),
                              s.get("profile_score",0), s.get("structuring_score",0)],
                    "Max":   [30,25,25,20],
                })
                fig_m = go.Figure()
                fig_m.add_trace(go.Bar(x=df_bd["Rule"], y=df_bd["Max"],
                                       marker_color="rgba(255,255,255,0.06)", name="Max"))
                fig_m.add_trace(go.Bar(x=df_bd["Rule"], y=df_bd["Score"],
                                       marker_color=["#00c9b1","#7c6ff7","#f59e0b","#ef4444"],
                                       name="Score",
                                       text=[f"{v:.1f}" for v in df_bd["Score"]],
                                       textposition="outside"))
                fig_m.update_layout(barmode="overlay", paper_bgcolor="rgba(0,0,0,0)",
                                    plot_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8",
                                    height=180, margin=dict(t=10,b=30,l=30,r=10),
                                    showlegend=False,
                                    yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,0.06)"))
                st.plotly_chart(fig_m, use_container_width=True, key=f"case_mini_{s['id']}")

                if s.get("narrative"):
                    excerpt = html.escape(s["narrative"][:500] + ("…" if len(s["narrative"])>500 else ""))
                    st.markdown(f'<div class="nar-box" style="max-height:180px;overflow-y:auto;">{excerpt}</div>', unsafe_allow_html=True)

                st.markdown("---")
                u1,u2,u3 = st.columns([2,1,1])
                with u1: new_notes  = st.text_input("Add Note", key=f"note_{s['id']}", placeholder="Analyst note…")
                with u2: new_status = st.selectbox("Update Status",["OPEN","APPROVED","UNDER REVIEW","CLOSED"], key=f"st_{s['id']}")
                with u3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Update", key=f"upd_{s['id']}", type="primary"):
                        update_sar(s["id"], {"status": new_status, "analyst_notes": new_notes})
                        log_audit(s["id"], s.get("customer_id"), "STATUS_UPDATED",
                                  "Analyst","Analyst", f"Status → {new_status}. {new_notes}")
                        st.success("Updated!"); st.rerun()


# ══════════════════════════════════════════════════════════════════════
# PAGE — AUDIT TRAIL
# ══════════════════════════════════════════════════════════════════════
elif page == "Audit Trail":
    st.markdown("""
    <div class="cryptix-header">
      <div class="cryptix-logo">🔍</div>
      <div>
        <div class="cryptix-title">Audit Trail</div>
        <div class="cryptix-sub">Immutable · Tamper-Evident · Full Traceability</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    entries = get_audit_trail()
    if entries:
        df_a = pd.DataFrame(entries)
        df_a["timestamp"] = pd.to_datetime(df_a["timestamp"])
        df_a["hour"] = df_a["timestamp"].dt.floor("h")
        counts = df_a.groupby("hour").size().reset_index(name="count")

        ch_a, ch_b = st.columns(2)
        with ch_a:
            fig_tl = go.Figure(go.Scatter(
                x=counts["hour"], y=counts["count"],
                mode="lines+markers", line_color="#00c9b1",
                fill="tozeroy", fillcolor="rgba(0,201,177,0.08)",
            ))
            fig_tl.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                 font_color="#94a3b8", height=180,
                                 margin=dict(t=10,b=20,l=30,r=10),
                                 xaxis=dict(showgrid=False),
                                 yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,0.06)",title="Events"),
                                 title=dict(text="Activity Timeline", font_size=11, font_color="#94a3b8"))
            st.plotly_chart(fig_tl, use_container_width=True, key="audit_timeline")

        with ch_b:
            ac_counts = df_a["action"].value_counts().reset_index()
            ac_counts.columns = ["action","count"]
            fig_ac = px.bar(ac_counts.head(8), x="action", y="count",
                            color="action", text="count",
                            color_discrete_sequence=["#00c9b1","#7c6ff7","#f59e0b","#ef4444","#22c55e","#3b82f6"])
            fig_ac.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                 font_color="#94a3b8", showlegend=False, height=180,
                                 margin=dict(t=10,b=30,l=30,r=10),
                                 xaxis=dict(showgrid=False, tickfont_size=8),
                                 yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,0.06)"),
                                 title=dict(text="Events by Action", font_size=11, font_color="#94a3b8"))
            fig_ac.update_traces(textposition="outside")
            st.plotly_chart(fig_ac, use_container_width=True, key="audit_actions")

        st.markdown(f"**{len(entries)} audit entries** — newest first")

        acolors = {
            "CUSTOMER_CREATED":"#00c9b1","RISK_COMPUTED":"#f59e0b",
            "NARRATIVE_GENERATED":"#7c6ff7","NARRATIVE_EDITED":"#f97316",
            "SAR_APPROVED":"#22c55e","SAR_CLOSED":"#64748b",
            "STATUS_UPDATED":"#3b82f6","NARRATIVE_ERROR":"#ef4444",
        }
        aicons = {
            "CUSTOMER_CREATED":"👤","RISK_COMPUTED":"⚠️",
            "NARRATIVE_GENERATED":"🦙","NARRATIVE_EDITED":"✏️",
            "SAR_APPROVED":"✅","SAR_CLOSED":"🔒",
            "STATUS_UPDATED":"🔄","NARRATIVE_ERROR":"❌",
        }
        st.markdown("""
        <div class="audit-row" style="background:#1a2235;font-size:.65rem;color:#64748b;text-transform:uppercase;letter-spacing:1px;">
          <span>TIME</span><span></span><span>EVENT</span><span>ACTOR</span>
        </div>
        """, unsafe_allow_html=True)

        for e in entries[:60]:
            ac = acolors.get(e["action"],"#64748b")
            ic = aicons.get(e["action"],"○")
            ts = e["timestamp"][:19].replace("T"," ")[-8:]
            st.markdown(f"""
            <div class="audit-row">
              <div class="audit-ts">{ts}</div>
              <div style="font-size:.9rem;">{ic}</div>
              <div class="audit-body">
                <span style="font-family:'Share Tech Mono',monospace;font-size:.62rem;color:{ac};
                      background:rgba(255,255,255,.04);padding:1px 7px;border-radius:3px;
                      margin-right:8px;border:1px solid {ac}33;">{html.escape(e['action'])}</span>
                {html.escape(e.get('detail',''))}
              </div>
              <div class="audit-who">{html.escape(e.get('actor',''))}<br>
                <span style="font-size:.55rem;">{html.escape(e.get('actor_role',''))}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

        import hashlib
        h = hashlib.sha256(json.dumps([e["id"] for e in entries]).encode()).hexdigest()[:24].upper()
        st.markdown(f"""
        <div style="margin-top:16px;text-align:center;font-family:'Share Tech Mono',monospace;
             font-size:.6rem;color:#64748b;padding:10px;background:#111827;
             border:1px solid rgba(0,201,177,0.12);border-radius:6px;">
          ⬡ INTEGRITY HASH: <span style="color:#00c9b1;">{h}</span>
          &nbsp;·&nbsp; {len(entries)} RECORDS &nbsp;·&nbsp; TAMPER-EVIDENT LOG
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No audit entries yet.")


# ── Footer ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:40px;padding:12px 0;border-top:1px solid rgba(0,201,177,0.1);
     text-align:center;font-family:'Share Tech Mono',monospace;font-size:.58rem;color:#374151;">
  CRYPTIX SAR &nbsp;·&nbsp; LLM: {GROQ_MODEL} via GROQ &nbsp;·&nbsp; DATA: MOCKAROO &nbsp;·&nbsp;
  PMLA 2002 · FATF R.20 &nbsp;·&nbsp; TEAM CRYPTIX 🔐 &nbsp;·&nbsp;
  ALL AI OUTPUTS REQUIRE HUMAN REVIEW BEFORE REGULATORY SUBMISSION
</div>
""", unsafe_allow_html=True)