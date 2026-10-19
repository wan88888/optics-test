"""Run the existing Optics CSV suites with isolated working directories."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def configure_web_driver():
    """Project-local workaround for Optics 1.11.0's limited launch settings.

    No installed package files are changed. All actions, assertions and reports
    still run through Optics; only Playwright browser startup is extended.
    """
    from optics_framework.engines.drivers import playwright as driver_module
    from playwright.async_api import async_playwright

    class DesktopPlaywright(driver_module.Playwright):
        async def _start_browser(self):
            browser = self._setting("browser", "chromium")
            headless = self._setting("headless", False)
            maximize = self._setting("maximize", False) and not headless
            if maximize and browser != "chromium":
                raise ValueError("Window maximization requires Chromium")

            self._pw = await async_playwright().start()
            self._browser = await getattr(self._pw, browser).launch(
                headless=headless,
                slow_mo=self._setting("slow_mo", 0),
                args=["--start-maximized"] if maximize else [],
            )
            viewport = self._setting("viewport", {"width": 1280, "height": 800})
            self._context = await self._browser.new_context(
                no_viewport=True if maximize or viewport is None else None,
                viewport=None if maximize else viewport,
            )
            self._context.set_default_timeout(self.element_timeout_s() * 1000)
            self.page = await self._context.new_page()
            if maximize:
                # --start-maximized alone is unreliable on macOS.
                cdp = await self._context.new_cdp_session(self.page)
                try:
                    window = await cdp.send("Browser.getWindowForTarget")
                    await cdp.send("Browser.setWindowBounds", {
                        "windowId": window["windowId"],
                        "bounds": {"windowState": "maximized"},
                    })
                    bounds = await cdp.send("Browser.getWindowBounds", {
                        "windowId": window["windowId"],
                    })
                    if bounds["bounds"]["windowState"] != "maximized":
                        raise RuntimeError(f"Browser did not maximize: {bounds}")
                    print(f"Browser window: {bounds['bounds']}", flush=True)
                finally:
                    await cdp.detach()

    driver_module.Playwright = DesktopPlaywright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=("web", "android", "ios", "mobile"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.platform == "mobile":
        processes = []
        try:
            for platform in ("android", "ios"):
                command = [sys.executable, str(Path(__file__).resolve()), platform]
                if args.dry_run:
                    command.append("--dry-run")
                processes.append((platform, subprocess.Popen(command)))
            failed = False
            for platform, process in processes:
                status = process.wait()
                print(f"{platform}: {'PASS' if status == 0 else 'FAIL'}", flush=True)
                failed = failed or status != 0
            return int(failed)
        finally:
            for _, process in processes:
                if process.poll() is None:
                    process.terminate()
            for _, process in processes:
                process.wait()

    # Optics creates some logs relative to cwd. Each process owns its directory.
    os.chdir(ROOT / args.platform)
    if args.platform == "web":
        configure_web_driver()
    from optics_framework.helper.execute import dryrun_main, execute_main
    run = dryrun_main if args.dry_run else execute_main
    run(str(ROOT / args.platform), use_printer=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
