"""
CRYPTIX SAR — Demo Data Seeder
Run this once to populate the database with realistic demo cases.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, insert_customer, insert_transactions, create_sar, log_audit
from risk_engine import compute_risk, generate_demo_transactions
from datetime import datetime, timedelta
import random

CUSTOMERS = [
    {"name":"Rajesh Kumar Verma",  "profile_type":"Retail",    "monthly_income":45000,   "account_status":"Dormant",      "kyc_risk":"High",   "inactive_days":210, "account_number":"HDFC40829173"},
    {"name":"Sunita Rao",          "profile_type":"SME",       "monthly_income":120000,  "account_status":"Active",       "kyc_risk":"Medium", "inactive_days":12,  "account_number":"ICIC29187364"},
    {"name":"Amir Khan Siddiqui",  "profile_type":"HNI",       "monthly_income":500000,  "account_status":"Restricted",   "kyc_risk":"High",   "inactive_days":0,   "account_number":"AXIS10293847"},
    {"name":"Priya Sharma",        "profile_type":"Corporate", "monthly_income":300000,  "account_status":"Under Review", "kyc_risk":"Medium", "inactive_days":95,  "account_number":"SBI00192837"},
    {"name":"Vikram Singh",        "profile_type":"Retail",    "monthly_income":35000,   "account_status":"Active",       "kyc_risk":"Low",    "inactive_days":320, "account_number":"PNB91827364"},
    {"name":"Ananya Mehta",        "profile_type":"PEP",       "monthly_income":200000,  "account_status":"Active",       "kyc_risk":"High",   "inactive_days":5,   "account_number":"KOTAK8273641"},
]

CASES_CONFIG = [
    # (cust_idx, txn_amt, avg_pd, curr_cnt, near_thresh, decision, analyst)
    (0, 980000,  1.2, 17, 5, "APPROVED",     "Priya Sharma"),
    (1, 450000,  3.5, 22, 3, "APPROVED",     "Rahul Gupta"),
    (2, 1500000, 8.0, 41, 8, "OPEN",         "Anita Desai"),
    (3, 600000,  2.0, 14, 4, "UNDER REVIEW", "Priya Sharma"),
    (4, 750000,  0.5, 19, 6, "OPEN",         "Rahul Gupta"),
    (5, 2000000, 5.0, 35, 9, "APPROVED",     "Anita Desai"),
]

def seed():
    init_db()
    print("Seeding CRYPTIX demo data...")

    for i, cd in enumerate(CUSTOMERS):
        last_active = (datetime.now() - timedelta(days=cd["inactive_days"])).strftime("%Y-%m-%d")
        cd["last_active_date"] = last_active
        cid = insert_customer(cd)

        if i < len(CASES_CONFIG):
            ci = CASES_CONFIG[i]
            rr = compute_risk(cd["inactive_days"], ci[1], ci[2], ci[3], cd["monthly_income"], cd["profile_type"], ci[4])

            txns = generate_demo_transactions(cid, cd["inactive_days"], ci[1], ci[3], ci[4])
            insert_transactions(txns)

            sample_nar = f"""1. CUSTOMER PROFILE SUMMARY
{cd['name']} is a {cd['profile_type']} customer with declared monthly income of ₹{cd['monthly_income']:,}. KYC risk category: {cd['kyc_risk']}. Account inactive for {cd['inactive_days']} days prior to review period.

2. TRANSACTION SUMMARY
High-value transaction of ₹{ci[1]:,} detected. {ci[3]} transactions recorded on the review date against a historical baseline of {ci[2]:.1f}/day. {ci[4]} near-threshold transactions flagged in the preceding 7-day window.

3. TRIGGERED RISK INDICATORS
{chr(10).join(f'• {r}' for r in rr['triggered_rules'])}

4. SUSPICION RATIONALE
The combination of dormancy reactivation, velocity anomaly, and income profile mismatch creates a convergence of AML red flags consistent with layering behaviour under PMLA 2002.

5. CONCLUSION & RECOMMENDATION
Risk Score: {rr['risk_score']}/100 — {rr['risk_level']}. Recommend immediate account freeze and FIU-IND notification."""

            sid, case_num = create_sar({
                "customer_id": cid, "risk_score": rr["risk_score"],
                "risk_level": rr["risk_level"], "status": ci[5],
                "dormant_score":     rr["rules"]["dormant"]["contribution"],
                "frequency_score":   rr["rules"]["frequency"]["contribution"],
                "profile_score":     rr["rules"]["profile"]["contribution"],
                "structuring_score": rr["rules"]["structuring"]["contribution"],
                "triggered_rules": rr["triggered_rules"],
                "narrative": sample_nar,
                "created_by": ci[6], "assigned_to": ci[6],
            })
            log_audit(sid, cid, "CUSTOMER_CREATED", ci[6], "AML Analyst", f"Customer {cd['name']} onboarded")
            log_audit(sid, cid, "RISK_COMPUTED",    ci[6], "AML Analyst", f"Risk: {rr['risk_score']}/100 — {rr['risk_level']}", rules_matched=rr["triggered_rules"])
            log_audit(sid, cid, "NARRATIVE_GENERATED", "claude-sonnet-4-5-20250929", "AI Engine", f"SAR narrative drafted for {case_num}")
            if ci[5] == "APPROVED":
                log_audit(sid, cid, "SAR_APPROVED", ci[6], "AML Analyst", f"{case_num} approved and filed with FIU-IND")
            print(f"  ✓ {case_num} | {cd['name']} | Risk {rr['risk_score']:.0f}/100 | {ci[5]}")

    print("\n✅ Demo data seeded successfully! Run: streamlit run app.py")

if __name__ == "__main__":
    seed()
