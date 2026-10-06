from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Annotated
from fastapi import Form
import sqlite3
import secrets
from urllib.parse import urlparse
from html import escape
import os
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()
SESSION_SECRET = os.getenv("SESSION_SECRET")

if not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET is missing from your .env file.")

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="url_shortener_session",
    same_site="lax",
    https_only=False,
)

DATABASE_NAME = "shortlinks.db"

def init_db():
    with sqlite3.connect(DATABASE_NAME) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS links (
                code TEXT PRIMARY KEY,
                long_url TEXT NOT NULL,
                owner_id TEXT
            )
        """)

        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(links)")
        }

        if "owner_id" not in columns:
            connection.execute("ALTER TABLE links ADD COLUMN owner_id TEXT")


init_db()

def get_browser_id(request: Request) -> str:
    browser_id = request.session.get("browser_id")

    if browser_id is None:
        browser_id = secrets.token_urlsafe(32)
        request.session["browser_id"] = browser_id

    with sqlite3.connect(DATABASE_NAME) as connection:
        connection.execute(
            "UPDATE links SET owner_id = ? WHERE owner_id IS NULL",
            (browser_id,),
        )

    return browser_id

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    browser_id = get_browser_id(request)
    with sqlite3.connect(DATABASE_NAME) as connection:
        links = connection.execute(
            "SELECT code, long_url FROM links WHERE owner_id = ? ORDER BY rowid DESC",
            (browser_id,),
        ).fetchall()

    if links:
        links_html = "".join(
            f'<li><a href="{request.base_url}r/{code}">'
            f'{request.base_url}r/{code}</a> — {escape(long_url)}</li>'
            for code, long_url in links
        )
    else:
        links_html = "<li>No links yet.</li>"

    return f"""
    <html>
        <head>
            <title>URL Shortener</title>
        </head>
        <body>
            <h1>URL Shortener</h1>
            <p>Paste a long URL and get a shorter one.</p>
            <form action="/shorten" method="post">
                <input type="url" name="long_url"
                       placeholder="https://example.com" required>
                <button type="submit">Shorten</button>
            </form>
            <p><small>
                Your saved links are tied to this browser. Clearing cookies or using another
                browser or device will hide them from your list. Short links you have copied
                will still work.
            </small></p>
            <h2>Your links</h2>
            <ul>{links_html}</ul>
        </body>
    </html>
    """

@app.post("/shorten")
def shorten(request: Request, long_url: Annotated[str, Form()]):
    browser_id = get_browser_id(request)
    parsed_url = urlparse(long_url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid URL starting with http:// or https://",
        )

    code = secrets.token_urlsafe(6)

    with sqlite3.connect(DATABASE_NAME) as connection:
        connection.execute(
            "INSERT INTO links (code, long_url, owner_id) VALUES (?, ?, ?)",
            (code, long_url, browser_id),
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