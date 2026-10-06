from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Annotated
from fastapi import Form
import psycopg
import secrets
from urllib.parse import urlparse

SHORT_CODE_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
from html import escape
import os
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from the environment.")

SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET is missing from the environment.")

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="url_shortener_session",
    same_site="lax",
    https_only=False,
)

def init_db():
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS links (
                code TEXT PRIMARY KEY,
                long_url TEXT NOT NULL,
                owner_id TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


init_db()

def get_browser_id(request: Request) -> str:
    browser_id = request.session.get("browser_id")

    if browser_id is None:
        browser_id = secrets.token_urlsafe(32)
        request.session["browser_id"] = browser_id

    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            "UPDATE links SET owner_id = %s WHERE owner_id IS NULL",
            (browser_id,),
        )

    return browser_id

PAGE_CSS = """
:root {
    color-scheme: light;
    --paper: #f4f3ed;
    --surface: #fffefa;
    --ink: #25352d;
    --muted: #717b73;
    --green: #3c684f;
    --green-dark: #2e523e;
    --line: #e6e6dc;
    --soft-green: #edf2eb;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;
    padding: 24px 20px 56px;
    background: var(--paper);
    color: var(--ink);
    font-family: "Segoe UI", Arial, sans-serif;
}

.page-shell {
    width: min(100%, 820px);
    margin: 0 auto;
}

.topbar,
.section-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}

.topbar {
    margin-bottom: 36px;
}

.brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    color: var(--ink);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-decoration: none;
}

.brand-mark {
    display: grid;
    width: 32px;
    height: 32px;
    place-items: center;
    border-radius: 10px;
    background: var(--green);
    color: white;
    font-size: 18px;
}

.topbar-note,
.eyebrow,
.link-count {
    color: var(--muted);
    font-size: 12px;
}

.hero-panel {
    padding: clamp(28px, 6vw, 56px);
    border: 1px solid var(--line);
    border-radius: 24px;
    background: var(--surface);
    box-shadow: 0 18px 50px rgb(37 53 45 / 6%);
}

.eyebrow {
    margin: 0 0 14px;
    font-weight: 700;
    letter-spacing: 0.12em;
}

.hero-title {
    margin: 0;
    font-family: Georgia, "Times New Roman", serif;
    font-size: clamp(42px, 8vw, 68px);
    font-weight: 500;
    letter-spacing: -0.055em;
    line-height: 1.02;
}

.hero-title span {
    color: var(--green);
    font-style: italic;
}

.intro {
    max-width: 480px;
    margin: 18px 0 30px;
    color: var(--muted);
    font-size: 16px;
    line-height: 1.7;
}

.shorten-form label {
    display: block;
    margin-bottom: 9px;
    font-size: 13px;
    font-weight: 650;
}

.form-row {
    display: flex;
    gap: 10px;
}

.form-row input {
    min-width: 0;
    flex: 1;
    padding: 14px 15px;
    border: 1px solid var(--line);
    border-radius: 11px;
    background: white;
    color: var(--ink);
    font: inherit;
}

.form-row input:focus {
    border-color: var(--green);
    outline: 3px solid rgb(60 104 79 / 16%);
}

.form-row button {
    padding: 0 20px;
    border: 0;
    border-radius: 11px;
    background: var(--green);
    color: white;
    font: inherit;
    font-weight: 650;
    cursor: pointer;
    transition: background 160ms ease, transform 160ms ease;
}

.form-row button:hover {
    transform: translateY(-1px);
    background: var(--green-dark);
}

.privacy-note {
    margin: 18px 0 0;
    padding: 13px 15px;
    border-radius: 10px;
    background: var(--soft-green);
    color: #4e6254;
    font-size: 13px;
    line-height: 1.6;
}

.links-section {
    margin-top: 38px;
}

.section-heading {
    margin-bottom: 14px;
}

.section-heading .eyebrow {
    margin-bottom: 5px;
}

.section-heading h2 {
    margin: 0;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 28px;
    font-weight: 500;
}

.link-count {
    padding: 7px 11px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface);
}

.link-list {
    display: grid;
    gap: 10px;
    margin: 0;
    padding: 0;
    list-style: none;
}

.link-list li {
    padding: 17px 19px;
    overflow-wrap: anywhere;
    border: 1px solid var(--line);
    border-radius: 13px;
    background: var(--surface);
    color: var(--muted);
    line-height: 1.7;
}

.link-list a {
    color: var(--green);
    font-weight: 650;
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
}

.saved-link {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}

.saved-link-main {
    min-width: 0;
    overflow-wrap: anywhere;
}

.original-url {
    margin: 6px 0 0;
    color: var(--muted);
    font-size: 13px;
    overflow-wrap: anywhere;
}

.link-actions {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.action-button {
    padding: 8px 12px;
    border: 1px solid var(--line);
    border-radius: 9px;
    background: white;
    color: var(--green);
    font: inherit;
    font-size: 13px;
    font-weight: 650;
    cursor: pointer;
    transition: background 160ms ease, transform 160ms ease;
}

.action-button:hover {
    transform: translateY(-1px);
    background: var(--soft-green);
}

.action-button:focus-visible {
    outline: 3px solid rgb(60 104 79 / 28%);
    outline-offset: 2px;
}

.action-button.copy-button {
    border-color: var(--green);
    background: var(--green);
    color: white;
}

.action-button.copy-button:hover {
    background: var(--green-dark);
}

.action-feedback {
    flex-basis: 100%;
    min-height: 1em;
    color: var(--green);
    font-size: 12px;
}

footer {
    margin-top: 32px;
    color: var(--muted);
    font-size: 12px;
    text-align: center;
}

@media (max-width: 560px) {
    body {
        padding: 18px 14px 40px;
    }

    .topbar {
        margin-bottom: 22px;
    }

    .topbar-note {
        max-width: 120px;
        text-align: right;
    }

    .form-row {
        flex-direction: column;
    }

    .form-row button {
        min-height: 48px;
    }

    .saved-link {
        align-items: flex-start;
        flex-direction: column;
    }

    .saved-link .link-actions {
        width: 100%;
    }
}

.result-panel {
    text-align: center;
}

.success-mark {
    display: grid;
    width: 54px;
    height: 54px;
    margin: 0 auto 20px;
    place-items: center;
    border-radius: 50%;
    background: var(--soft-green);
    color: var(--green);
    font-size: 25px;
    font-weight: 700;
}

.result-panel .intro {
    margin-right: auto;
    margin-left: auto;
}

.short-url-box {
    margin: 24px auto 0;
    padding: 17px 20px;
    border: 1px solid var(--line);
    border-radius: 13px;
    background: white;
}

.short-url-box a {
    color: var(--green);
    font-size: 17px;
    font-weight: 700;
    overflow-wrap: anywhere;
    text-decoration-thickness: 1px;
    text-underline-offset: 4px;
}

.short-url-box .link-actions {
    justify-content: center;
    margin-top: 14px;
}

.back-link {
    display: inline-block;
    margin-top: 22px;
    color: var(--green);
    font-size: 14px;
    font-weight: 650;
    text-decoration: none;
}

.back-link:hover {
    text-decoration: underline;
}
"""

PAGE_SCRIPT = """
async function copyShortUrl(url) {
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(url);
        return;
    }

    const textArea = document.createElement("textarea");
    textArea.value = url;
    textArea.style.position = "fixed";
    textArea.style.opacity = "0";
    document.body.appendChild(textArea);
    textArea.select();
    const copied = document.execCommand("copy");
    textArea.remove();

    if (!copied) {
        throw new Error("Clipboard copy was not available");
    }
}

document.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;

    const actions = button.closest(".link-actions");
    if (!actions) return;

    const url = actions.dataset.url;
    const feedback = actions.querySelector(".action-feedback");
    feedback.textContent = "";

    if (button.dataset.action === "copy") {
        try {
            await copyShortUrl(url);
            feedback.textContent = "Link copied.";
        } catch {
            feedback.textContent = "Could not copy automatically. Please copy the link manually.";
        }
        return;
    }

    if (button.dataset.action === "share") {
        if (navigator.share) {
            try {
                await navigator.share({ title: "A short link", url });
                feedback.textContent = "Share menu opened.";
            } catch (error) {
                if (error.name !== "AbortError") {
                    feedback.textContent = "Sharing could not be opened.";
                }
            }
        } else {
            try {
                await copyShortUrl(url);
                feedback.textContent = "Sharing is not available here, so the link was copied instead.";
            } catch {
                feedback.textContent = "Sharing is unavailable and the link could not be copied.";
            }
        }
    }
});
"""

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    browser_id = get_browser_id(request)
    with psycopg.connect(DATABASE_URL) as connection:
        links = connection.execute(
            "SELECT code, long_url FROM links WHERE owner_id = %s ORDER BY created_at DESC",
            (browser_id,),
        ).fetchall()

    if links:
        links_html = ""

        for code, long_url in links:
            short_url = f"{request.base_url}r/{code}"
            safe_short_url = escape(short_url, quote=True)

            links_html += (
                '<li class="saved-link">'
                '<div class="saved-link-main">'
                f'<a class="saved-short-link" href="{safe_short_url}">'
                f'{escape(code)}</a>'
                f'<p class="original-url">{escape(long_url)}</p>'
                '</div>'
                f'<div class="link-actions" data-url="{safe_short_url}">'
                '<button type="button" class="action-button copy-button" data-action="copy">Copy</button>'
                '<button type="button" class="action-button" data-action="share">Share</button>'
                '<span class="action-feedback" aria-live="polite"></span>'
                '</div>'
                '</li>'
            )
    else:
        links_html = "<li>No links yet.</li>"

    return f"""
        <!doctype html>
        <html lang="en">
        <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>URL Shortener</title>
        <style>{PAGE_CSS}</style>
    </head>
    <body>
        <div class="page-shell">
            <header class="topbar">
                <a class="brand" href="/">
                    <span class="brand-mark" aria-hidden="true">↗</span>
                    <span>URL SHORTENER</span>
                </a>
                <span class="topbar-note">A small tool for long links</span>
            </header>

            <main>
                <section class="hero-panel">
                    <p class="eyebrow">A QUIETER WAY TO SHARE</p>
                    <h1 class="hero-title">Long links,<br><span>made lighter.</span></h1>
                    <p class="intro">
                        Turn a long URL into a short link that’s easier to share.
                    </p>

                    <form class="shorten-form" action="/shorten" method="post">
                        <label for="long_url">Your long URL</label>
                        <div class="form-row">
                            <input
                                id="long_url"
                                type="url"
                                name="long_url"
                                placeholder="https://example.com"
                                required
                            >
                            <button type="submit">Shorten link&nbsp; ↗</button>
                        </div>
                    </form>

                    <p class="privacy-note">
                        Your saved links are tied to this browser. Clearing cookies
                        or switching browsers or devices will hide them from your list.
                        Short links you have copied will still work.
                    </p>
                </section>

                <section class="links-section">
                    <div class="section-heading">
                        <div>
                            <p class="eyebrow">YOUR COLLECTION</p>
                            <h2>Your links</h2>
                        </div>
                        <span class="link-count">{len(links)} saved</span>
                    </div>
                    <ul class="link-list">{links_html}</ul>
                </section>
            </main>

            <footer>Made for useful links.</footer>
        </div>
    <script>{PAGE_SCRIPT}</script>
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

    with psycopg.connect(DATABASE_URL) as connection:
        while True:
            code = "".join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(7))
            inserted = connection.execute(
                """
                INSERT INTO links (code, long_url, owner_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (code) DO NOTHING
                RETURNING code
                """,
                (code, long_url, browser_id),
            ).fetchone()

            if inserted is not None:
                break

    short_url = f"{request.base_url}r/{code}"

    safe_short_url = escape(short_url, quote=True)
    return HTMLResponse(f"""
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Your link is ready</title>
            <style>{PAGE_CSS}</style>
        </head>
        <body>
            <div class="page-shell">
            <header class="topbar">
                <a class="brand" href="/">
                    <span class="brand-mark" aria-hidden="true">↗</span>
                    <span>URL SHORTENER</span>
                </a>
                    <span class="topbar-note">A small tool for long links</span>
            </header>

        <main>
            <section class="hero-panel result-panel">
                <div class="success-mark" aria-hidden="true">✓</div>
                <p class="eyebrow">YOUR LINK IS READY</p>
                <h1 class="hero-title">All set.</h1>
                <p class="intro">
                    Here’s your shorter link. Anyone who has it can use it.
                </p>

                <div class="short-url-box">
                    <a href="{safe_short_url}">{escape(code)}</a>
                    <div class="link-actions" data-url="{safe_short_url}">
                        <button type="button" class="action-button copy-button" data-action="copy">Copy</button>
                        <button type="button" class="action-button" data-action="share">Share</button>
                        <span class="action-feedback" aria-live="polite"></span>
                    </div>
                </div>

                <a class="back-link" href="/">← Back to your links</a>
            </section>
        </main>

        <footer>Made for useful links.</footer>
    </div>
<script>{PAGE_SCRIPT}</script>
</body>
</html>
""")

@app.get("/r/{code}")
def follow_short_link(code: str):
    with psycopg.connect(DATABASE_URL) as connection:
        row = connection.execute(
            "SELECT long_url FROM links WHERE code = %s",
            (code,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Short link not found")

    return RedirectResponse(url=row[0])