# Security Policy

## Scope

This is a POC crawler. It stores publicly available real-estate listing data.
It does not handle user credentials, payments, or PII beyond what the source
site publicly displays (agent names, masked phone numbers).

## Reporting a vulnerability

Do **not** open a public issue for a security problem. Report privately to the
JOOservices team.

## Practices

- All SQL uses parameterized statements — no string-concatenated queries.
- Crawl URLs are derived from config seeds and relative links resolved against
  the trusted base host; the crawler never follows user-supplied URLs.
- No secrets, tokens, or API keys are committed. Runtime secrets (if any) must
  come from environment variables, never source control.
- The database may contain scraped public data; treat it with the same care as
  any bulk dataset and comply with the source site's terms and applicable law.