import os

from pages.base_page import BasePage
from utilities.breadcrumb_validator import BreadcrumbValidator
from utilities.config_reader import ConfigReader
from utilities.constants import PDF_LINK_SELECTORS, PRODUCT_TITLE_SELECTORS, RESOURCE_LINK_SELECTORS
from utilities.detail_validator import DetailValidator
from utilities.link_validator import LinkValidator
from utilities.metadata_validator import MetadataValidator
from utilities.pdf_validator import PDFValidator


class ProductDetailPage(BasePage):
    def __init__(self, page):
        super().__init__(page)
        self.download_dir = ConfigReader.get_path("download_path", "downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        self.link_validator = LinkValidator(page)
        self.metadata_validator = MetadataValidator(page)
        self.breadcrumb_validator = BreadcrumbValidator(page)
        self.pdf_validator = PDFValidator()
        self.detail = DetailValidator(page)

    def wait_until_loaded(self):
        self.page.wait_for_url("**/partner-spotlight/**", timeout=self.timeout)
        self.wait_for_page_load()
        self.page.wait_for_function(
            """() => {
                const h2s = [...document.querySelectorAll('h2')];
                return h2s.some(el => {
                    const t = (el.textContent || '').trim();
                    return t.length > 3 && !t.includes('Oops') && !t.includes('Filter By')
                        && !t.includes('Subscribe') && !t.includes('Select Your Region');
                });
            }""",
            timeout=self.timeout,
        )
        return self.get_product_title()

    def get_product_title(self):
        for selector in PRODUCT_TITLE_SELECTORS:
            loc = self.page.locator(selector)
            for i in range(loc.count()):
                text = loc.nth(i).inner_text(timeout=5000).strip()
                if text and text not in (
                    "Edge AI Partner Spotlight", "Related Products", "Filter By",
                    "Subscribe To Our Newsletter", "Thank you for subscribing",
                ):
                    return text
        og = self.page.locator("meta[property='og:title']").first
        if og.count():
            content = og.get_attribute("content") or ""
            if " - " in content:
                return content.split(" - ")[0].strip()
        return self.page.title().split(" - ")[0].strip()

    def get_product_description(self):
        ok, _, text = self.detail.validate_full_description()
        return text if ok else ""

    def validate_product_detail(self, expected_title=None, expected_description=None):
        title = self.get_product_title()
        ok, msg, desc = self.detail.validate_full_description(expected_description or "")
        errors = []
        if expected_title and expected_title.lower() not in title.lower():
            errors.append(f"Title mismatch: expected '{expected_title}', got '{title}'")
        if expected_description and not ok:
            errors.append(msg)
        if not title.strip():
            errors.append("Product title is empty")
        if errors:
            return False, "; ".join(errors), {"title": title, "description": desc}
        return True, "Product detail validation passed", {"title": title, "description": desc}

    def validate_thumbnail(self, product_name=None):
        return self.detail.validate_thumbnail(product_name)

    def validate_features(self, expected_features=None):
        return self.detail.validate_features_section(expected_features)

    def validate_contact_link(self, expected_fragment=""):
        return self.detail.validate_partner_contact_link(expected_fragment)

    def validate_categories(self, expected_categories=None):
        if isinstance(expected_categories, str):
            expected_categories = [c.strip() for c in expected_categories.split(",") if c.strip()]
        return self.detail.validate_categories_section(expected_categories)

    def validate_category_subcategory_strict(
        self, category_pairs, listing_site_data=None
    ):
        """Strict validation: Excel pairs must appear on listing + detail page."""
        import allure

        from utilities.category_validator import CategoryValidator

        validator = CategoryValidator(self.page)
        detail_data = validator.collect_detail_site_data()
        ok, msg, report, info = validator.validate_pairs_combined(
            category_pairs,
            listing_data=listing_site_data,
            detail_data=detail_data,
        )
        allure.attach(
            report,
            name="category_subcategory_site_vs_excel",
            attachment_type=allure.attachment_type.TEXT,
        )
        self.logger.info("Combined category validation:\n%s", report)
        return ok, msg, info

    def validate_related_products(self, partner_name):
        return self.detail.validate_related_products(partner_name)

    def download_pdf(self, filename=None):
        link = None
        for selector in PDF_LINK_SELECTORS:
            candidate = self.page.locator(selector).first
            try:
                if candidate.is_visible(timeout=3000):
                    href = candidate.get_attribute("href") or ""
                    cls = candidate.get_attribute("class") or ""
                    if href.endswith(".pdf") or "trackpdfdwload" in cls or "Download" in candidate.inner_text(timeout=2000):
                        link = candidate
                        break
            except Exception:
                continue
        if link is None:
            raise AssertionError("No PDF download link found on page")
        with self.page.expect_download(timeout=self.timeout) as download_info:
            link.click()
        download = download_info.value
        save_name = filename or download.suggested_filename
        save_path = os.path.join(self.download_dir, save_name)
        download.save_as(save_path)
        self.logger.info("Downloaded PDF: %s", save_path)
        return save_path

    def download_and_validate_pdf(self, expected_text=None):
        pdf_path = self.download_pdf()
        ok, message = self.pdf_validator.validate(pdf_path, expected_text=expected_text)
        return ok, message, pdf_path

    def validate_resource_links(self, expected_url=""):
        ok, msg, links = self.detail.validate_resources_section(expected_url)
        if ok or expected_url:
            return ok, msg, links
        return self.link_validator.validate_resource_links(RESOURCE_LINK_SELECTORS, require_all=False)

    def validate_breadcrumbs(self, expected_trail=None):
        if expected_trail and isinstance(expected_trail, str):
            expected_trail = [p.strip() for p in expected_trail.replace("/", ">").split(">") if p.strip()]
        return self.breadcrumb_validator.validate(expected_trail)

    def validate_metadata(self, expected=None):
        return self.metadata_validator.validate(expected)
