"""
CRYPTIX SAR — Risk Engine + Mockaroo Data Layer
Fetches realistic customer & transaction data from Mockaroo API,
then scores them through 4 AML detection rules.
"""

import os
import uuid
import random
import requests
from datetime import datetime, timedelta

# ── API Config ────────────────────────────────────────────────────────
MOCKAROO_API_KEY  = os.environ.get("MOCKAROO_API_KEY", "")
MOCKAROO_BASE_URL = "https://api.mockaroo.com/api"

REPORTING_THRESHOLD = 1_000_000   # INR 10 Lakh

# ── Risk Level Labels (banking-grade) ────────────────────────────────
RISK_LABELS = {
    (80, 100): ("IMMEDIATE ACTION REQUIRED",  "#e53935", "🔴"),
    (60,  79): ("ESCALATE FOR REVIEW",        "#f57c00", "🟠"),
    (40,  59): ("ENHANCED DUE DILIGENCE",     "#f9a825", "🟡"),
    (20,  39): ("STANDARD MONITORING",        "#43a047", "🟢"),
    (0,   19): ("ROUTINE SURVEILLANCE",       "#1e88e5", "🔵"),
}

RULE_WEIGHTS = {
    "dormant":     30,
    "frequency":   25,
    "profile":     25,
    "structuring": 20,
}


def get_risk_label(score: float):
    for (lo, hi), (label, color, icon) in RISK_LABELS.items():
        if lo <= score <= hi:
            return label, color, icon
    return "ROUTINE SURVEILLANCE", "#1e88e5", "🔵"


# ══════════════════════════════════════════════════════════════════════
# MOCKAROO DATA FETCHER
# ══════════════════════════════════════════════════════════════════════

def fetch_mockaroo_customers(count: int = 1) -> list[dict]:
    """
    Fetch customer records from Mockaroo.
    Falls back to local generation if API key missing or call fails.
    """
    if not MOCKAROO_API_KEY:
        return _local_customers(count)

    schema = [
        {"name": "name",           "type": "Full Name"},
        {"name": "profile_type",   "type": "Custom List",
         "values": ["Retail", "SME", "Corporate", "HNI", "PEP"]},
        {"name": "monthly_income", "type": "Number",
         "min": 20000, "max": 500000, "decimals": 0},
        {"name": "account_status", "type": "Custom List",
         "values": ["Active", "Dormant", "Restricted", "Under Review"]},
        {"name": "kyc_risk",       "type": "Custom List",
         "values": ["Low", "Medium", "High"]},
        {"name": "inactive_days",  "type": "Number",
         "min": 0, "max": 365, "decimals": 0},
        {"name": "account_number", "type": "Alphanumeric",
         "length": 12},
    ]
    try:
        resp = requests.post(
            f"{MOCKAROO_BASE_URL}/generate.json",
            params={"key": MOCKAROO_API_KEY, "count": count},
            json=schema,
            timeout=10
        )
        resp.raise_for_status()
        records = resp.json()
        # Normalise fields
        cleaned = []
        for r in records:
            r["monthly_income"] = float(r.get("monthly_income", 45000))
            r["inactive_days"]  = int(r.get("inactive_days", 0))
            r["account_number"] = "MOCK" + str(r.get("account_number","")).upper()[:10]
            r["last_active_date"] = (
                datetime.now() - timedelta(days=r["inactive_days"])
            ).strftime("%Y-%m-%d")
            cleaned.append(r)
        return cleaned
    except Exception as e:
        print(f"[Mockaroo] Customer fetch failed: {e} — using local fallback")
        return _local_customers(count)


def fetch_mockaroo_transactions(customer_id: str, count: int = 20,
                                 txn_amount: float = 500000,
                                 near_threshold: int = 4) -> list[dict]:
    """
    Fetch transaction records from Mockaroo.
    Falls back to local generation if API key missing or call fails.
    """
    if not MOCKAROO_API_KEY:
        return _local_transactions(customer_id, count, txn_amount, near_threshold)

    banks    = ["HDFC Bank", "SBI", "ICICI Bank", "Axis Bank",
                "Kotak Bank", "PNB", "Bank of Baroda", "Yes Bank"]
    channels = ["NEFT", "RTGS", "IMPS", "UPI", "SWIFT", "Cash"]

    schema = [
        {"name": "txn_type",    "type": "Custom List",
         "values": ["CREDIT", "DEBIT"]},
        {"name": "amount",      "type": "Number",
         "min": 5000, "max": int(txn_amount), "decimals": 0},
        {"name": "counterparty","type": "Custom List",  "values": banks},
        {"name": "channel",     "type": "Custom List",  "values": channels},
        {"name": "txn_date",    "type": "Datetime",
         "min": "2025-01-01 00:00:00", "max": "2025-02-15 23:59:59",
         "format": "%Y-%m-%d %H:%M:%S"},
    ]
    try:
        resp = requests.post(
            f"{MOCKAROO_BASE_URL}/generate.json",
            params={"key": MOCKAROO_API_KEY, "count": count},
            json=schema,
            timeout=10
        )
        resp.raise_for_status()
        raw = resp.json()

        txns = []
        base = datetime.now()

        # Inject the main high-value flagged transaction
        txns.append({
            "id":          str(uuid.uuid4())[:8],
            "customer_id": customer_id,
            "amount":      txn_amount,
            "txn_type":    "CREDIT",
            "counterparty": f"{random.choice(banks)} ****{random.randint(1000,9999)}",
            "channel":     "RTGS",
            "txn_date":    base.strftime("%Y-%m-%d %H:%M:%S"),
            "is_flagged":  1,
            "flag_reason": "High-value post-dormancy transaction",
        })

        # Inject near-threshold transactions
        for _ in range(near_threshold):
            dt  = base - timedelta(days=random.randint(1,7))
            amt = REPORTING_THRESHOLD * random.uniform(0.88, 0.98)
            txns.append({
                "id":          str(uuid.uuid4())[:8],
                "customer_id": customer_id,
                "amount":      round(amt),
                "txn_type":    "CREDIT",
                "counterparty": f"{random.choice(banks)} ****{random.randint(1000,9999)}",
                "channel":     random.choice(channels),
                "txn_date":    dt.strftime("%Y-%m-%d %H:%M:%S"),
                "is_flagged":  1,
                "flag_reason": "Near-threshold structuring",
            })

        # Fill remaining from Mockaroo data
        for r in raw:
            txns.append({
                "id":          str(uuid.uuid4())[:8],
                "customer_id": customer_id,
                "amount":      float(r.get("amount", 50000)),
                "txn_type":    r.get("txn_type", "CREDIT"),
                "counterparty": f"{r.get('counterparty','Unknown')} ****{random.randint(1000,9999)}",
                "channel":     r.get("channel", "NEFT"),
                "txn_date":    r.get("txn_date", base.strftime("%Y-%m-%d %H:%M:%S")),
                "is_flagged":  1,
                "flag_reason": "Frequency spike",
            })

        return txns

    except Exception as e:
        print(f"[Mockaroo] Transaction fetch failed: {e} — using local fallback")
        return _local_transactions(customer_id, count, txn_amount, near_threshold)


# ── Local Fallbacks (used when no Mockaroo key) ───────────────────────

def _local_customers(count: int) -> list[dict]:
    names    = ["Rajesh Kumar Verma", "Sunita Rao", "Amir Khan",
                "Priya Sharma", "Vikram Singh", "Ananya Mehta"]
    profiles = ["Retail", "SME", "Corporate", "HNI", "PEP"]
    statuses = ["Active", "Dormant", "Restricted", "Under Review"]
    risks    = ["Low", "Medium", "High"]
    out = []
    for _ in range(count):
        inactive = random.randint(0, 365)
        out.append({
            "name":           random.choice(names),
            "profile_type":   random.choice(profiles),
            "monthly_income": float(random.randint(20000, 500000)),
            "account_status": random.choice(statuses),
            "kyc_risk":       random.choice(risks),
            "inactive_days":  inactive,
            "account_number": f"DEMO{random.randint(10000000, 99999999)}",
            "last_active_date": (datetime.now() - timedelta(days=inactive)).strftime("%Y-%m-%d"),
        })
    return out


def _local_transactions(customer_id: str, count: int,
                          txn_amount: float, near_threshold: int) -> list[dict]:
    """Pure-local transaction generation (no API needed)."""
    banks    = ["HDFC Bank", "SBI", "ICICI Bank", "Axis Bank",
                "Kotak Bank", "PNB", "Bank of Baroda", "Yes Bank"]
    channels = ["NEFT", "RTGS", "IMPS", "UPI", "SWIFT", "Cash"]
    base     = datetime.now()
    txns     = []

    # Main flagged transaction
    txns.append({
        "id": str(uuid.uuid4())[:8], "customer_id": customer_id,
        "amount": txn_amount, "txn_type": "CREDIT",
        "counterparty": f"{random.choice(banks)} ****{random.randint(1000,9999)}",
        "channel": "RTGS", "txn_date": base.strftime("%Y-%m-%d %H:%M:%S"),
        "is_flagged": 1, "flag_reason": "High-value post-dormancy transaction",
    })
    # Near-threshold
    for _ in range(near_threshold):
        dt  = base - timedelta(days=random.randint(1, 7))
        amt = REPORTING_THRESHOLD * random.uniform(0.88, 0.98)
        txns.append({
            "id": str(uuid.uuid4())[:8], "customer_id": customer_id,
            "amount": round(amt), "txn_type": "CREDIT",
            "counterparty": f"{random.choice(banks)} ****{random.randint(1000,9999)}",
            "channel": random.choice(channels), "txn_date": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "is_flagged": 1, "flag_reason": "Near-threshold structuring",
        })
    # Frequency spike
    for _ in range(min(count - 1, 20)):
        dt  = base - timedelta(hours=random.randint(0, 10))
        amt = random.randint(10000, 200000)
        txns.append({
            "id": str(uuid.uuid4())[:8], "customer_id": customer_id,
            "amount": amt, "txn_type": random.choice(["CREDIT", "DEBIT"]),
            "counterparty": f"{random.choice(banks)} ****{random.randint(1000,9999)}",
            "channel": random.choice(channels), "txn_date": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "is_flagged": 1, "flag_reason": "Frequency spike",
        })
    return txns


# Alias used by seed_demo.py
def generate_demo_transactions(customer_id, inactive_days, txn_amount, count, near_threshold):
    return _local_transactions(customer_id, count, txn_amount, near_threshold)


# ══════════════════════════════════════════════════════════════════════
# AML RULES ENGINE
# ══════════════════════════════════════════════════════════════════════

def check_dormant(inactive_days: int, txn_amount: float) -> dict:
    triggered = inactive_days > 90 and txn_amount > 50_000
    if not triggered:
        raw = min((inactive_days / 90) * 50, 50) if inactive_days > 30 else 0
        score = round(raw * RULE_WEIGHTS["dormant"] / 100, 1)
        return {"triggered": False, "score": score,
                "weight": RULE_WEIGHTS["dormant"], "contribution": score,
                "detail": f"Inactive {inactive_days}d — below trigger threshold"}

    dormancy_factor = min(inactive_days / 365, 1.0)
    amount_factor   = min(txn_amount / REPORTING_THRESHOLD, 1.0)
    raw_score       = (dormancy_factor * 0.6 + amount_factor * 0.4) * 100
    contribution    = round(raw_score * RULE_WEIGHTS["dormant"] / 100, 1)
    return {
        "triggered": True, "score": round(raw_score, 1),
        "weight": RULE_WEIGHTS["dormant"], "contribution": contribution,
        "detail": f"Account dormant {inactive_days} days; sudden ₹{txn_amount:,.0f} transaction",
        "dormancy_days": inactive_days, "txn_amount": txn_amount,
    }


def check_frequency(avg_per_day: float, current_count: int) -> dict:
    if avg_per_day <= 0:
        avg_per_day = 0.5
    ratio     = current_count / avg_per_day
    triggered = ratio >= 5 and current_count >= 5
    raw_score = min((ratio / 20) * 100, 100)
    contribution = round(raw_score * RULE_WEIGHTS["frequency"] / 100, 1)
    return {
        "triggered": triggered, "score": round(raw_score, 1),
        "weight": RULE_WEIGHTS["frequency"], "contribution": contribution,
        "ratio": round(ratio, 1),
        "detail": f"{current_count} txns today vs {avg_per_day:.1f}/day avg ({ratio:.1f}× spike)",
        "avg_per_day": avg_per_day, "current_count": current_count,
    }


def check_profile(monthly_income: float, txn_amount: float, profile_type: str) -> dict:
    if monthly_income <= 0:
        monthly_income = 1
    income_ratio = txn_amount / monthly_income
    triggered    = income_ratio >= 3
    raw_score    = min((income_ratio / 15) * 100, 100)
    contribution = round(raw_score * RULE_WEIGHTS["profile"] / 100, 1)
    return {
        "triggered": triggered, "score": round(raw_score, 1),
        "weight": RULE_WEIGHTS["profile"], "contribution": contribution,
        "income_ratio": round(income_ratio, 1),
        "detail": f"₹{txn_amount:,.0f} = {income_ratio:.1f}× declared monthly income ({profile_type})",
        "monthly_income": monthly_income, "txn_amount": txn_amount,
        "profile_type": profile_type,
    }


def check_structuring(near_threshold_count: int,
                       threshold: float = REPORTING_THRESHOLD) -> dict:
    triggered    = near_threshold_count >= 3
    raw_score    = min((near_threshold_count / 10) * 100, 100)
    contribution = round(raw_score * RULE_WEIGHTS["structuring"] / 100, 1)
    return {
        "triggered": triggered, "score": round(raw_score, 1),
        "weight": RULE_WEIGHTS["structuring"], "contribution": contribution,
        "count": near_threshold_count, "threshold": threshold,
        "detail": f"{near_threshold_count} near-threshold txns (below ₹{threshold:,.0f}) in 7 days",
    }


def compute_risk(inactive_days, txn_amount, avg_per_day, current_count,
                 monthly_income, profile_type, near_threshold_count) -> dict:
    r1 = check_dormant(inactive_days, txn_amount)
    r2 = check_frequency(avg_per_day, current_count)
    r3 = check_profile(monthly_income, txn_amount, profile_type)
    r4 = check_structuring(near_threshold_count)

    risk_score = round(min(
        r1["contribution"] + r2["contribution"] +
        r3["contribution"] + r4["contribution"], 100
    ), 1)

    triggered_rules = []
    if r1["triggered"]: triggered_rules.append("DORMANT_ACTIVATION")
    if r2["triggered"]: triggered_rules.append("FREQUENCY_SPIKE")
    if r3["triggered"]: triggered_rules.append("PROFILE_MISMATCH")
    if r4["triggered"]: triggered_rules.append("NEAR_THRESHOLD_STRUCTURING")

    label, color, icon = get_risk_label(risk_score)
    return {
        "risk_score": risk_score, "risk_level": label,
        "risk_color": color, "risk_icon": icon,
        "triggered_rules": triggered_rules,
        "rules": {
            "dormant":     r1, "frequency": r2,
            "profile":     r3, "structuring": r4,
        },
        "score_breakdown": {
            "Dormant Activation":         r1["contribution"],
            "Frequency Spike":            r2["contribution"],
            "Profile Mismatch":           r3["contribution"],
            "Near-Threshold Structuring": r4["contribution"],
        },
    }


# ══════════════════════════════════════════════════════════════════════
# GROQ / LLAMA 3.1 — SAR NARRATIVE
# ══════════════════════════════════════════════════════════════════════

GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an expert AML (Anti-Money Laundering) compliance analyst assistant.
Your task is to generate a formal, regulator-ready Suspicious Activity Report (SAR) narrative.

STRICT RULES:
- Base the narrative strictly on provided data only. Do NOT invent facts.
- Reference triggered detection rules by name.
- Remain neutral, factual, and non-discriminatory.
- Focus solely on financial behaviour and measurable risk indicators.
- Do not exaggerate risk beyond what the data supports.
- Be concise but thorough — suitable for regulatory submission.

OUTPUT FORMAT (use these exact section headers):
1. CUSTOMER PROFILE SUMMARY
2. TRANSACTION SUMMARY
3. TRIGGERED RISK INDICATORS
4. SUSPICION RATIONALE
5. CONCLUSION & RECOMMENDATION"""


def build_user_prompt(customer: dict, risk_result: dict,
                      txn_amount: float, near_threshold_count: int,
                      avg_per_day: float, current_count: int) -> str:
    rules    = risk_result["rules"]
    triggered = ", ".join(risk_result["triggered_rules"]) or "NONE"
    return f"""Generate a formal SAR narrative for the following case:

CUSTOMER INFORMATION:
- Name: {customer.get('name','')}
- Profile Type: {customer.get('profile_type','')}
- Declared Monthly Income: INR {float(customer.get('monthly_income',0)):,.0f}
- Account Status: {customer.get('account_status','')}
- KYC Risk Category: {customer.get('kyc_risk','')}
- Days Inactive: {customer.get('inactive_days',0)} days
- Account Number: {customer.get('account_number','')}

TRANSACTION DATA:
- High-Value Transaction Amount: INR {txn_amount:,.0f}
- Reporting Threshold: INR {REPORTING_THRESHOLD:,.0f}
- Historical Average Transactions/Day: {avg_per_day:.1f}
- Current Day Transaction Count: {current_count}
- Near-Threshold Transactions (Last 7 Days): {near_threshold_count}

RISK ASSESSMENT:
- Composite Risk Score: {risk_result['risk_score']}/100
- Risk Classification: {risk_result['risk_level']}
- Triggered Rules: {triggered}

RULE DETAILS:
1. Dormant Activation:          {rules['dormant']['detail']}    (Score: {rules['dormant']['contribution']}/30)
2. Frequency Spike:             {rules['frequency']['detail']}  (Score: {rules['frequency']['contribution']}/25)
3. Profile Mismatch:            {rules['profile']['detail']}    (Score: {rules['profile']['contribution']}/25)
4. Near-Threshold Structuring:  {rules['structuring']['detail']} (Score: {rules['structuring']['contribution']}/20)

Generate the SAR narrative now."""


def generate_sar_narrative(customer: dict, risk_result: dict,
                            txn_amount: float, near_threshold_count: int,
                            avg_per_day: float, current_count: int) -> tuple[str, str]:
    """
    Calls Groq API with Llama 3.1 70B to generate the SAR narrative.
    Returns (narrative_text, model_used).
    Raises on API error so caller can surface it.
    """
    from groq import Groq
    client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    prompt = build_user_prompt(customer, risk_result, txn_amount,
                                near_threshold_count, avg_per_day, current_count)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=1400,
        temperature=0.3,       # low temp = consistent, formal output
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )
    narrative = response.choices[0].message.content.strip()
    return narrative, GROQ_MODEL
