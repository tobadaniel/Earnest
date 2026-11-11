#!/usr/bin/env python3
"""Capture Earnest screenshots + demo video from the local production build (demo wallet flow)."""
import os, json, base64
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:4176/"
ASSETS = os.path.expanduser("~/workspace/earnest/assets")
VIDEO_DIR = os.path.expanduser("~/workspace/earnest/assets/video-raw")
os.makedirs(ASSETS, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)


def flow(page, shots=False, slow=False):
    def wait(ms):
        page.wait_for_timeout(ms * (2 if slow else 1))

    page.goto(URL, wait_until="networkidle")
    page.wait_for_selector(".passport", timeout=20000)
    page.add_style_tag(content="footer{display:none!important}")
    wait(900)
    if shots:
        page.screenshot(path=f"{ASSETS}/screenshot-1.png")

    # Verify the passport chain
    page.click('button[data-action="verify"]')
    wait(1600)
    page.locator('.receipt').last.scroll_into_view_if_needed()
    wait(500)
    if shots:
        page.screenshot(path=f"{ASSETS}/screenshot-2.png")

    # Jobs board
    page.evaluate("window.scrollTo(0,0)")
    page.click('button[data-action="tab"][data-id="jobs"]')
    wait(700)
    if shots:
        page.screenshot(path=f"{ASSETS}/screenshot-3.png")

    # Claim job 1, get paid, seal the receipt
    card = page.locator('article.job').first
    card.scroll_into_view_if_needed()
    card.locator('button[data-action="claim"]').click()
    wait(800)
    card = page.locator('article.job').first
    card.locator('button[data-action="pay"]').click()
    page.wait_for_selector('button[data-action="sign-poster"]', timeout=20000)
    wait(900)
    card = page.locator('article.job').first
    card.locator('button[data-action="sign-poster"]').click()
    page.wait_for_selector('button[data-action="seal"]', timeout=20000)
    wait(900)
    card = page.locator('article.job').first
    card.locator('button[data-action="seal"]').click()
    page.wait_for_selector('text=receipt sealed in the passport chain', timeout=20000)
    wait(1000)
    if shots:
        card = page.locator('article.job').first
        card.scroll_into_view_if_needed()
        wait(300)
        page.screenshot(path=f"{ASSETS}/screenshot-4.png")

    # Passport again: the chain grew
    page.click('button[data-action="tab"][data-id="passport"]')
    wait(800)
    page.evaluate("window.scrollTo(0,0)")
    wait(400)
    if shots:
        page.screenshot(path=f"{ASSETS}/screenshot-5.png")

    # Public passport link view
    raw = page.evaluate("localStorage.getItem('earnest-v1')")
    data = json.loads(raw)
    payload = json.dumps({"n": data["name"], "r": data["receipts"]})
    enc = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    page.goto(URL + "?pub=1#p=" + enc, wait_until="networkidle")
    page.wait_for_selector("button[data-action='verify-public']", timeout=20000)
    page.add_style_tag(content="footer{display:none!important}")
    wait(800)
    page.click('button[data-action="verify-public"]')
    wait(1700)
    if shots:
        page.screenshot(path=f"{ASSETS}/screenshot-6.png")

    # Grow tab
    page.goto(URL + "?g=1", wait_until="networkidle")
    page.wait_for_selector(".passport", timeout=20000)
    page.add_style_tag(content="footer{display:none!important}")
    wait(600)
    page.click('button[data-action="tab"][data-id="grow"]')
    wait(700)
    if shots:
        page.screenshot(path=f"{ASSETS}/screenshot-7.png")
    page.locator('button[data-action="stake"]').click()
    wait(1600)
    if shots:
        page.screenshot(path=f"{ASSETS}/screenshot-8.png")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 430, "height": 932}, device_scale_factor=2)
        flow(page, shots=True)
        browser.close()
        print("screenshots done")

        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 430, "height": 932}, device_scale_factor=1,
            record_video_dir=VIDEO_DIR, record_video_size={"width": 430, "height": 932},
        )
        page = ctx.new_page()
        flow(page, shots=False, slow=True)
        ctx.close()
        browser.close()
        print("video done:", os.listdir(VIDEO_DIR))


if __name__ == "__main__":
    main()
