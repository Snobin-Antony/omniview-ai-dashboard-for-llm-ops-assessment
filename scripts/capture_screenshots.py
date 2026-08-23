"""Capture UI screenshots for the three exercise pages."""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BASE = "http://127.0.0.1:5173"


def capture(page, path: str, out: Path) -> None:
    page.goto(f"{BASE}{path}", wait_until="networkidle")
    page.wait_for_timeout(1500)
    page.screenshot(path=str(out), full_page=True)
    print(f"saved {out.name}")


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        capture(page, "/usage", ASSETS / "problem1_usage_admin_view.png")
        capture(page, "/documents", ASSETS / "problem2_document_insights.png")
        # Open details panel if a row exists
        rows = page.locator("button").filter(has_text="Document")
        if rows.count() > 0:
            rows.first.click()
            page.wait_for_timeout(800)
            page.screenshot(
                path=str(ASSETS / "problem2_document_insights.png"), full_page=True
            )
        capture(page, "/jobs", ASSETS / "problem3_jobs_worker.png")
        browser.close()


if __name__ == "__main__":
    main()
