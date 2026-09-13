# Installation

## Host requirements

- **macOS** (the Cloudflare bypass requires Google Chrome on a macOS host).
- **Google Chrome** installed at
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`. Override the
  path with the `BDS_CHROME` environment variable.
- **Python 3.12+**.

> Linux/container Chrome is detected and blocked by batdongsan's Cloudflare —
> see [Architecture](../02-concepts/architecture.md). Do not expect the crawler
> to bypass from Docker/Linux.

## Set up

```bash
cd <repo>
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

`requirements.txt`:

- `playwright` — CDP control of the real Chrome.
- `curl_cffi` — kept for experimentation with TLS impersonation (not the
  working bypass path).
- `beautifulsoup4` — reserved for parsing helpers.

Playwright does **not** need its own browser download here: the crawler
connects over CDP to a separately launched Google Chrome
(`playwright install` is not required).

## Verify

```bash
.venv/bin/python -m pytest tests/ -q
```

All tests should pass without any network access (they cover price parsing and
the geo resolver against an in-memory database).