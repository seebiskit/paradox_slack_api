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

        # Delete metric definitions for non-template categories
        cursor.execute("""
            DELETE FROM metric_definitions
            WHERE category_id IN (
                SELECT id FROM categories WHERE is_template = FALSE
            )
        """)
        metric_defs_deleted = cursor.rowcount
        print(f"Deleted {metric_defs_deleted} metric definitions for user categories")

        # Delete non-template categories
        cursor.execute("DELETE FROM categories WHERE is_template = FALSE")
        categories_deleted = cursor.rowcount
        print(f"Deleted {categories_deleted} user-created categories")

        conn.commit()
        print("\n✓ Database cleaned successfully!")
        print("Templates preserved and ready for use.")

    except Exception as e:
        conn.rollback()
        print(f"Error cleaning database: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    clean_database()
