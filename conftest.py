import os
import sys
from datetime import datetime

import allure
import pytest
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(__file__))

from utilities.config_reader import ConfigReader
from utilities.excel_report_writer import ExcelReportWriter
from utilities.logger import get_logger
from utilities.screenshot_util import ScreenshotUtil
from utilities.test_result_store import TestResultStore
from utilities.visual_mode import enable as enable_visual_mode

logger = get_logger("conftest")


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default=None,
        help="Target environment: dev | staging | prod",
    )
    parser.addoption(
        "--browser-name",
        action="store",
        default=None,
        help="Browser: chromium | firefox | webkit",
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run browser in headed mode with slow motion and scroll",
    )
    parser.addoption(
        "--slow-mo",
        action="store",
        default=None,
        type=int,
        help="Delay in ms between Playwright actions (default: 500 with --headed)",
    )
    parser.addoption(
        "--no-slow-scroll",
        action="store_true",
        default=False,
        help="Disable slow top-to-bottom scroll in headed mode",
    )


def pytest_configure(config):
    TestResultStore.reset()

    env = config.getoption("--env")
    if env:
        os.environ["TEST_ENV"] = env
        ConfigReader.reset_cache()

    if config.getoption("--headed"):
        slow_mo = config.getoption("--slow-mo")
        enable_visual_mode(slow_mo=slow_mo if slow_mo is not None else None)
        if config.getoption("--no-slow-scroll"):
            os.environ["AUTO_SLOW_SCROLL"] = "false"
        else:
            os.environ["AUTO_SLOW_SCROLL"] = "true"

    reports_dir = ConfigReader.get_path("report_path", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(ConfigReader.get_path("screenshot_path", "screenshots"), exist_ok=True)
    os.makedirs(ConfigReader.get_path("download_path", "downloads"), exist_ok=True)
    os.makedirs(os.path.join(reports_dir, "allure-results"), exist_ok=True)

    if not os.environ.get("TEST_LOG_FILE"):
        os.environ["TEST_LOG_FILE"] = os.path.join(
            reports_dir,
            f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        )

    config._metadata = getattr(config, "_metadata", {})
    config._metadata["Environment"] = ConfigReader.get_environment_name()
    config._metadata["Base URL"] = ConfigReader.get("base_url")

    TestResultStore.set_session_meta(
        run_started=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        environment=ConfigReader.get_environment_name(),
        base_url=ConfigReader.get("base_url"),
        html_report=os.path.join(reports_dir, "report.html"),
        log_file=os.environ.get("TEST_LOG_FILE", ""),
    )


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="function")
def browser(playwright_instance, pytestconfig):
    """Function-scoped browser for safe parallel execution (pytest-xdist)."""
    browser_name = pytestconfig.getoption("--browser-name") or ConfigReader.get(
        "browser", "chromium"
    )
    headed = pytestconfig.getoption("--headed")
    headless = ConfigReader.get("headless", True) if not headed else False
    launch_args = {"headless": headless}

    if headed:
        from utilities.visual_mode import get_slow_mo

        launch_args["slow_mo"] = get_slow_mo()
        logger.info("Visual mode: headed browser, slow_mo=%sms", launch_args["slow_mo"])

    browser_type = getattr(playwright_instance, browser_name)
    instance = browser_type.launch(**launch_args)
    yield instance
    instance.close()


@pytest.fixture(scope="function")
def context(browser):
    viewport = ConfigReader.get("viewport", {"width": 1920, "height": 1080})
    ctx = browser.new_context(
        accept_downloads=True,
        viewport=viewport,
        record_video_dir=None,
    )
    ctx.set_default_timeout(ConfigReader.get("timeout", 30000))
    ctx.set_default_navigation_timeout(ConfigReader.get("navigation_timeout", 60000))
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def page(context):
    pg = context.new_page()
    yield pg
    pg.close()


@pytest.fixture(scope="session")
def env_config():
    return ConfigReader.get_all()


def _product_context_from_item(item, product_data=None):
    product_data = product_data if isinstance(product_data, dict) else {}
    test_id = str(product_data.get("test_id") or "").strip()
    partner = str(product_data.get("partner_name") or "").strip()
    product = str(
        product_data.get("product_name") or product_data.get("application_name") or ""
    ).strip()
    module = "Partner Spotlight" if product_data else "Edge Catalog"
    if not test_id:
        name = item.name
        if "metadata" in name:
            test_id = "CAT-001"
        elif "view_toggle" in name:
            test_id = "CAT-002"
        elif "search" in name:
            test_id = "CAT-003"
        else:
            test_id = name[:32]
    return test_id, partner, product, module


@pytest.fixture(autouse=True)
def _excel_report_test_context(request):
    product_data = {}
    if "product_data" in request.fixturenames:
        try:
            product_data = request.getfixturevalue("product_data") or {}
        except Exception:
            product_data = {}
    test_id, partner, product, module = _product_context_from_item(request.node, product_data)
    TestResultStore.set_context(
        test_id=test_id,
        test_name=request.node.name,
        module=module,
        partner=partner,
        product=product,
    )
    yield


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    screenshot_path = ""

    if report.when == "call" and report.failed:
        page = item.funcargs.get("page")
        if page:
            screenshot_util = ScreenshotUtil(page)
            screenshot_path = screenshot_util.capture(name=item.name)
            logger.error("Test failed — screenshot: %s", screenshot_path)

            try:
                html = page.content()
                allure.attach(
                    html,
                    name="page_source",
                    attachment_type=allure.attachment_type.HTML,
                )
            except Exception as exc:
                logger.warning("Could not attach page source: %s", exc)

    if report.when == "setup" and report.failed:
        product_data = getattr(item, "funcargs", {}).get("product_data") or {}
        test_id, partner, product, module = _product_context_from_item(item, product_data)
        failure_msg = str(getattr(report, "longreprtext", report.longrepr))
        TestResultStore.record_test_outcome(
            test_id=test_id,
            test_name=item.name,
            module=module,
            partner=partner,
            product=product,
            status="ERROR",
            duration_sec=report.duration,
            failure_message=failure_msg,
            screenshot=screenshot_path,
        )
        return

    if report.when == "call":
        product_data = item.funcargs.get("product_data") or {}
        test_id, partner, product, module = _product_context_from_item(item, product_data)
        if report.skipped:
            status = "SKIPPED"
        elif report.failed:
            status = "FAILED"
        elif report.passed:
            status = "PASSED"
        else:
            status = "ERROR"

        failure_msg = ""
        if report.failed and hasattr(report, "longreprtext"):
            failure_msg = str(report.longreprtext)

        TestResultStore.record_test_outcome(
            test_id=test_id,
            test_name=item.name,
            module=module,
            partner=partner,
            product=product,
            status=status,
            duration_sec=report.duration,
            failure_message=failure_msg,
            screenshot=screenshot_path,
        )


def pytest_sessionfinish(session, exitstatus):
    try:
        excel_path = ExcelReportWriter.write()
        session.config._excel_report_path = excel_path
        print(f"\nExcel test report: {excel_path}")
        print(f"Latest copy: {os.path.join(ConfigReader.get_path('report_path', 'reports'), 'latest_test_results.xlsx')}")
    except Exception as exc:
        logger.error("Failed to write Excel report: %s", exc)

