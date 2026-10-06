from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Annotated
from fastapi import Form
import sqlite3
import secrets
from urllib.parse import urlparse

app = FastAPI()

DATABASE_NAME = "shortlinks.db"

def init_db():
    with sqlite3.connect(DATABASE_NAME) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS links (
                code TEXT PRIMARY KEY,
                long_url TEXT NOT NULL
            )
        """)


init_db()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>URL Shortener</title>
        </head>
        <body>
            <h1>URL Shortener</h1>
            <p>Paste a long URL and get a shorter one.</p>
            <form action="/shorten" method="post">
            <input type="url" name="long_url" placeholder="https://example.com" required>
            <button type="submit">Shorten</button>
            </form>
        </body>
    </html>
    """

@app.post("/shorten")
def shorten(request: Request, long_url: Annotated[str, Form()]):
    parsed_url = urlparse(long_url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid URL starting with http:// or https://",
        )

    code = secrets.token_urlsafe(6)

    with sqlite3.connect(DATABASE_NAME) as connection:
        connection.execute(
            "INSERT INTO links (code, long_url) VALUES (?, ?)",
            (code, long_url),
        )

    short_url = f"{request.base_url}r/{code}"

    return HTMLResponse(
        f'<p>Your short link: <a href="{short_url}">{short_url}</a></p>'
        '<p><a href="/">Shorten another URL</a></p>'
    )

@app.get("/r/{code}")
def follow_short_link(code: str):
    with sqlite3.connect(DATABASE_NAME) as connection:
        row = connection.execute(
            "SELECT long_url FROM links WHERE code = ?",
            (code,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Short link not found")

    return RedirectResponse(url=row[0])