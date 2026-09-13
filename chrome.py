"""Chrome watchdog session: launch real Chrome, connect via CDP, restart on death."""

import os
import subprocess
import time
import urllib.request

import config


class ChromeSession:
    def __init__(self):
        self.proc = None
        self.browser = None
        self.ctx = None
        self.pages = {}

    def _launch(self):
        self.kill()
        time.sleep(1.0)
        config.PROFILE.mkdir(exist_ok=True)
        args = [
            config.CHROME,
            f"--user-data-dir={config.PROFILE}",
            "--no-first-run",
            "--no-default-browser-check",
            f"--remote-debugging-port={config.PORT}",
            "--window-size=1366,900",
            config.WARMUP,
        ]
        if os.environ.get("BDS_NO_SANDBOX", "1") == "1":
            args.insert(4, "--no-sandbox")  # on by default; disable for non-root Docker (BDS_NO_SANDBOX=0)
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            if self._cdp_alive():
                return
            time.sleep(1)
        raise TimeoutError("Chrome CDP not reachable")

    def _cdp_alive(self):
        try:
            with urllib.request.urlopen(f"http://localhost:{config.PORT}/json/version", timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    def alive(self):
        return self._cdp_alive()

    def kill(self):
        subprocess.run(["pkill", "-9", "-f", f"remote-debugging-port={config.PORT}"], capture_output=True, check=False)
        if self.proc:
            try:
                self.proc.kill()
            except Exception:
                pass
        self.proc = None
        self.pages.clear()

    def invalidate(self):
        """Đánh dấu browser/ctx đã chết -> lần ensure() tới sẽ reconnect."""
        self.browser = None
        self.ctx = None
        self.pages.clear()

    async def ensure(self, pw):
        """Make sure a live Chrome + CDP connection exists. Relaunch if needed."""
        if not self.alive() or self.browser is None:
            self._launch()
            self.browser = await pw.chromium.connect_over_cdp(f"http://localhost:{config.PORT}")
            self.ctx = self.browser.contexts[0]
            self.pages.clear()
        return self

    async def get_page(self, wid):
        p = self.pages.get(wid)
        if p is None or p.is_closed():
            p = await self.ctx.new_page()
            self.pages[wid] = p
        return p

    async def reset_page(self, wid):
        p = self.pages.pop(wid, None)
        if p is not None and not p.is_closed():
            try:
                await p.close()
            except Exception:
                pass

    async def close(self):
        try:
            if self.browser is not None:
                await self.browser.close()
        except Exception:
            pass
        self.kill()
