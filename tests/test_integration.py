import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8765"


async def mcp_result(root):
    params = StdioServerParameters(command=sys.executable, args=[str(root / "mcp_server.py")])
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            listed = await session.call_tool("list_qa_runs", {})
            assert not listed.isError, listed
            runs = listed.structuredContent["result"]
            candidate = next(run for run in runs if run["environment"] == "Local candidate")
            detail = await session.call_tool("get_qa_run", {"run_id": candidate["id"]})
            assert not detail.isError, detail
            return runs, detail.structuredContent


class WorkbenchIntegrationTest(unittest.TestCase):
    def test_dashboard_history_screenshots_and_mcp(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for folder in ("demo", "web"):
                shutil.copytree(ROOT / folder, root / folder)
            for file in ("app.py", "workbench.py", "mcp_server.py"):
                shutil.copyfile(ROOT / file, root / file)
            (root / "profiles.local.json").write_text(json.dumps([{
                "name": "Custom smoke",
                "url": URL + "/demo/",
                "suite": "smoke",
                "checks": [{"name": "Checkout heading", "selector": "h1", "text": "Checkout"}],
                "repository": "https://github.com/example/storefront",
                "revision": "main",
            }]), encoding="utf-8")

            with subprocess.Popen(
                [sys.executable, str(root / "app.py")],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ) as app:
                try:
                    self.wait_for_dashboard(app)
                    self.run_browser_demo()
                    runs, detail = asyncio.run(mcp_result(root))
                    self.assertEqual(len(runs), 3)
                    self.assertEqual(detail["status"], "failed")
                    failed = [check for check in detail["checks"] if check["status"] == "failed"]
                    self.assertEqual(len(failed), 3)
                    self.assertIn("$55.00", failed[0]["detail"])
                    with urlopen(failed[0]["screenshot_url"], timeout=5) as screenshot:
                        self.assertEqual(screenshot.headers.get_content_type(), "image/png")
                        self.assertEqual(screenshot.read(8), b"\x89PNG\r\n\x1a\n")
                finally:
                    if app.poll() is None:
                        app.terminate()
                        app.wait(timeout=10)

    def wait_for_dashboard(self, app):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            self.assertIsNone(app.poll(), "Dashboard exited. Check that port 8765 is free.")
            try:
                with urlopen(URL, timeout=1) as response:
                    if response.status == 200:
                        return
            except URLError:
                time.sleep(0.1)
        self.fail("Dashboard did not become available.")

    def run_browser_demo(self):
        with sync_playwright() as playwright:
            with playwright.chromium.launch() as browser:
                page = browser.new_page()
                page.goto(URL)
                button = page.get_by_role("button", name="Run checks")
                button.click()
                expect(page.get_by_role("button", name="Local reference · passed · 4/4", exact=False)).to_be_visible(
                    timeout=20000
                )
                picker = page.get_by_label("Environment")
                picker.select_option("Local candidate")
                button.click()
                expect(page.get_by_role("button", name="Local candidate · failed · 1/4", exact=False)).to_be_visible(
                    timeout=20000
                )
                expect(page.get_by_role("link", name="Open screenshot")).to_have_count(3)
                picker.select_option("Custom smoke")
                button.click()
                expect(page.get_by_role("button", name="Custom smoke · passed · 1/1", exact=False)).to_be_visible(
                    timeout=20000
                )
                page.reload()
                page.get_by_role("button", name="Local candidate · failed · 1/4", exact=False).click()
                expect(page.get_by_role("link", name="Open screenshot")).to_have_count(3)
