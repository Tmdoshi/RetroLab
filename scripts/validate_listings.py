"""
validate_listings.py

This script checks the Retro Lab SQLite database for common data-quality
problems: duplicate listing titles, non-positive prices, and missing
required fields. It prints a summary report to the terminal so the
results can be independently verified by re-running the script against
the live database at any time.

Usage:
    python3 validate_listings.py
"""

import sqlite3
import sys
import os

DB_NAME = os.path.join(os.path.dirname(__file__), "..", "retrolab.db")


def validate():
    if not os.path.exists(DB_NAME):
        print(f"Error: database not found at {DB_NAME}")
        sys.exit(1)

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    issues_found = 0

    # Check 1: duplicate titles
    cursor.execute("""
        SELECT title, COUNT(*) as count
        FROM listings
        GROUP BY title
        HAVING count > 1
    """)
    duplicates = cursor.fetchall()
    if duplicates:
        print("DUPLICATE LISTINGS FOUND:")
        for row in duplicates:
            print(f"  - '{row['title']}' appears {row['count']} times")
        issues_found += len(duplicates)
    else:
        print("No duplicate listing titles found.")

    # Check 2: non-positive or missing prices
    cursor.execute("SELECT id, title, price FROM listings WHERE price IS NULL OR price <= 0")
    bad_prices = cursor.fetchall()
    if bad_prices:
        print("\nLISTINGS WITH INVALID PRICES:")
        for row in bad_prices:
            print(f"  - id {row['id']}: '{row['title']}' has price {row['price']}")
        issues_found += len(bad_prices)
    else:
        print("All listings have valid (positive) prices.")

    # Check 3: missing required text fields
    cursor.execute("""
        SELECT id, title FROM listings
        WHERE seller_name IS NULL OR seller_name = ''
           OR category IS NULL OR category = ''
    """)
    incomplete = cursor.fetchall()
    if incomplete:
        print("\nLISTINGS MISSING REQUIRED FIELDS:")
        for row in incomplete:
            print(f"  - id {row['id']}: '{row['title']}'")
        issues_found += len(incomplete)
    else:
        print("All listings have required fields populated.")

    total = cursor.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    print(f"\nChecked {total} listings. {issues_found} issue(s) found.")

    conn.close()


if __name__ == "__main__":
    validate()
