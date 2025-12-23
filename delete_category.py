#!/usr/bin/env python3
"""Delete a category and all its associated metrics from the database"""

import sqlite3
import argparse
from pathlib import Path

DB_PATH = Path("data/metrics.db")

def delete_category(category_name: str, confirm: bool = False):
    """Delete a category and all its associated data"""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # First, find the category
        cursor.execute("SELECT * FROM categories WHERE name = ?", (category_name,))
        category = cursor.fetchone()

        if not category:
            print(f"Category '{category_name}' not found in database")
            return False

        category_id = category['id']
        is_template = category['is_template']

        # Show what will be deleted
        cursor.execute("SELECT COUNT(*) as count FROM metrics WHERE category_id = ?", (category_id,))
        metrics_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM metric_definitions WHERE category_id = ?", (category_id,))
        metric_defs_count = cursor.fetchone()['count']

        print(f"\nCategory: {category['name']} (ID: {category_id})")
        print(f"Type: {'Template' if is_template else 'User Category'}")
        print(f"Icon: {category['icon']}")
        print(f"Metric definitions: {metric_defs_count}")
        print(f"Logged metrics: {metrics_count}")

        # Ask for confirmation if not provided
        if not confirm:
            response = input(f"\nAre you sure you want to delete this category and all its data? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Deletion cancelled")
                return False

        # Delete in order: metrics -> metric_definitions -> category
        cursor.execute("DELETE FROM metrics WHERE category_id = ?", (category_id,))
        metrics_deleted = cursor.rowcount
        print(f"\nDeleted {metrics_deleted} logged metrics")

        cursor.execute("DELETE FROM metric_definitions WHERE category_id = ?", (category_id,))
        metric_defs_deleted = cursor.rowcount
        print(f"Deleted {metric_defs_deleted} metric definitions")

        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        print(f"Deleted category '{category_name}'")

        conn.commit()
        print(f"\n✓ Category '{category_name}' and all associated data deleted successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error deleting category: {e}")
        return False
    finally:
        conn.close()

def list_categories():
    """List all categories in the database"""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT c.*,
                   COUNT(DISTINCT md.id) as metric_def_count,
                   COUNT(DISTINCT m.id) as metrics_count
            FROM categories c
            LEFT JOIN metric_definitions md ON c.id = md.category_id
            LEFT JOIN metrics m ON c.id = m.category_id
            GROUP BY c.id
            ORDER BY c.is_template DESC, c.name
        """)

        categories = cursor.fetchall()

        if not categories:
            print("No categories found in database")
            return

        print("\nCategories in database:")
        print("-" * 80)

        current_type = None
        for cat in categories:
            cat_type = "Template" if cat['is_template'] else "User Category"
            if cat_type != current_type:
                print(f"\n{cat_type}s:")
                current_type = cat_type

            print(f"  {cat['icon']} {cat['name']}")
            print(f"     Metrics: {cat['metric_def_count']} definitions, {cat['metrics_count']} logged entries")

        print("-" * 80)

    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete a category and all its associated metrics")
    parser.add_argument("-n", "--name", type=str, help="Name of the category to delete")
    parser.add_argument("-l", "--list", action="store_true", help="List all categories")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    if args.list:
        list_categories()
    elif args.name:
        delete_category(args.name, confirm=args.yes)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python3 delete_category.py -l                    # List all categories")
        print("  python3 delete_category.py -n 'Sunday Service'   # Delete category interactively")
        print("  python3 delete_category.py -n 'Sunday Service' -y  # Delete without confirmation")
