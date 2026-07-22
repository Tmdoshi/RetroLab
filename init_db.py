"""
init_db.py
Creates the SQLite database and schema for Retro Lab, a retro gaming
hardware marketplace. Run this once before starting the Flask app,
and again any time you want to reset the database to sample data.
"""

import sqlite3

DB_NAME = "retrolab.db"


def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Main table: listings for retro gaming hardware
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            condition TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            seller_name TEXT NOT NULL,
            date_added TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Clear existing rows so re-running this script gives a clean, known state
    cursor.execute("DELETE FROM listings")

    sample_listings = [
        ("Sega Genesis Model 1 Console", "Console", "Good", 85.00,
         "Includes two 3-button controllers and power cable. Tested and working.",
         "RetroRick"),
        ("Nintendo Game Boy Color - Purple", "Handheld", "Fair", 45.00,
         "Screen has minor scratches but fully playable. Includes 2 AA battery cover.",
         "PixelPam"),
        ("Commodore 64 with Datasette", "Computer", "Excellent", 220.00,
         "Fully restored, recapped motherboard. Comes with datasette and 5 game tapes.",
         "VintageVault"),
        ("Atari 2600 Joystick (CX40)", "Accessory", "Good", 15.00,
         "Standard CX40 joystick, minor yellowing, works perfectly.",
         "RetroRick"),
        ("Super Nintendo (PAL) Bundle", "Console", "Very Good", 130.00,
         "Includes Super Mario World cartridge and one controller.",
         "8BitBazaar"),
    ]

    cursor.executemany("""
        INSERT INTO listings (title, category, condition, price, description, seller_name)
        VALUES (?, ?, ?, ?, ?, ?)
    """, sample_listings)

    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' created with {len(sample_listings)} sample listings.")


if __name__ == "__main__":
    create_database()
