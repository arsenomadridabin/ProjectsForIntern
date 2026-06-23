import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


DOWNLOAD_KEYWORDS = [
    "download pdf",
    "pdf",
    "download",
    "view pdf",
    "article pdf",
    "full text pdf",
]


# Check out what regular expressions are
def safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\-. ]+", "_", name)
    return name[:180]


# Sometime we may want to take help of Claude to find the pdf_link. We want to do it programattically though
def find_pdf_links(page, base_url):
    links = page.locator("a")
    candidates = []

    for i in range(links.count()):
        try:
            link = links.nth(i)
            text = link.inner_text(timeout=1000).strip().lower()
            href = link.get_attribute("href")

            if not href:
                continue

            full_url = urljoin(base_url, href)
            href_lower = full_url.lower()

            if (
                ".pdf" in href_lower
                or "pdf" in href_lower
                or any(k in text for k in DOWNLOAD_KEYWORDS)
            ):
                candidates.append(
                    {
                        "index": i,
                        "text": text,
                        "url": full_url,
                    }
                )
        except Exception:
            continue

    return candidates


def download_direct_pdf(page, pdf_url, filename=None):
    response = page.request.get(pdf_url, timeout=60000)

    content_type = response.headers.get("content-type", "").lower()

    if not response.ok:
        print(f"Failed direct download: HTTP {response.status}")
        return None

    if "pdf" not in content_type and not pdf_url.lower().endswith(".pdf"):
        print("Link did not return a PDF.")
        return None

    if filename is None:
        filename = pdf_url.split("/")[-1].split("?")[0] or "paper.pdf"

    if not filename.endswith(".pdf"):
        filename += ".pdf"

    path = DOWNLOAD_DIR / safe_filename(filename)
    path.write_bytes(response.body())

    print(f"Download successful")
    print(f"Downloaded in this location: {path.resolve()}")

    return path


def click_and_download(page, locator):
    try:
        with page.expect_download(timeout=15000) as download_info:
            locator.click(timeout=10000)

        download = download_info.value
        filename = safe_filename(download.suggested_filename)
        path = DOWNLOAD_DIR / filename

        download.save_as(path)

        print("Download successful")
        print(f"Downloaded in this location: {path.resolve()}")

        return path

    except PlaywrightTimeoutError:
        return None
    except Exception as e:
        print(f"Click download failed: {e}")
        return None


def try_download_from_website(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
        )

        context = browser.new_context(
            accept_downloads=True,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()

        print(f"Opening: {url}")

        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        final_url = page.url
        print(f"Final URL after redirect: {final_url}")

        # Case 1: current page itself is a PDF
        content_type = ""
        try:
            response = page.goto(final_url, wait_until="domcontentloaded", timeout=60000)
            if response:
                content_type = response.headers.get("content-type", "").lower()
        except Exception:
            pass

        if "pdf" in content_type or final_url.lower().endswith(".pdf"):
            print("Current page appears to be a PDF.")
            result = download_direct_pdf(page, final_url)
            browser.close()
            return result

        # Case 2: find PDF/download links
        candidates = find_pdf_links(page, final_url)

        print(f"Found {len(candidates)} possible PDF/download candidates.")

        for c in candidates:
            print(f"- Candidate: text='{c['text']}' url='{c['url']}'")

        # First try direct PDF-looking URLs
        for c in candidates:
            if ".pdf" in c["url"].lower() or "pdf" in c["url"].lower():
                result = download_direct_pdf(page, c["url"])
                if result:
                    browser.close()
                    return result

        # Then try clicking candidate links/buttons
        links = page.locator("a")

        for c in candidates:
            locator = links.nth(c["index"])
            result = click_and_download(page, locator)
            if result:
                browser.close()
                return result

        # Case 3: try common button/link text
        for keyword in DOWNLOAD_KEYWORDS:
            locator = page.get_by_text(keyword, exact=False)

            if locator.count() > 0:
                print(f"Trying visible text match: {keyword}")
                result = click_and_download(page, locator.first)
                if result:
                    browser.close()
                    return result

        print("No downloadable PDF found.")
        browser.close()
        return None

## CODE I ADDED?CHANGED

if __name__ == "__main__":

    with open("dois.txt", "r", encoding="utf-8") as f, \
         open("download_log.csv", "w", encoding="utf-8") as log:

        log.write("doi_url,status,file_or_error\n")

        for line in f:
            doi_url = line.strip()

            if not doi_url:
                continue

            if not doi_url.startswith("http"):
                doi_url = "https://doi.org/" + doi_url

            print(f"\nTrying: {doi_url}")

            try:
                result = try_download_from_website(doi_url)

                if result:
                    log.write(f"{doi_url},success,{result}\n")
                else:
                    log.write(f"{doi_url},failed,no_pdf_found\n")

            except Exception as e:
                log.write(f"{doi_url},failed,{e}\n")
                print(f"Failed: {e}")
