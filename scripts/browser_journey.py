"""Actual Chromium end-to-end smoke for the Persian RTL shopping journey.

Uses only synthetic fixture data and a disposable CI database.
Records screenshot evidence; never claims that a synthetic merchant was contacted.
"""
from __future__ import annotations

import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:5173"
OUTPUT = Path("browser-artifacts")
OUTPUT.mkdir(exist_ok=True)


def wait_for_service(url: str, *, seconds: int = 60) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, TimeoutError):
            time.sleep(1)
    raise AssertionError(f"Service did not become ready: {url}")


def assert_no_horizontal_overflow(page, width: int) -> None:
    layout = page.evaluate(
        """() => ({
            scrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth,
            direction: getComputedStyle(document.documentElement).direction,
            language: document.documentElement.lang,
        })"""
    )
    assert layout["direction"] == "rtl", layout
    assert layout["language"] == "fa", layout
    assert layout["scrollWidth"] <= layout["innerWidth"] + 2, (
        f"Horizontal overflow at {width}px: {layout}"
    )


def main() -> None:
    wait_for_service("http://127.0.0.1:8000/api/v1/health/ready/")
    wait_for_service(BASE)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for width in (320, 390, 1440):
                context = browser.new_context(
                    viewport={"width": width, "height": 850},
                    locale="fa-IR",
                    timezone_id="Asia/Tehran",
                    permissions=[],
                )
                page = context.new_page()
                page.set_default_timeout(25000)
                page.goto(BASE, wait_until="domcontentloaded")
                page.locator('textarea[aria-label="پیام به دستیار خرید"]').wait_for()
                assert_no_horizontal_overflow(page, width)
                page.screenshot(path=str(OUTPUT / f"welcome-{width}.png"), full_page=True)

                if width == 390:
                    composer = page.locator('textarea[aria-label="پیام به دستیار خرید"]')
                    posted_missions = []
                    page.on(
                        "request",
                        lambda request: posted_missions.append(request.url)
                        if request.method == "POST" and "/api/v1/missions/" in request.url
                        else None,
                    )
                    composer.fill("احوال شما؟")
                    page.get_by_role("button", name="ارسال پیام").click()
                    page.get_by_text("سلام! خوش اومدی.", exact=False).first.wait_for()
                    assert page.locator(".mission-product-card").count() == 0
                    assert page.locator(".genui-empty-state").count() == 0
                    assert posted_missions == [], "A social greeting must not POST or spend model credit"
                    page.screenshot(path=str(OUTPUT / "greeting-no-products-mobile.png"), full_page=True)
                    composer.fill("چطوری؟")
                    page.get_by_role("button", name="ارسال پیام").click()
                    page.get_by_text("سلام! خوش اومدی.", exact=False).first.wait_for()
                    assert page.locator(".genui-empty-state").count() == 0
                    composer.fill("راهنما")
                    page.get_by_role("button", name="ارسال پیام").click()
                    page.get_by_text("برای شروع نام یا کاربرد محصول را بنویس", exact=False).first.wait_for()
                    assert_no_horizontal_overflow(page, width)
                    page.get_by_role("button", name="انتخاب دستی محدوده").click()
                    page.locator("#manual-tehran-region").select_option("jomhouri")
                    page.get_by_text("محدوده نمونه", exact=False).first.wait_for()
                    assert_no_horizontal_overflow(page, width)
                    # Remove the selected radius before the full fixture journey,
                    # since the example area and synthetic stores are not coincident.
                    page.get_by_role("button", name="حذف موقعیت").click()

                page.locator('textarea[aria-label="پیام به دستیار خرید"]').fill(
                    "هدفون بی سیم تست مرورگر"
                )
                page.get_by_role("button", name="ارسال پیام").click()
                page.locator(".mission-product-card").first.wait_for()
                assert page.locator(".mission-product-highlights").first.is_visible()
                expect(page.locator('.shopping-journey [aria-current="step"]')).to_contain_text("انتخاب مدل")
                assert page.locator(".mission-product-price-line .mission-price-eyebrow").first.is_visible()
                assert page.locator(".mission-product-actions button").first.evaluate(
                    "(el) => el.getBoundingClientRect().height >= 44"
                ), "Primary shopping action must remain thumb-friendly"
                if width == 390:
                    # After a real search, smalltalk should not fabricate or replace
                    # products; the previous search remains available.
                    previous_cards = page.locator(".mission-product-card").count()
                    previous_replies = page.get_by_text("سلام! خوش اومدی.", exact=False).count()
                    prior_post_count = len(posted_missions)
                    composer.fill("احوال شما؟")
                    page.get_by_role("button", name="ارسال پیام").click()
                    page.get_by_text("سلام! خوش اومدی.", exact=False).last.wait_for()
                    assert page.get_by_text("سلام! خوش اومدی.", exact=False).count() == previous_replies + 1
                    assert page.locator(".mission-product-card").count() == previous_cards
                    assert len(posted_missions) == prior_post_count
                assert_no_horizontal_overflow(page, width)
                page.screenshot(path=str(OUTPUT / f"products-{width}.png"), full_page=True)

                if width == 390:
                    # A model-card choice must not invent a chat message.
                    previous_user_turns = page.locator(".chat-message-user").count()
                    page.locator(".mission-product-card .mission-select-button").first.click()
                    expect(page.locator(".mission-product-card .mission-select-button").first).to_have_attribute("aria-pressed", "true")
                    assert page.locator(".chat-message-user").count() == previous_user_turns
                    expect(page.locator('.shopping-journey [aria-current="step"]')).to_contain_text("بررسی فروشگاه")

                    # Comparison remains a user-controlled, difference-first tool.
                    page.locator(".mission-compare-button").first.click()
                    page.locator(".mission-compare-button").nth(1).click()
                    page.locator(".genui-comparison-table").first.wait_for()
                    assert page.locator(".genui-comparison-table tbody tr").count() >= 2
                    assert page.locator(".genui-table-wrap").first.get_attribute("tabindex") == "0"
                    # Dialogue comparison must use the same selected models,
                    # persisted via the focus endpoint before the turn is sent.
                    composer.fill("این دو تا چه فرقی دارند؟")
                    page.get_by_role("button", name="ارسال پیام").click()
                    expect(page.locator(".genui-comparison-table")).to_have_count(2)
                    page.get_by_role("button", name="نمایش همه ویژگی‌ها").first.click()
                    page.get_by_role("button", name="نمایش فقط تفاوت‌ها").first.click()
                    page.locator(".mission-compare-clear").first.click()
                    page.screenshot(path=str(OUTPUT / "comparison-mobile.png"), full_page=True)

                    page.locator(".mission-offers-toggle").first.click()
                    page.locator(".mission-offer-row").nth(1).wait_for()
                    assert page.locator(".mission-offer-row").count() == 2
                    assert page.locator(".mission-offer-list").first.evaluate(
                        "(el) => el.parentElement?.classList.contains('mission-product-card')"
                    ), "Seller evidence should fill the card rather than a narrow text column"
                    page.locator(".mission-seller-location-board summary").first.click()
                    # The server's paid Neshan provider is off by default;
                    # the map/list UX remains fully functional without a secret.
                    page.locator(".mission-neshan-routing").first.get_by_text(
                        "اتصال مسیریابی نشان هنوز فعال نشده است", exact=False
                    ).wait_for()
                    assert page.locator(".mission-neshan-routing button").count() == 0
                    assert page.locator(".mission-location-choices button").count() == 2
                    assert page.locator(".mission-location-map iframe").count() == 0
                    page.locator(".mission-location-choices button").nth(1).click()
                    expect(page.locator(".mission-location-choices button").nth(1)).to_have_attribute("aria-pressed", "true")
                    # Keyless Neshan point link is an explicit opt-in external action,
                    # never auto-navigation, fake ETA or lookup by synthetic shop name.
                    neshan_link = page.get_by_role("link", name="بازکردن مختصات ثبت‌شده در نقشه نشان، نه تأیید فروشگاه")
                    neshan_url = neshan_link.get_attribute("href")
                    assert neshan_url and neshan_url.startswith("https://nshn.ir/?lat=")
                    assert "lng=" in neshan_url
                    assert neshan_link.get_attribute("target") == "_blank"
                    page.get_by_role("button", name="نمایش نقشه OpenStreetMap").click()
                    page.locator(".mission-location-map iframe").first.wait_for()
                    map_url = page.locator(".mission-location-map iframe").first.get_attribute("src")
                    assert map_url and map_url.startswith("https://www.openstreetmap.org/export/embed.html")
                    page.get_by_role("button", name="بستن نقشه").click()
                    assert page.locator(".mission-location-map iframe").count() == 0
                    page.locator(".mission-offer-row .mission-select-button").nth(1).click()
                    expect(page.locator(".mission-offer-row .mission-select-button").nth(1)).to_have_attribute("aria-pressed", "true")
                    # Bare "دومی" now means the second seller, not the second product.
                    composer.fill("دومی")
                    page.get_by_role("button", name="ارسال پیام").click()
                    page.locator(".chat-message-assistant").last.get_by_text("انتخاب شد", exact=False).wait_for()
                    composer.fill("آدرسش")
                    page.get_by_role("button", name="ارسال پیام").click()
                    page.locator(".genui-sellers").last.wait_for()
                    assert "ثبت‌شده" in page.locator(".genui-sellers").last.inner_text()
                    # A stock question must show approval, never silently
                    # run the simulator or search for a product called 'موجودی'.
                    composer.fill("موجودی رو بررسی کن")
                    page.get_by_role("button", name="ارسال پیام").click()
                    page.locator(".genui-contact-consent").last.wait_for()
                    assert "تماس یا پیام واقعی" in page.locator(".genui-contact-consent").last.inner_text()
                    page.locator(".mission-seller-details summary").first.click()
                    # Map was explicitly opened above; no background third-party
                    # embed is created by simply opening the seller list.

                    # The simulator's first result is no_answer and second is available.
                    page.locator(".mission-offer-verify").first.click()
                    page.get_by_text("فروشگاه در سناریوی دمو پاسخ نداد").first.wait_for()
                    page.locator(".mission-offer-verify").nth(1).click()
                    page.locator(".genui-visit-plan").first.wait_for()
                    expect(page.locator('.shopping-journey [aria-current="step"]')).to_contain_text("برنامه مراجعه")
                    page.screenshot(path=str(OUTPUT / "visit-plan-mobile.png"), full_page=True)
                    assert_no_horizontal_overflow(page, width)

                    # The server must return inferred natural-language budget as
                    # effective constraints so the editable UI reflects hard filters.
                    page.locator('textarea[aria-label="پیام به دستیار خرید"]').fill(
                        "هدفون بی سیم تست مرورگر تا سقف ۱ میلیون تومان"
                    )
                    page.get_by_role("button", name="ارسال پیام").click()
                    page.locator(".mission-active-filters").first.wait_for()
                    assert "شرایط همین جست‌وجو" in page.locator(".mission-active-filters").first.inner_text()
                    assert "۱" in page.locator(".mission-active-filters").first.inner_text()
                    assert_no_horizontal_overflow(page, width)
                    page.screenshot(path=str(OUTPUT / "inferred-budget-mobile.png"), full_page=True)

                    # Missing products should show a single clear recovery form,
                    # not a three-times-repeated no-result announcement.
                    page.locator('textarea[aria-label="پیام به دستیار خرید"]').fill(
                        "کوانتوم ناموجود آزمایشگاهی بدون مدل"
                    )
                    page.get_by_role("button", name="ارسال پیام").click()
                    page.locator(".genui-empty-state").last.wait_for()
                    assert page.locator(".genui-empty-state .genui-empty-heading").last.count() == 1
                    assert page.locator(".genui-empty-state .genui-card-heading").last.count() == 0
                    assert page.locator(".chat-message-assistant").last.locator(".assistant-message-copy").count() == 0
                    assert_no_horizontal_overflow(page, width)
                    page.screenshot(path=str(OUTPUT / "empty-result-mobile.png"), full_page=True)

                    # A temporary proxy failure must not delete the draft or
                    # silently submit twice. Recover via GET instead of POST.
                    page.route(
                        "**/api/v1/missions/*/turns/",
                        lambda route: route.fulfill(status=502, content_type="text/html", body="<html>upstream</html>"),
                    )
                    composer.fill("هدفون بی سیم تست مرورگر")
                    page.get_by_role("button", name="ارسال پیام").click()
                    page.locator(".conversation-error").get_by_text("ارتباط با سرور", exact=False).wait_for()
                    assert composer.input_value() == "هدفون بی سیم تست مرورگر"
                    page.unroute("**/api/v1/missions/*/turns/")
                    page.get_by_role("button", name="بازیابی وضعیت").click()
                    page.locator(".conversation-error").wait_for(state="detached")
                    assert_no_horizontal_overflow(page, width)
                    page.screenshot(path=str(OUTPUT / "upstream-recovery-mobile.png"), full_page=True)

                context.close()
            print("BROWSER_JOURNEY=PASS; Chromium RTL 320/390/1440; synthetic fixtures.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
