"""
app.py
Retro Lab - a marketplace for buying and selling retro gaming hardware.
Flask + SQLite. See init_db.py for the database schema.
"""

import os
from flask import Flask, render_template, request, redirect, url_for

import sqlite3

app = Flask(__name__)

# Absolute path so this works correctly whether run locally or under
# Apache/WSGI (which uses a different working directory than a manual
# `flask run` from inside the project folder).
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retrolab.db")


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


@app.route("/")
def index():
    """Show all listings, optionally filtered by category (?category=)
    and/or searched by title (?q=)."""
    category = request.args.get("category")
    query = request.args.get("q", "").strip()
    conn = get_db_connection()

    sql = "SELECT * FROM listings WHERE 1=1"
    params = []

    if category and category != "All":
        sql += " AND category = ?"
        params.append(category)

    if query:
        sql += " AND title LIKE ?"
        params.append(f"%{query}%")

    sql += " ORDER BY date_added DESC"

    listings = conn.execute(sql, params).fetchall()

    categories = conn.execute(
        "SELECT DISTINCT category FROM listings ORDER BY category"
    ).fetchall()
    conn.close()

    return render_template(
        "index.html",
        listings=listings,
        categories=[c["category"] for c in categories],
        selected_category=category or "All",
        search_query=query
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


@app.route("/listing/<int:listing_id>/edit", methods=["GET", "POST"])
def edit_listing(listing_id):
    """Edit an existing listing's details."""
    conn = get_db_connection()
    listing = conn.execute(
        "SELECT * FROM listings WHERE id = ?", (listing_id,)
    ).fetchone()

    if listing is None:
        conn.close()
        return "Listing not found", 404

    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        condition = request.form["condition"]
        price = request.form["price"]
        description = request.form["description"]
        seller_name = request.form["seller_name"]

        conn.execute("""
            UPDATE listings
            SET title = ?, category = ?, condition = ?, price = ?,
                description = ?, seller_name = ?
            WHERE id = ?
        """, (title, category, condition, price, description, seller_name, listing_id))
        conn.commit()
        conn.close()

        return redirect(url_for("listing_detail", listing_id=listing_id))

    conn.close()
    return render_template("edit.html", listing=listing)


@app.route("/listing/<int:listing_id>/delete", methods=["POST"])
def delete_listing(listing_id):
    """Delete a listing from the marketplace."""
    conn = get_db_connection()
    conn.execute("DELETE FROM listings WHERE id = ?", (listing_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("index"))


if __name__ == "__main__":
    # debug=True is for local testing only - turn this off in production (Apache/WSGI)
    app.run(debug=True, host="0.0.0.0", port=5000)
