"""
CRYPTIX SAR - Database Layer (SQLite for demo, swappable to PostgreSQL)
"""
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "cryptix_sar.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Customers table
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            profile_type TEXT,
            monthly_income REAL,
            account_status TEXT,
            kyc_risk TEXT,
            last_active_date TEXT,
            inactive_days INTEGER,
            account_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Transactions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            customer_id TEXT,
            amount REAL,
            txn_type TEXT,
            counterparty TEXT,
            channel TEXT,
            txn_date TEXT,
            is_flagged INTEGER DEFAULT 0,
            flag_reason TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    # SAR cases table
    c.execute("""
        CREATE TABLE IF NOT EXISTS sar_cases (
            id TEXT PRIMARY KEY,
            customer_id TEXT,
            case_number TEXT UNIQUE,
            status TEXT DEFAULT 'OPEN',
            risk_score REAL,
            risk_level TEXT,
            dormant_score REAL DEFAULT 0,
            frequency_score REAL DEFAULT 0,
            profile_score REAL DEFAULT 0,
            structuring_score REAL DEFAULT 0,
            triggered_rules TEXT,
            narrative TEXT,
            analyst_notes TEXT,
            created_by TEXT,
            assigned_to TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    # Audit trail table
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_trail (
            id TEXT PRIMARY KEY,
            case_id TEXT,
            customer_id TEXT,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            actor_role TEXT,
            detail TEXT,
            data_points TEXT,
            rules_matched TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ── Customer CRUD ──────────────────────────────────────
def insert_customer(data: dict) -> str:
    cid = str(uuid.uuid4())[:8].upper()
    conn = get_connection()
    conn.execute("""
        INSERT INTO customers (id,name,profile_type,monthly_income,account_status,
        kyc_risk,last_active_date,inactive_days,account_number)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (cid, data["name"], data["profile_type"], data["monthly_income"],
          data["account_status"], data["kyc_risk"], data["last_active_date"],
          data["inactive_days"], data["account_number"]))
    conn.commit(); conn.close()
    return cid


def get_customer(cid: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_customers() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM customers ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Transaction CRUD ───────────────────────────────────
def insert_transactions(txns: list):
    conn = get_connection()
    for t in txns:
        conn.execute("""
            INSERT OR IGNORE INTO transactions
            (id,customer_id,amount,txn_type,counterparty,channel,txn_date,is_flagged,flag_reason)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (t["id"], t["customer_id"], t["amount"], t["txn_type"],
              t["counterparty"], t["channel"], t["txn_date"],
              t.get("is_flagged", 0), t.get("flag_reason", "")))
    conn.commit(); conn.close()


def get_transactions(customer_id: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE customer_id=? ORDER BY txn_date DESC",
        (customer_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── SAR CRUD ───────────────────────────────────────────
def create_sar(data: dict) -> str:
    sid = str(uuid.uuid4())[:8].upper()
    case_num = f"CRYPTIX-SAR-{datetime.now().strftime('%Y%m')}-{sid}"
    conn = get_connection()
    conn.execute("""
        INSERT INTO sar_cases (id,customer_id,case_number,status,risk_score,risk_level,
        dormant_score,frequency_score,profile_score,structuring_score,
        triggered_rules,narrative,created_by,assigned_to)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (sid, data["customer_id"], case_num, data.get("status","OPEN"),
          data["risk_score"], data["risk_level"],
          data.get("dormant_score",0), data.get("frequency_score",0),
          data.get("profile_score",0), data.get("structuring_score",0),
          json.dumps(data.get("triggered_rules",[])),
          data.get("narrative",""), data.get("created_by","System"),
          data.get("assigned_to","Unassigned")))
    conn.commit(); conn.close()
    return sid, case_num


def update_sar(sid: str, updates: dict):
    conn = get_connection()
    updates["updated_at"] = datetime.now().isoformat()
    fields = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [sid]
    conn.execute(f"UPDATE sar_cases SET {fields} WHERE id=?", vals)
    conn.commit(); conn.close()


def get_sar(sid: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM sar_cases WHERE id=?", (sid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_sars() -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.*, c.name as customer_name, c.account_number
        FROM sar_cases s LEFT JOIN customers c ON s.customer_id=c.id
        ORDER BY s.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Audit Trail ────────────────────────────────────────
def log_audit(case_id: str, customer_id: str, action: str, actor: str,
              actor_role: str, detail: str, data_points: dict = None,
              rules_matched: list = None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO audit_trail
        (id,case_id,customer_id,action,actor,actor_role,detail,data_points,rules_matched)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (str(uuid.uuid4())[:8].upper(), case_id, customer_id, action, actor,
          actor_role, detail,
          json.dumps(data_points or {}),
          json.dumps(rules_matched or [])))
    conn.commit(); conn.close()


def get_audit_trail(case_id: str = None, customer_id: str = None) -> list:
    conn = get_connection()
    if case_id:
        rows = conn.execute(
            "SELECT * FROM audit_trail WHERE case_id=? ORDER BY timestamp DESC",
            (case_id,)).fetchall()
    elif customer_id:
        rows = conn.execute(
            "SELECT * FROM audit_trail WHERE customer_id=? ORDER BY timestamp DESC",
            (customer_id,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM audit_trail ORDER BY timestamp DESC LIMIT 100"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dashboard_stats() -> dict:
    conn = get_connection()
    total_cases  = conn.execute("SELECT COUNT(*) FROM sar_cases").fetchone()[0]
    open_cases   = conn.execute("SELECT COUNT(*) FROM sar_cases WHERE status='OPEN'").fetchone()[0]
    approved     = conn.execute("SELECT COUNT(*) FROM sar_cases WHERE status='APPROVED'").fetchone()[0]
    customers    = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    audit_count  = conn.execute("SELECT COUNT(*) FROM audit_trail").fetchone()[0]

    monthly = conn.execute("""
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as cnt
        FROM sar_cases GROUP BY month ORDER BY month DESC LIMIT 6
    """).fetchall()

    by_risk = conn.execute("""
        SELECT risk_level, COUNT(*) as cnt FROM sar_cases GROUP BY risk_level
    """).fetchall()

    by_status = conn.execute("""
        SELECT status, COUNT(*) as cnt FROM sar_cases GROUP BY status
    """).fetchall()

    conn.close()
    return {
        "total_cases": total_cases,
        "open_cases": open_cases,
        "approved": approved,
        "customers": customers,
        "audit_count": audit_count,
        "monthly": [dict(r) for r in monthly],
        "by_risk": [dict(r) for r in by_risk],
        "by_status": [dict(r) for r in by_status],
    }
