from urllib.parse import urljoin, urlparse

from playwright.sync_api import Page

from utilities.logger import get_logger

logger = get_logger(__name__)


class LinkValidator:
    """Validates resource and navigation links on a page."""

    def __init__(self, page: Page):
        self.page = page

    def get_links(self, selector="a[href]"):
        locator = self.page.locator(selector)
        count = locator.count()
        links = []
        for index in range(count):
            element = locator.nth(index)
            href = element.get_attribute("href")
            text = element.inner_text(timeout=5000).strip()
            if href:
                links.append({"href": href, "text": text, "index": index})
        return links

    def resolve_url(self, href, base_url=None):
        base = base_url or self.page.url
        if href.startswith("//"):
            href = f"https:{href}"
        resolved = urljoin(base, href)
        if resolved.startswith("/"):
            resolved = urljoin("https://builders.intel.com", href)
        return resolved

    def is_valid_url(self, url):
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    def validate_link_responds(self, url, timeout=15000):
        resolved = self.resolve_url(url)
        if not self.is_valid_url(resolved):
            return False, f"Invalid URL: {resolved}"

        if resolved.lower().endswith(".pdf"):
            response = self.page.request.head(resolved, timeout=timeout)
            if response.ok:
                return True, f"PDF link OK ({response.status}): {resolved}"
            return False, f"PDF link failed ({response.status}): {resolved}"

        response = self.page.request.get(resolved, timeout=timeout)
        if response.ok:
            return True, f"Link OK ({response.status}): {resolved}"
        return False, f"Link failed ({response.status}): {resolved}"

    def validate_resource_links(self, selectors, require_all=True):
        results = []
        for selector in selectors:
            links = self.get_links(selector)
            for link in links:
                ok, message = self.validate_link_responds(link["href"])
                results.append(
                    {
                        "href": link["href"],
                        "text": link["text"],
                        "ok": ok,
                        "message": message,
                    }
                )
                logger.info("Resource link check: %s", message)

        if not results:
            return False, "No resource links found", results

        failed = [r for r in results if not r["ok"]]
        if failed and require_all:
            return False, f"{len(failed)} resource link(s) failed", results

        return True, f"All {len(results)} resource link(s) valid", results
