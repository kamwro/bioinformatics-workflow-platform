from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

_STATIC_DIR = Path(__file__).parent / "static"


def _head_injection() -> str:
    dark_theme_css = (_STATIC_DIR / "swagger_dark.css").read_text(encoding="utf-8")
    toggle_css = (_STATIC_DIR / "swagger_theme_toggle.css").read_text(encoding="utf-8")
    toggle_js = (_STATIC_DIR / "swagger_theme_toggle.js").read_text(encoding="utf-8")

    return (
        f'<style id="swagger-dark-style">{dark_theme_css}</style>'
        f"<style>{toggle_css}</style>"
        f"<script>{toggle_js}</script>"
    )


def register_swagger_ui(app: FastAPI) -> None:
    """Serve Swagger UI at /docs with a light/dark theme switch.

    The default docs route must be disabled (``docs_url=None``) so this route can
    replace it. The dark theme is injected as a toggleable stylesheet layered on
    top of the standard swagger-ui.css; the injected script adds a small button
    that flips between light and dark and stores the choice in localStorage,
    defaulting to the OS color scheme.
    """

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui_html() -> HTMLResponse:
        response = get_swagger_ui_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title=f"{app.title} - Swagger UI",
        )
        html = (
            bytes(response.body)
            .decode("utf-8")
            .replace("</head>", f"{_head_injection()}</head>")
        )
        return HTMLResponse(html)
