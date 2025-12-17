#!/usr/bin/env python3
"""Clean user data from database while preserving templates"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/metrics.db")

def clean_database():
    """Remove all user data but keep category templates"""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Delete all logged metrics
        cursor.execute("DELETE FROM metrics")
        metrics_deleted = cursor.rowcount
        print(f"Deleted {metrics_deleted} logged metrics")

        # Delete all metric definitions
        cursor.execute("DELETE FROM metric_definitions")
        metric_defs_deleted = cursor.rowcount
        print(f"Deleted {metric_defs_deleted} metric definitions")

        # Delete all categories (including templates)
        cursor.execute("DELETE FROM categories")
        categories_deleted = cursor.rowcount
        print(f"Deleted {categories_deleted} categories")

        conn.commit()
        print("\n✓ Database cleaned successfully!")
        print("Starting with a completely fresh database.")

    except Exception as e:
        conn.rollback()
        print(f"Error cleaning database: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    clean_database()
