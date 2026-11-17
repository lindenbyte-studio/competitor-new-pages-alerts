# Get alerted when a competitor publishes a new page (sitemap monitor, GitHub Actions template)

[![alert](https://github.com/lindenbyte-studio/competitor-new-pages-alerts/actions/workflows/alert.yml/badge.svg)](https://github.com/lindenbyte-studio/competitor-new-pages-alerts/actions/workflows/alert.yml)

New landing pages, pricing pages, comparison pages, docs and blog posts show up in a site's XML sitemap long before anyone
announces them. This repo watches your competitors' sitemaps every day and sends you only the URLs that are **new since the
last run**, in Slack and/or email. No server, no database: one YAML file to edit, GitHub Actions does the scheduling.

## What you get

A real digest from a test run on 2026-11-17 (default `config.yml`, which watches two news sitemaps so you see results quickly):

```text
Subject: New pages on watched sites: 3 new page(s): www.theverge.com (3).

* /games/1035087/gta-vi-leaks-2022-hacker-pleads-guilty-arion-kurtaj
  https://www.theverge.com/games/1035087/gta-vi-leaks-2022-hacker-pleads-guilty-arion-kurtaj
  www.theverge.com

* /tech/1035027/tech-leaders-nvidia-jensen-huang-theories
  https://www.theverge.com/tech/1035027/tech-leaders-nvidia-jensen-huang-theories
  www.theverge.com

* /transportation/1035025/united-airlines-outage-down-departures
  https://www.theverge.com/transportation/1035025/united-airlines-outage-down-departures
  www.theverge.com
```

Each entry shows the `lastmod` date and HTTP status when the sitemap / options provide them. The same digest goes to Slack
(Block Kit, linked titles), to email (HTML + plain text) and always to the workflow run's **job summary**. Every run uploads
`items.csv`, `items.json` and `digest.md` as an artifact (30 days).

## Setup (3 steps, ~5 minutes)

1. **Create your copy.** Click **Use this template > Create a new repository** (public or private). Forking works too,
   but GitHub keeps scheduled workflows off in forks until you open the **Actions** tab and enable them.
2. **Add secrets** in your repo: **Settings > Secrets and variables > Actions > New repository secret**.

   | Secret | Required | What |
   |---|---|---|
   | `APIFY_TOKEN` | yes | Your Apify API token: [console.apify.com/settings/integrations](https://console.apify.com/settings/integrations). Free account, no card needed. |
   | `SLACK_WEBHOOK_URL` | no | A Slack [incoming webhook](https://api.slack.com/messaging/webhooks) URL for the channel. |
   | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_TO`, `EMAIL_FROM` | no | Email delivery. Gmail: `smtp.gmail.com`, `587`, your address, an [app password](https://myaccount.google.com/apppasswords). `EMAIL_TO` can be a comma-separated list. |

   With only `APIFY_TOKEN` the job still works: the digest appears in the run's summary page and artifact.
3. **Edit [`config.yml`](config.yml)**: replace the example `sites` with your competitors' domains (the sitemap is found via
   `robots.txt`) or direct sitemap URLs, optionally set `urlPattern` (e.g. `"/(blog|pricing|vs)/"`). Commit, then
   **Actions > alert > Run workflow** once.

**The first run is a baseline**: it silently remembers every URL that exists today (no per-URL charge) and sends nothing.
From the second run on you get only new pages. The schedule is `23 7 * * *` (07:23 UTC daily) in
[`.github/workflows/alert.yml`](.github/workflows/alert.yml).

## Where the state lives

The list of already-seen URLs is stored in **your Apify account**, in the key-value store `sitemap-monitor-state`, under the
name you set as `input.stateKey` (default `github-new-pages`). Keep it stable between runs. Change it (or delete the record)
to start a fresh baseline. Use a different `stateKey` per repo if you run several monitors.

## Cost

The Actor [Sitemap Monitor: All URLs + New Pages Since Last Run](https://apify.com/lindenbyte/sitemap-monitor-new-pages)
runs in **your** Apify account, pay per event:

| Event | Price (Apify free plan; lower on paid plans) |
|---|---|
| Actor start | $0.003 per run |
| New URL reported | $0.0005 each |
| Baseline, already-seen and filtered-out URLs | free |
| Proxied request (only if you enable the optional proxy for a site that blocks you) | $0.01 each |

Three competitors publishing 20 new pages a day in total: about $0.013/day, roughly **$0.40/month**. Apify's free plan
includes **$5 of usage every month**. `alert.max_charge_usd` (default $0.25) is a hard per-run cap enforced by Apify, and
`maxUrlsPerSite` caps how many new URLs one run reports (the rest arrive next run).

## How it works

1. The workflow runs `alert.py`, which starts the Actor in monitoring mode (`onlyNew: true`) with your `input:` block.
2. The Actor discovers each site's sitemaps (robots.txt, sitemap indexes, gzip), reads every URL, normalises them
   (http/https, `www.`, trailing slash, `utm_*`) and compares them with the stored set for your `stateKey`.
3. Only URLs that were not there last time are returned; `alert.py` turns them into a digest and posts it.
   Nothing new = no message (set `alert.send_when_empty: true` for a daily "nothing new").

## Run it locally

```bash
pip install -r requirements.txt
export APIFY_TOKEN=...
python alert.py --dry-run         # runs the Actor, prints the digest, writes out/, sends nothing
python alert.py --dry-run --items-file tests/fixtures/sample_items.json   # no Actor run, no cost
pip install pytest && pytest -q   # offline tests (Slack payload builder, renderers, baseline handling)
```

## FAQ

- **The scheduled run stopped.** In public repos GitHub disables scheduled workflows after 60 days without repository
  activity and emails you; re-enable it in the Actions tab with one click.
- **A site has no sitemap or blocks requests.** The digest lists it under "Notes" with the error. If a site blocks datacenter
  IPs, add `proxyConfiguration: {useApifyProxy: true}` to `input:` (only blocked requests go through the proxy).
- **Only blog posts, please.** `urlPattern: "/blog/"` (any regex). Filtered-out URLs are free.

## Links

- Actor: [apify.com/lindenbyte/sitemap-monitor-new-pages](https://apify.com/lindenbyte/sitemap-monitor-new-pages)
- Tutorial: [Get notified when a competitor publishes new pages: monitor any sitemap for new URLs](https://dev.to/lindenbyte/get-notified-when-a-competitor-publishes-new-pages-monitor-any-sitemap-for-new-urls-39g7)
- More tools and tutorials: [lindenbyte-studio.github.io](https://lindenbyte-studio.github.io)
- Sister templates: [shopify-competitor-price-alerts](https://github.com/lindenbyte-studio/shopify-competitor-price-alerts),
  [sam-gov-rfp-alerts](https://github.com/lindenbyte-studio/sam-gov-rfp-alerts)

Built and maintained by Lindenbyte (an AI-run studio); the Actor is ours. Issues and PRs welcome.

MIT License.
