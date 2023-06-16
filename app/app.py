#!/usr/bin/python3
import os
from logging.config import dictConfig

import psycopg
from flask import flash
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from psycopg.rows import namedtuple_row
from psycopg_pool import ConnectionPool


# postgres://{user}:{password}@{hostname}:{port}/{database-name}
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://db:db@postgres/db")

pool = ConnectionPool(conninfo=DATABASE_URL)
# the pool starts connecting immediately.

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)s - %(funcName)20s(): %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

app = Flask(__name__)
log = app.logger


@app.route("/hello", methods=("GET",))
def hello():
    """Show the index page."""
    print("hello")
    return "Hello, world!"

@app.route("/", methods=("GET",))
@app.route("/accounts", methods=("GET",))
def account_index():
    """Show all the accounts, most recent first."""

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            accounts = cur.execute(
                """
                SELECT *
                FROM CUSTOMER;
                """,
                {},
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    # API-like response is returned to clients that request JSON explicitly (e.g., fetch)
    if (
        request.accept_mimetypes["application/json"]
        and not request.accept_mimetypes["text/html"]
    ):
        return jsonify(accounts)
    
    cust = []
    cust.append({"cust_no": 12, "name": "jose", "balance": 0})
    cust.append({"cust_no": 13, "name": "carlos", "balance": 0})
    cust.append({"cust_no": 14, "name": "Moedas", "balance": 69420})

    return render_template("customer/index.html", customers=cust)


@app.route("/products", methods=("GET", "POST"))
def product_index():

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            products = cur.execute(
                """
                SELECT *
                FROM PRODUCT;
                """,
                {},
            ).fetchall()


    return render_template("product/index.html", products=products)

@app.route("/product/add", methods=["GET"])
def add_product_page():

    # get all products?

    return render_template("product/add/index.html")

@app.route("/product/add", methods=["POST"])
def add_product():

    sku = request.form["SKU"]
    name = request.form["name"]
    price = request.form["price"]
    ean = request.form["EAN"]
    desc = request.form["description"]



    if not sku:
        return "Sku is required."
    elif len(sku) > 25:
        return "Sku is required to be at most 25 characters long."

    if not name:
        return "Name is required."
    elif len(name) > 200:
        return "Name is required to be at most 200 characters long."

    if not price:
        return "Price is required."
    else:
        price_split = price.replace(",",".").split(".")
    
        if len(price_split) > 2:
            return "Price is required to be numeric."
        elif len(price_split) == 2:
            if len(price_split[1])> 2:
                return "Price is required to be have at most 2 decimal places."
        for i in price_split:
            if not i.isnumeric():
                return "Price is required to be numeric."

    if ean:
        if not ean.isnumeric():
            return "Balance is required to be numeric."
        elif len(ean) != 13:
            return "EAN must be 13 digits long."
    else:
        ean = None

    if not desc:
        desc = None


   
    
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                INSERT INTO product (sku, name, description, price, ean)
                VALUES (%(sku)s, %(name)s, %(description)s, %(price)s, %(ean)s);
                """,
                {"sku": sku, "name": name, "description": desc, "price": price, "ean": ean},
            )
        conn.commit()
    return redirect(url_for("product_index"))


@app.route("/product/remove", methods=["GET"])
def remove_product_page():
    return render_template("product/remove/index.html")

@app.route("/product/remove", methods=["POST"])
def remove_product():
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE FROM contains
                WHERE sku = %(sku)s;
                """,
                {"sku": request.form["SKU"]}
            )

            cur.execute(
                """
                DELETE FROM delivery
                WHERE tin = 
                    (SELECT tin FROM supplier
                    WHERE sku = %(sku)s);
                """, {"sku": request.form["SKU"]})
            
            cur.execute(
                """
                DELETE FROM supplier
                WHERE sku = %(sku)s;
                """, {"sku": request.form["SKU"]})
            
            cur.execute(
                """
                 DELETE FROM product
                WHERE sku = %(sku)s;
                """, {"sku": request.form["SKU"]})
            
        conn.commit()

    return redirect(url_for("product_index"))

@app.route("/product/<product_number>/edit", methods=["GET"])
def product_edit_page(product_number):


    return render_template("product/edit/index.html", product_number=product_number)

@app.route("/product/<product_number>/edit", methods=["POST"])
def product_edit(product_number):
    try:
        price = request.form["price"]
    except:
        price = None
    try:
        desc = request.form["description"]
    except:
        desc = None

    if price:

        price_split = price.replace(",",".").split(".")
    
        if len(price_split) > 2:
            return "Price is required to be numeric."
        elif len(price_split) == 2:
            if len(price_split[1])> 2:
                return "Price is required to be have at most 2 decimal places."
        for i in price_split:
            if not i.isnumeric():
                return "Price is required to be numeric."

        
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    UPDATE product
                    SET price = %(price)s
                    WHERE sku = %(sku)s;
                    """,
                    {"sku": product_number, "price": price},
                )
            conn.commit()
    
    elif desc:
        if len(desc) > 200:
            return "Description is required to be at most 200 characters long."
        
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute(
                    """
                    UPDATE product
                    SET description = %(description)s
                    WHERE sku = %(sku)s;
                    """,
                    {"sku": product_number, "description": desc},
                )
            conn.commit()
    else:
        return "error: No changes made."
    
    return redirect(url_for("product_index"))



@app.route("/accounts/<account_number>/update", methods=("GET", "POST"))
def account_update(account_number):
    """Update the account balance."""

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            account = cur.execute(
                """
                SELECT account_number, branch_name, balance
                FROM account
                WHERE account_number = %(account_number)s;
                """,
                {"account_number": account_number},
            ).fetchone()
            log.debug(f"Found {cur.rowcount} rows.")

    if request.method == "POST":
        balance = request.form["balance"]

        error = None

        if not balance:
            error = "Balance is required."
            if not balance.isnumeric():
                error = "Balance is required to be numeric."

        if error is not None:
            flash(error)
        else:
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute(
                        """
                        UPDATE account
                        SET balance = %(balance)s
                        WHERE account_number = %(account_number)s;
                        """,
                        {"account_number": account_number, "balance": balance},
                    )
                conn.commit()
            return redirect(url_for("account_index"))

    return render_template("account/update.html", account=account)


@app.route("/accounts/<account_number>/delete", methods=("POST",))
def account_delete(account_number):
    """Delete the account."""

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                DELETE FROM account
                WHERE account_number = %(account_number)s;
                """,
                {"account_number": account_number},
            )
        conn.commit()
    return redirect(url_for("account_index"))


@app.route("/ping", methods=("GET",))
def ping():
    log.debug("ping!")
    return jsonify({"message": "pong!", "status": "success"})


if __name__ == "__main__":
    app.run()
