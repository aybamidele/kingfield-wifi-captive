# Dokploy Deployment Guide

This app is designed to run on Dokploy with Railpack, Gunicorn, WhiteNoise, and
PostgreSQL. The local database is only a development fallback; production should
use `DATABASE_URL`.

## 1. Create the app

1. In Dokploy, create a new application from GitHub.
2. Select the repository: `aybamidele/kingfield-wifi-captive`.
3. Use the default branch: `main`.
4. Keep Railpack as the builder. The repository includes `railpack.json`.

## 2. Add PostgreSQL

1. Add a PostgreSQL service in Dokploy.
2. Copy the generated connection string.
3. Set it as `DATABASE_URL` on the app.

## 3. Add environment variables

Set at least:

```env
SECRET_KEY=<strong-random-secret>
DEBUG=False
ALLOWED_HOSTS=wifi.hotel-domain.co.uk
CSRF_TRUSTED_ORIGINS=https://wifi.hotel-domain.co.uk
DATABASE_URL=<dokploy-postgres-url>
DATA_RETENTION_DAYS=365
PORTAL_BRAND_NAME=Kingfield Hotel
PORTAL_TAGLINE=Guest Wi-Fi
PORTAL_PRIMARY_COLOR=#0b6b61
PORTAL_SUPPORT_TEXT=Need help? Please contact reception.
PORTAL_SUCCESS_MESSAGE=You are connected. You can now continue browsing.
DEFAULT_AUTH_MINUTES=1440
SUCCESS_REDIRECT_URL=
OMADA_ENABLED=True
OMADA_CONTROLLER_URL=<private-controller-url-over-vpn>
OMADA_CONTROLLER_ID=<controller-id>
OMADA_OPERATOR_USERNAME=<hotspot-operator-username>
OMADA_OPERATOR_PASSWORD=<hotspot-operator-password>
OMADA_VERIFY_SSL=True
OMADA_DEFAULT_SITE=<site-name>
OMADA_TIMEOUT_SECONDS=5
GOOGLE_SHEETS_ENABLED=False
```

Use a dedicated Omada Hotspot Operator account. Do not use the main Omada
controller admin account.

## 4. Set domain and HTTPS

1. Add the domain, for example `wifi.hotel-domain.co.uk`.
2. Point DNS to the Dokploy VPS.
3. Enable HTTPS in Dokploy.

## 5. Deploy

Deploy the app from Dokploy. Railpack runs the configured start command:

```bash
python manage.py migrate --noinput &&
python manage.py collectstatic --noinput &&
gunicorn wifi_portal.wsgi:application --bind 0.0.0.0:${PORT:-8000}
```

## 6. Create an admin user

Run a one-off command from Dokploy:

```bash
python manage.py createsuperuser
```

## 7. Smoke test

Confirm:

- `https://wifi.hotel-domain.co.uk/health/` returns `{"status":"ok"}`.
- `https://wifi.hotel-domain.co.uk/portal/` renders the branded portal.
- `https://wifi.hotel-domain.co.uk/terms/` renders Wi-Fi terms.
- `https://wifi.hotel-domain.co.uk/privacy/` renders the privacy notice.
- `/admin/` is available to staff over HTTPS.

## 8. Operations

Export guest data from Django admin or purge old records:

```bash
python manage.py purge_old_sessions --dry-run
python manage.py purge_old_sessions --days 365
```
