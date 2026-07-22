"""
app.py
Retro Lab - a marketplace for buying and selling retro gaming hardware.
Flask + SQLite. See init_db.py for the database schema.
"""

from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)
DB_NAME = "retrolab.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


@app.route("/")
def index():
    """Show all listings, optionally filtered by category via ?category=."""
    category = request.args.get("category")
    conn = get_db_connection()

    if category and category != "All":
        listings = conn.execute(
            "SELECT * FROM listings WHERE category = ? ORDER BY date_added DESC",
            (category,)
        ).fetchall()
    else:
        listings = conn.execute(
            "SELECT * FROM listings ORDER BY date_added DESC"
        ).fetchall()

    categories = conn.execute(
        "SELECT DISTINCT category FROM listings ORDER BY category"
    ).fetchall()
    conn.close()

    return render_template(
        "index.html",
        listings=listings,
        categories=[c["category"] for c in categories],
        selected_category=category or "All"
    )


@app.route("/listing/<int:listing_id>")
def listing_detail(listing_id):
    """Show a single listing in full detail."""
    conn = get_db_connection()
    listing = conn.execute(
        "SELECT * FROM listings WHERE id = ?", (listing_id,)
    ).fetchone()
    conn.close()

    if listing is None:
        return "Listing not found", 404

    return render_template("listing.html", listing=listing)


@app.route("/add", methods=["GET", "POST"])
def add_listing():
    """Form to add a new listing to the marketplace."""
    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        condition = request.form["condition"]
        price = request.form["price"]
        description = request.form["description"]
        seller_name = request.form["seller_name"]

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO listings (title, category, condition, price, description, seller_name)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, category, condition, price, description, seller_name))
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template("add.html")


if __name__ == "__main__":
    # debug=True is for local testing only - turn this off in production (Apache/WSGI)
    app.run(debug=True, host="0.0.0.0", port=5000)
