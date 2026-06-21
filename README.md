# Kingfield Wi-Fi Captive Portal

Django external captive portal MVP for a TP-Link Omada guest Wi-Fi network.
It provides a branded mobile-first portal, stores guest consent and Omada
redirect parameters, and exposes Django admin for session review.

## Stack

- Python 3.12+
- Django 6.x
- PostgreSQL in production
- SQLite fallback for local development when `DATABASE_URL` is unset
- Gunicorn
- WhiteNoise
- django-environ
- requests
- pytest + pytest-django
- uv
- Invoke
- Railpack

## Local setup

```bash
uv sync
cp .env.example .env
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run inv runserver
```

Open:

- `http://127.0.0.1:8000/portal/`
- `http://127.0.0.1:8000/terms/`
- `http://127.0.0.1:8000/privacy/`
- `http://127.0.0.1:8000/health/`
- `http://127.0.0.1:8000/admin/`

## Common commands

```bash
uv run inv install
uv run inv makemigrations
uv run inv migrate
uv run inv collectstatic
uv run inv test
uv run inv runserver
uv run inv gunicorn
```

## Environment variables

| Variable | Required | Notes |
| --- | --- | --- |
| `SECRET_KEY` | yes in production | Django secret key. |
| `DEBUG` | yes | Use `false` in production. |
| `ALLOWED_HOSTS` | yes | Comma-separated hostnames. |
| `CSRF_TRUSTED_ORIGINS` | production HTTPS | Comma-separated trusted origins, including scheme. |
| `DATABASE_URL` | production | PostgreSQL URL. If unset, local SQLite is used. |
| `DATA_RETENTION_DAYS` | no | Guest Wi-Fi session retention period. Defaults to `365`. |
| `PORTAL_BRAND_NAME` | no | Defaults to `Kingfield Hotel`. |
| `PORTAL_TAGLINE` | no | Short text shown above the brand name. |
| `PORTAL_LOGO_URL` | no | Prefer local/static URLs because unauthenticated guests may not have internet access. |
| `PORTAL_BACKGROUND_URL` | no | Prefer local/static URLs for captive portal reliability. |
| `PORTAL_ALLOWED_REDIRECT_HOSTS` | no | Extra comma-separated hosts allowed for Omada `redirectUrl`. |
| `PORTAL_PRIMARY_COLOR` | no | Primary button and brand colour. Defaults to `#0b6b61`. |
| `PORTAL_SUPPORT_TEXT` | no | Help text shown below portal cards. |
| `PORTAL_SUCCESS_MESSAGE` | no | Success page body copy. |
| `PORTAL_RATE_LIMIT_ENABLED` | no | Enables cache-based submit rate limiting. Defaults to `True`. |
| `PORTAL_RATE_LIMIT_ATTEMPTS` | no | Submit attempts per IP per window. Defaults to `20`. |
| `PORTAL_RATE_LIMIT_WINDOW_SECONDS` | no | Submit rate-limit window. Defaults to `60`. |
| `DEFAULT_AUTH_MINUTES` | no | Defaults to `1440`. |
| `SECURE_SSL_REDIRECT` | production | Redirect HTTP to HTTPS when behind a correctly configured proxy. |
| `SUCCESS_REDIRECT_URL` | no | If unset, successful submissions redirect to `/success/`. |
| `OMADA_ENABLED` | no | Enables Omada Hotspot API authorisation. Defaults to `False`. |
| `OMADA_CONTROLLER_URL` | when enabled | Base Omada controller URL. |
| `OMADA_CONTROLLER_ID` | when enabled | Controller ID path segment used by the Hotspot API. |
| `OMADA_OPERATOR_USERNAME` | when enabled | Dedicated Hotspot Operator username. Do not use the controller admin account. |
| `OMADA_OPERATOR_PASSWORD` | when enabled | Dedicated Hotspot Operator password. |
| `OMADA_VERIFY_SSL` | no | Verify Omada controller TLS certificates. Defaults to `True`. |
| `OMADA_DEFAULT_SITE` | when enabled | Fallback site when Omada does not send `site`. |
| `OMADA_TIMEOUT_SECONDS` | no | Request timeout for Omada API calls. Defaults to `5`. |
| `GOOGLE_SHEETS_ENABLED` | no | Enables optional Apps Script webhook posting. Defaults to `False`. |
| `GOOGLE_SHEETS_WEBHOOK_URL` | when enabled | Google Apps Script Web App URL. |
| `GOOGLE_SHEETS_WEBHOOK_SECRET` | when enabled | Shared secret sent in the webhook payload. |
| `GOOGLE_SHEETS_TIMEOUT_SECONDS` | no | Short webhook timeout. Defaults to `5`. |

## Portal UI customization

Edit portal branding and copy in Django admin under **Portal customization**.
Create one customization record; its values override the `PORTAL_*` environment
variables used by the public portal. If no customization record exists, the app
continues to use `.env` values as bootstrap defaults.

See `docs/google-sheets-integration.md` for setup and retry instructions.
See `docs/dokploy-deployment.md`, `docs/omada-setup.md`, and
`docs/oc200-connectivity.md` for production deployment and controller setup.

## Omada external portal parameters

The portal accepts and stores these query/post parameters:

- `clientMac`
- `apMac`
- `gatewayMac`
- `vid`
- `ssidName`
- `radioId`
- `site`
- `redirectUrl`
- `t`

Omada should send guests to `/portal/` with these parameters. The page keeps
them as hidden form fields and stores them on submit.

## Compliance notes

Terms acceptance and marketing consent are separate checkboxes. Terms acceptance
is required for access. Marketing consent is optional, is not pre-ticked, and
is not required for internet access. Both consent timestamps are stored when
applicable, along with client IP and user agent.

## Dokploy / Railpack deployment

This repository includes `railpack.json`. Railpack detects the Python project
from `pyproject.toml`/`uv.lock` and Django from `manage.py` plus the Django
dependency.

Dokploy environment variables should include:

```text
SECRET_KEY=<strong-secret>
DEBUG=false
ALLOWED_HOSTS=<your-domain>
CSRF_TRUSTED_ORIGINS=https://<your-domain>
DATABASE_URL=<dokploy-postgres-url>
PORTAL_BRAND_NAME=Kingfield Hotel Wi-Fi
DEFAULT_AUTH_MINUTES=1440
```

The Railpack start command runs:

```bash
python manage.py migrate --noinput &&
python manage.py collectstatic --noinput &&
gunicorn wifi_portal.wsgi:application --bind 0.0.0.0:${PORT:-8000}
```

After deployment, verify:

- `https://<your-domain>/health/`
- `https://<your-domain>/portal/`
- `https://<your-domain>/terms/`
- `https://<your-domain>/privacy/`

## Current limitation

This MVP stores Omada redirect/session data but does not call the Omada
controller authorization API. That integration needs the controller endpoint,
site ID behaviour, API version, and credential/token flow before it can be
implemented safely.
