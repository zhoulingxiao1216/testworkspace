from pathlib import Path

from playwright.sync_api import sync_playwright


WORKSPACE = Path(__file__).resolve().parents[1]
HTML_PATH = WORKSPACE / "assets" / "dual_agent_capability_map.html"
PNG_PATH = WORKSPACE / "assets" / "dual_agent_capability_map.png"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1800, "height": 1080},
            device_scale_factor=2,
        )
        page = context.new_page()
        page.goto(HTML_PATH.as_uri(), wait_until="networkidle")
        page.locator(".canvas").screenshot(path=str(PNG_PATH))
        browser.close()

    print(f"Saved {PNG_PATH}")


if __name__ == "__main__":
    main()
