# 🔐 CRYPTIX SAR Intelligence Platform
### Hackathon Demo — Team CRYPTIX

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Claude API key
export ANTHROPIC_API_KEY=your_key_here

# 3. Seed demo data (optional but recommended for presentation)
python seed_demo.py

# 4. Launch the app
streamlit run app.py
```

---

## 🏗️ Architecture

```
cryptix_sar/
├── app.py           ← Streamlit frontend (all UI pages)
├── risk_engine.py   ← AML rules engine + scoring logic
├── database.py      ← SQLite backend (drop-in for PostgreSQL)
├── seed_demo.py     ← Populates 6 realistic demo cases
├── requirements.txt
└── cryptix_sar.db   ← Auto-created on first run
```

**Stack:**
- **Frontend:** Streamlit + Plotly
- **Backend:** Python (risk_engine.py)
- **Database:** SQLite (swap connection string for PostgreSQL)
- **LLM:** Anthropic Claude via API
- **Charts:** Plotly (interactive)

---

## ⚠️ 4 AML Detection Rules

| Rule | Trigger | Weight |
|------|---------|--------|
| **Dormant Activation** | Account inactive >90 days + high-value txn | 30/100 |
| **Frequency Spike** | Today's txn count >5× historical avg | 25/100 |
| **Profile Mismatch** | Transaction >3× monthly declared income | 25/100 |
| **Near-Threshold Structuring** | ≥3 txns just below reporting limit in 7 days | 20/100 |

---

## 📊 Risk Classification (Banking-Grade)

| Score | Classification |
|-------|---------------|
| 80–100 | 🔴 **IMMEDIATE ACTION REQUIRED** |
| 60–79  | 🟠 **ESCALATE FOR REVIEW** |
| 40–59  | 🟡 **ENHANCED DUE DILIGENCE** |
| 20–39  | 🟢 **STANDARD MONITORING** |
| 0–19   | 🔵 **ROUTINE SURVEILLANCE** |

---

## 📋 Features

- ✅ 4 AML detection rules with weighted risk scoring
- ✅ Claude AI SAR narrative generation (5-section format)
- ✅ Interactive risk radar + breakdown bar charts
- ✅ Complete SQLite audit trail with integrity hash
- ✅ Human analyst edit + approve/reject workflow
- ✅ Dashboard with case analytics & trends
- ✅ Case registry with search/filter
- ✅ Demo data seeder for presentations
- ✅ CRYPTIX dark theme UI

---

## 🎯 Regulatory Alignment

- PMLA 2002 (India)
- FIU-IND reporting standards
- FATF Recommendation R.20
- RBI KYC Master Direction 2016

---

*Team CRYPTIX — AML Hackathon 2025*
