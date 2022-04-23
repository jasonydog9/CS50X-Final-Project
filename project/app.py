import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///crypto.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    Count = db.execute("SELECT COUNT(username) FROM users")
    cash = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])[0]["cash"] # Selects cash from a user
    portfolio = db.execute("SELECT stock, quantity FROM portfolio WHERE userid=:userid", userid=session["user_id"]) #Selects a persons stocks and quantity from their portfolio
    netWorth = cash

    for quote in portfolio:
        stock = lookup(quote["stock"]) #Looksup specific stock
        cost = stock["price"] #Takes price of specific stock
        totalCost = cost * quote["quantity"] # Multiplies
        quote.update({'price': cost, 'total': totalCost}) #Updates values, help from a friend
        netWorth += totalCost

    net_worth = db.execute("SELECT net_worth FROM users WHERE id=:id", id=session["user_id"])

    if not net_worth:  # if there is no quantity of a stock add quantity.
        db.execute("INSERT INTO users (net_worth, id) VALUES (:net_worth, :id)", # help from a friend
                        net_worth=netWorth, id=session["user_id"])

    if net_worth:
        db.execute("UPDATE users SET net_worth=:net_worth WHERE id=:id", net_worth=netWorth, id=session["user_id"])

    return render_template("index.html", cash=cash, portfolio=portfolio, netWorth=netWorth, count = Count)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("Stock symbol not provided.")

        if not request.form.get("shares"):
            return apology("Quantity not provided.")

        shares = request.form.get("shares")  # took three days to fix :), I used this tool https://docs.python.org/3/library/stdtypes.html#str.isdigit
        if not shares.isdigit():
            return apology("Must enter positive integer quantity.")
        if shares.isalpha():
            return apology("Must enter positive integer quantity.")

        quote = lookup(request.form.get("symbol"))

        if quote == None:
            return apology("Please provide valid stock symbol.")

        cost = quote['price'] * int(request.form.get("shares"))
        cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])

        if (cash[0]["cash"] < cost):
            return apology("Not enough money.")

        db.execute("INSERT INTO purchases (userid, stock, price, quantity, BuyorSell) VALUES (:userid, :stock, :price, :quantity, :BuyorSell)",  # Creates a transaction with all values, help from a friend
                   userid=session["user_id"], stock=quote["symbol"], price=quote["price"], quantity=shares, BuyorSell="Buy")

        db.execute("UPDATE users SET cash=cash-:cash WHERE id=:id", cash=cost, id=session["user_id"])

        portfolio = db.execute("SELECT quantity FROM portfolio WHERE stock=:stock AND userid=:userid",
                               stock=quote["symbol"], userid=session["user_id"])

        if not portfolio:  # if there is no quantity of a stock add quantity.
            db.execute("INSERT INTO portfolio (stock, quantity, userid) VALUES (:stock, :quantity, :userid)", # help from a friend
                       stock=quote["symbol"], quantity=shares, userid=session["user_id"])

        if portfolio:
            db.execute("UPDATE portfolio SET quantity=:quantity+quantity WHERE stock=:stock",
                       stock=quote["symbol"], quantity=int(shares))

        return redirect("/")
    if request.method == "GET":
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():

    portfolio = db.execute("SELECT stock, quantity, price, BuyorSell FROM purchases WHERE userid = :id", id=session["user_id"]) # help from a friend
    cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    return render_template("history.html", portfolio=portfolio, cash=cash)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/crypto", methods=["GET", "POST"])
@login_required
def crypto():
    if request.method == "POST":            # if someones does a post request

        if not request.form.get("symbol"):
            return apology("Stock symbol not provided")

        quote = lookup(request.form.get("symbol"))

        if not quote or quote == None:
            return apology("Please provide valid cryptocurrency symbol.")

        else:
            return render_template("cryptos.html", quote=quote, name=quote["name"], price=quote["price"], symbol=quote["symbol"])

    if request.method == "GET":             # if someones does a get request
        return render_template("crypto.html")

@app.route("/ranking", methods=["GET"])
def ranking():
    ranking=db.execute("SELECT ROW_NUMBER() OVER(ORDER BY net_worth DESC) AS num_row, net_worth, username FROM users ORDER BY net_worth DESC LIMIT 10") # https://learnsql.com/cookbook/how-to-number-rows-in-sql/#:~:text=If%20you'd%20like%20to,sorted%20according%20to%20any%20column.

    return render_template("ranking.html", ranking=ranking)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password") or not request.form.get("confirmation"):
            return apology("must provide password")

        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("Confirmed password must match password")

        hashPassword = generate_password_hash(request.form.get("password"))

        if len(db.execute('SELECT username FROM users WHERE username = ?', request.form.get("username"))) > 0: # help from a friend
            return apology("Username already exists", 400)

        else:
            Name = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", # help from a friend
                              username=request.form.get("username"), hash=hashPassword)
            session["user_id"] = Name

            return redirect("/")

    if request.method == "GET":
        return render_template("register.html")




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("Please insert a stock symbol.")
        if not request.form.get("shares"):
            return apology("Please insert a quantity.")

        quote = lookup(request.form.get("symbol"))
        if quote == None:
            return apology("Please provide valid stock symbol.")


        shares = db.execute("SELECT quantity FROM portfolio WHERE stock=:stock", stock=quote["symbol"])
        price = quote['price'] * int(request.form.get("shares"))

        if (int(request.form.get("shares")) > shares[0]["quantity"]):
            return apology("You're selling more than you own.")

        db.execute("UPDATE users SET cash=cash+:cash WHERE id=:id", cash=price, id=session["user_id"])# help from a friend
        db.execute("UPDATE portfolio SET quantity=quantity-:quantity WHERE stock=:stock AND userid=:userid", # help from a friend
                   quantity=int(request.form.get("shares")), stock=quote["symbol"], userid=session["user_id"])

        db.execute("INSERT INTO purchases (userid, stock, price, quantity, BuyorSell) VALUES (:userid, :stock, :price, :quantity, :BuyorSell)",  # Creates a transaction with all values
                   userid=session["user_id"], stock=quote["symbol"], price=quote["price"], quantity=request.form.get("shares"), BuyorSell="Sell")

        db.execute("DELETE FROM portfolio WHERE stock=:stock AND quantity=:quantity AND userid=:userid",  # Deletes stock from portfolio when quantity = 0 for convenience.
                   stock=quote["symbol"], quantity=0, userid=session["user_id"])
        return redirect("/")

    else:
        stock = db.execute("SELECT stock FROM portfolio WHERE userid=:userid", userid=session["user_id"]) # If user has no stocks, sell method is blocked

        if not stock:
            return apology("No stocks to sell, buy one first!")
        if request.method == "GET":
            return render_template("sell.html", stock=stock) # returns sell.html with all of the stocks to display

@app.route("/change_username", methods=["GET", "POST"])
@login_required
def change_username():
    if request.method == "POST":
        if not request.form.get("new_username") or not request.form.get("password"):
            return apology("Input invalid")

        rows = db.execute("SELECT * FROM users WHERE id=:id", id=session["user_id"])
        if check_password_hash(rows[0]["hash"], request.form.get("password")):
            db.execute("UPDATE users SET username=:username WHERE id=:id", username=request.form.get("new_username"), id=session["user_id"])
            return redirect("/")
        else:
            return apology("Invalid Password")
    else:
        return render_template("settings.html")

@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        if not request.form.get("new_password") or not request.form.get("old_password"):
            return apology("Input invalid")

        rows = db.execute("SELECT * FROM users WHERE id=:id", id=session["user_id"])
        if check_password_hash(rows[0]["hash"], request.form.get("old_password")):
            db.execute("UPDATE users SET hash=:hash WHERE id=:id", hash=generate_password_hash(request.form.get("new_password")), id=session["user_id"])
            return redirect("/")
        elif request.form.get("new_password") == request.form.get("old_password"):
            return apology("Input a new password.")
        else:
            return apology("Invalid Password")
    else:
        return render_template("settings.html")


@app.route("/user", methods=["GET", "POST"])
@login_required
def users():
    if request.method == "POST":

        if not request.form.get("user"):
            return apology("Please input a user")

        userID = db.execute("SELECT * FROM users WHERE username=:username", username = request.form.get("user"))
        if not userID:
            return apology("Invalid Usernmame")
        username = userID[0]["username"]

        portfolio = db.execute("SELECT stock, quantity FROM portfolio WHERE userid=:userid", userid=userID[0]["id"])
        return render_template("users.html", portfolio=portfolio, username=username)

    else:
        return render_template("user.html")