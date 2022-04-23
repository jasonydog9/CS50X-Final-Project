from datetime import datetime
import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        url = f"https://api.coinranking.com/v2/search-suggestions?query={symbol}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        crypto = response.json()
        return {
            "name": crypto["data"]["coins"][0]["name"],
            "symbol": crypto["data"]["coins"][0]["symbol"],
            "price": float(crypto["data"]["coins"][0]["price"])
        }
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.4f}" # rounded to 4 digits due to complexity and precision of cryptocurrency
