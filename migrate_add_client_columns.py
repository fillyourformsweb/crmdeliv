"""
Migration script: Add ALL missing columns to clients, receivers, and client_addresses tables.
Run once with: python migrate_add_client_columns.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'crm_delivery.db')

MIGRATIONS = {
    "clients": [
        ("company_name",       "TEXT"),
        ("email",              "TEXT"),
        ("phone",              "TEXT"),
        ("address",            "TEXT"),
        ("landmark",           "TEXT"),
        ("city",               "TEXT"),
        ("state",              "TEXT"),
        ("pincode",            "TEXT"),
        ("alt_address",        "TEXT"),
        ("alt_landmark",       "TEXT"),
        ("alt_phone",          "TEXT"),
        ("alt_email",          "TEXT"),
        ("gst_number",         "TEXT"),
        ("billing_pattern_id", "INTEGER"),
        ("bill_pattern",       "TEXT"),
        ("billing_date",       "INTEGER"),
        ("is_active",          "INTEGER DEFAULT 1"),
        ("created_at",         "DATETIME"),
        ("updated_at",         "DATETIME"),
    ],
    "receivers": [
        ("landmark",     "TEXT"),
        ("alt_address",  "TEXT"),
        ("city",         "TEXT"),
        ("state",        "TEXT"),
        ("pincode",      "TEXT"),
        ("gst_number",   "TEXT"),
        ("bill_pattern", "TEXT"),
    ],
    "client_addresses": [
        ("landmark",      "TEXT"),
        ("address_label", "TEXT DEFAULT 'Primary'"),
        ("city",          "TEXT"),
        ("state",         "TEXT"),
        ("pincode",       "TEXT"),
    ],
}


def get_existing_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for table, columns in MIGRATIONS.items():
        existing = get_existing_columns(cursor, table)
        print(f"\n[{table}] existing columns: {existing}")
        for col_name, col_type in columns:
            if col_name not in existing:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                print(f"  + Added: {col_name} ({col_type})")
            else:
                print(f"  - Skipped (exists): {col_name}")

    conn.commit()
    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    main()
