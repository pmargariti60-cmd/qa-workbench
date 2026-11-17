"""Environment profiles, Playwright checks, and persisted run evidence."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.sync_api import Error, expect, sync_playwright

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "data" / "runs"
WORKBENCH_URL = "http://127.0.0.1:8765"
LABEL = re.compile(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+")
RUN_ID = re.compile(r"[0-9a-f]{32}")


def profiles():
    result = [
        {
            "name": "Local reference",
            "url": f"{WORKBENCH_URL}/demo/",
            "suite": "checkout",
        },
        {
            "name": "Local candidate",
            "url": f"{WORKBENCH_URL}/demo/?build=candidate",
            "suite": "checkout",
        },
    ]
    config = ROOT / "profiles.local.json"
    if config.exists():
        custom = json.loads(config.read_text(encoding="utf-8"))
        if not isinstance(custom, list):
            raise ValueError("profiles.local.json must contain an array.")
        result.extend(custom)
    names = set()
    for profile in result:
        validate_profile(profile)
        if profile["name"] in names:
            raise ValueError(f"Duplicate profile name: {profile['name']}")
        names.add(profile["name"])
    return result


def validate_profile(profile):
    if not isinstance(profile, dict):
        raise ValueError("Each profile must be an object.")
    for key in ("name", "url", "suite"):
        if not isinstance(profile.get(key), str) or not profile[key].strip():
            raise ValueError(f"A profile needs a nonempty {key}.")
    url = urlsplit(profile["url"])
    if url.scheme not in ("http", "https") or not url.hostname or url.username is not None:
        raise ValueError("Environment URL must be HTTP or HTTPS without inline credentials.")
    repo = profile.get("repository", "")
    if not isinstance(repo, str) or (repo and not re.fullmatch(
        r"https://github\.com/" + LABEL.pattern, repo
    )):
        raise ValueError("Repository must use https://github.com/OWNER/REPOSITORY.")
    if not isinstance(profile.get("revision", ""), str):
        raise ValueError("Revision must be text.")
    suite = profile["suite"]
    if suite == "checkout":
        return
    if suite != "smoke":
        raise ValueError("Suite must be checkout or smoke.")
    checks = profile.get("checks")
    if not isinstance(checks, list) or not 1 <= len(checks) <= 12:
        raise ValueError("A smoke suite needs 1–12 checks.")
    for check in checks:
        if not isinstance(check, dict) or any(
            not isinstance(check.get(key), str) or not check[key].strip()
            for key in ("name", "selector")
        ):
            raise ValueError("Each smoke check needs a name and selector.")
        if "text" in check and not isinstance(check["text"], str):
            raise ValueError("Smoke check text must be a string.")


def apply_code(page, value):
    page.get_by_label("Discount code").fill(value)
    page.get_by_role("button", name="Apply code").click()


def initial_total(page):
    expect(page.locator("#total")).to_have_text("$55.00")


def discounted_total(page):
    apply_code(page, "SAVE10")
    expect(page.locator("#discount")).to_have_text("$5.00")
    expect(page.locator("#total")).to_have_text("$50.00")


def normalized_code(page):
    apply_code(page, "  save10  ")
    expect(page.locator("#promo-message")).to_have_text("SAVE10 applied.")


def single_order(page):
    button = page.get_by_role("button", name="Place demo order")
    button.click()
    expect(page.locator("#confirmation")).to_contain_text("FS-0001")
    expect(button).to_be_disabled()


def smoke_check(check, page):
    locator = page.locator(check["selector"])
    expect(locator).to_be_visible()
    if "text" in check:
        expect(locator).to_have_text(check["text"])


def suite_for(profile):
    if profile["suite"] == "checkout":
        return [
            ("Initial total is $55.00", initial_total),
            ("Accepted discount updates total", discounted_total),
            ("Padded lowercase code is accepted", normalized_code),
            ("Confirmed order cannot be submitted again", single_order),
        ]
    from functools import partial
    return [(check["name"], partial(smoke_check, check)) for check in profile["checks"]]


def execute_check(browser, url, title, check, artifact_dir, index):
    result = {"name": title, "status": "passed"}
    with browser.new_context(viewport={"width": 960, "height": 820}) as context:
        page = context.new_page()
        page.set_default_timeout(4000)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=12000)
            if response is None or not response.ok:
                status = response.status if response else "no HTTP response"
                return {"name": title, "status": "error", "detail": f"Navigation returned {status}."}
            check(page)
        except (AssertionError, Error) as exc:
            result["status"] = "failed" if isinstance(exc, AssertionError) else "error"
            result["detail"] = str(exc)[:3000]
            try:
                filename = f"check-{index}.png"
                page.screenshot(path=artifact_dir / filename, timeout=4000)
                result["screenshot"] = filename
            except Error:
                pass
    return result


def start_run(profile):
    run_id = uuid4().hex
    directory = RUNS / run_id
    directory.mkdir(parents=True)
    record = {
        "id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profile": {key: value for key, value in profile.items() if key != "checks"},
        "checks": [],
    }
    expect.set_options(timeout=2500)
    try:
        with sync_playwright() as playwright:
            with playwright.chromium.launch() as browser:
                record["browser"] = f"Chromium {browser.version}"
                for index, (title, check) in enumerate(suite_for(profile), start=1):
                    result = execute_check(browser, profile["url"], title, check, directory, index)
                    record["checks"].append(result)
    except Error as exc:
        record["error"] = str(exc)[:3000]

    checks = record["checks"]
    if "error" in record or any(item["status"] == "error" for item in checks):
        record["status"] = "error"
    elif any(item["status"] == "failed" for item in checks):
        record["status"] = "failed"
    else:
        record["status"] = "passed"

    temporary = directory / "result.tmp"
    temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
    temporary.replace(directory / "result.json")
    return record


def read_run(run_id):
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid run ID.")
    path = RUNS / run_id / "result.json"
    return json.loads(path.read_text(encoding="utf-8"))


def list_runs(limit=20):
    paths = sorted(RUNS.glob("*/result.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    records = []
    for path in paths[:limit]:
        run = read_run(path.parent.name)
        profile = run["profile"]
        records.append({
            "id": run["id"], "started_at": run["started_at"], "status": run["status"],
            "environment": profile["name"], "passed": sum(
                check["status"] == "passed" for check in run["checks"]
            ), "total": len(run["checks"]),
        })
    return records
