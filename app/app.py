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
@app.route("/customers", defaults = {'page': 1}, methods=("GET",))
@app.route("/customers/<int:page>", methods=["GET"])
def customer_index(page = 1):
    """Show all the accounts, most recent first."""
    display_limit = 2 #CONSTANT

    if page == 0:
        page = 1
    offset = (page - 1) * display_limit

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            customers = cur.execute(
                """
                SELECT *
                FROM CUSTOMER
                LIMIT %(display_limit)s OFFSET %(offset)s;
                """,
                {"display_limit": display_limit, "offset": offset},
            ).fetchall()
            max_obj = cur.rowcount + offset
    
    return render_template("customer/index.html", customers=customers, page=page, display_limit = display_limit, max_obj = max_obj)

@app.route("/products", defaults = {'page': 1}, methods=("GET", "POST"))
@app.route("/products", methods=("GET", "POST"))
def product_index(page = 1):

    display_limit = 10 #CONSTANT

    if page == 0:
        page = 1
    offset = (page - 1) * display_limit

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            products = cur.execute(
                """
                SELECT *
                FROM PRODUCT
                LIMIT %(display_limit)s OFFSET %(offset)s;
                """,
                {"display_limit": display_limit, "offset": offset},
            ).fetchall()
            max_obj = cur.rowcount + offset

    return render_template("product/index.html", products=products, page=page, display_limit = display_limit, max_obj = max_obj)

@app.route("/customer/add", methods=["GET"])
def add_customer_page():

    return render_template("customer/add/index.html")

@app.route("/customer/add", methods=["POST"])
def add_customer():

    cust_no = request.form["cust_no"]
    name = request.form["name"]
    address = request.form["address"]
    phone = request.form["phone"]
    email = request.form["email"]

    if not cust_no:
        return "Customer number is required."
    if not cust_no.isnumeric():
        return "Customer number is required to be numeric."
    
    if not name:
        return "Name is required."
    elif len(name) > 80:
        return "Name is required to be at most 80 characters long."
    elif not name.isalpha():
        return "Name is required to be alphabetic."
    
    if not email:
        return "Email is required."
    elif len(email) > 254:
        return "Email is required to be at most 254 characters long."
    
    if address:
        if len(address) > 255:
            return "Address is required to be at most 255 characters long."
    else:
        address = None
    
    if phone:
        if len(phone) > 15:
            return "Phone is required to be at most 20 characters long."
        if not phone.isnumeric():
            return "Phone is required to be numeric."
    else:
        phone = None
        
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                INSERT INTO customer (cust_no, name, email, phone, address)
                VALUES (%(cust_no)s, %(name)s, %(email)s, %(phone)s, %(address)s);
                """,
                {"cust_no": cust_no, "name": name, "email": email, "phone": phone, "address": address},
            )
        conn.commit()


    return redirect(url_for("customer_index"))


@app.route("/customer/remove", methods=["GET"])
def remove_customer_page():

    # get all products?

    return render_template("customer/remove/index.html")

@app.route("/customer/remove", methods=["POST"])
def remove_customer():
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            # delete from pay
            cur.execute(
                """
                DELETE FROM pay
                WHERE cust_no = %(cust_no)s;
                """,
                {"cust_no": request.form["cust_no"]}
            )
            
            #delete orders from contains
            cur.execute(
                """
                DELETE FROM contains
                WHERE order_no IN (
                    SELECT order_no
                    FROM orders
                    WHERE cust_no = %(cust_no)s
                );
                """, {"cust_no": request.form["cust_no"]})
            
            # delete orders from process
            cur.execute(
                """
                DELETE FROM process
                WHERE order_no IN (
                    SELECT order_no
                    FROM orders
                    WHERE cust_no = %(cust_no)s
                );
                """, {"cust_no": request.form["cust_no"]})
            
            cur.execute(
                """
                DELETE FROM orders
                WHERE cust_no = %(cust_no)s;
                """,
                {"cust_no": request.form["cust_no"]})


            cur.execute(
                """
                DELETE FROM customer
                WHERE cust_no = %(cust_no)s;
                """,
                {"cust_no": request.form["cust_no"]}
            )
        conn.commit()

    return redirect(url_for("customer_index"))



@app.route("/product/add", methods=["GET"])
def add_product_page():

    # get all products?

    return render_template("product/add/index.html")



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




@app.route("/product/order/<sku>", methods=["GET"])
def order_product_page(sku):
    return render_template("product/order/add/index.html", sku=sku)

@app.route("/product/order/<sku>", methods=["POST"])
def order_product(sku):
    qty = request.form["qty"]
    cust_no = request.form["cust_no"]
    if not qty:
        return "Quantity is required."
    if not qty.isnumeric():
        return "Quantity is required to be numeric."
    if not cust_no:
        return "Customer number is required."
    if not cust_no.isnumeric():
        return "Customer number is required to be numeric."
    

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            last_order_no = cur.execute(
                """
                SELECT MAX(order_no) AS last_order_no
                FROM orders;
                """).fetchone()[0]

            if last_order_no is None:
                last_order_no = 0

            cust_no_in_bd = cur.execute(
                """
                SELECT cust_no 
                FROM customer
                WHERE cust_no = %(cust_no)s;
                """,
                {"cust_no": cust_no},
                ).fetchone()

            if not cust_no_in_bd:
                return "O cliente introduzido não existe."
            
            cust_no_in_bd = cust_no_in_bd[0]
            

            cur.execute(
                """
                INSERT INTO orders (order_no, cust_no, date)
                VALUES (%(order_no)s, %(cust_no)s, CURRENT_DATE);
                """,
                {"order_no": last_order_no + 1, "cust_no": cust_no}
            )
            cur.execute(
                """
                INSERT INTO contains (order_no, SKU, qty)
                VALUES (%(order_no)s, %(SKU)s, %(qty)s);
                """,
                {"order_no": last_order_no + 1, "SKU": sku, "qty": qty}
            )
        conn.commit()

    return redirect(url_for("pay_order_page", cust_no=cust_no, order_no=last_order_no + 1))   


@app.route("/pay/<order_no>/<cust_no>", methods=["GET"])
def pay_order_page(order_no, cust_no):
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
                total_price = cur.execute(
                    """
                    SELECT p.price * c.qty AS total_price
                    FROM contains AS c, product AS p
                    WHERE c.order_no = %(order_no)s AND c.sku = p.sku;
                    """, {"order_no": order_no},
                    ).fetchone()[0]
                cust_name = cur.execute(
                    """
                    SELECT name 
                    FROM customer 
                    WHERE cust_no = %(cust_no)s;
                    """, {"cust_no": cust_no},
                    ).fetchone()[0]
                 
    return render_template("/pay/pay_order.html", cust_name=cust_name, order_no=order_no, total_price=total_price, cust_no=cust_no)


@app.route("/pay/<order_no>/<cust_no>", methods=["POST"])
def pay_order(order_no, cust_no):
    if not order_no:
        return "error: No such order."
    if not cust_no:
        return "error: No such customer."
    if not order_no.isnumeric():
        return "error: Order is invalid"
    if not cust_no.isnumeric():
        return "Customer number is invalid."
    
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cust_no_in_bd = cur.execute(
                """
                SELECT cust_no 
                FROM customer
                WHERE cust_no = %(cust_no)s;
                """,
                {"cust_no": cust_no},
                ).fetchone()

            if not cust_no_in_bd:
                return "O cliente introduzido não existe."
            

            order_no_in_bd = cur.execute(
                """
                SELECT order_no  
                FROM orders 
                WHERE order_no = %(order_no)s;
                """,
                {"order_no": order_no},
                ).fetchone()

            if not order_no_in_bd:
                return "A encomenda introduzida não existe."
            

            order_no_in_pay = cur.execute(
                """
                SELECT order_no
                FROM pay
                WHERE order_no = %(order_no)s;
                """,
                {"order_no": order_no},
                ).fetchone()

            if order_no_in_pay:
                return "A encomenda já foi paga."

            cur.execute(
                """
                INSERT INTO pay (order_no, cust_no)
                VALUES (%(order_no)s, %(cust_no)s);
                """,
                {"order_no": order_no, "cust_no": cust_no}
            )
        conn.commit()

    return redirect(url_for("product_index"))       




@app.route("/ping", methods=("GET",))
def ping():
    log.debug("ping!")
    return jsonify({"message": "pong!", "status": "success"})


if __name__ == "__main__":
    app.run()


