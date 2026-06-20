# Live Commissioning Checklist

Use this checklist when taking the hotel captive portal live.

## Pre-deployment

- [ ] Domain points to Dokploy app.
- [ ] HTTPS certificate active.
- [ ] `/health/` returns OK.
- [ ] `/portal/` loads on mobile.
- [ ] `/terms/` loads.
- [ ] `/privacy/` loads.
- [ ] Static files load without external internet dependencies.
- [ ] PostgreSQL connected.
- [ ] Django admin works.
- [ ] Superuser created.
- [ ] Environment variables set.
- [ ] `OMADA_ENABLED=False` tested.
- [ ] `OMADA_ENABLED=True` tested in staging.

## Omada/controller

- [ ] OC200 reachable from Dokploy over VPN/tunnel.
- [ ] Hotspot Operator account created.
- [ ] Operator credentials added to Dokploy env vars.
- [ ] Controller ID configured.
- [ ] SSL verification setting configured.
- [ ] Hotel guest SSID created.
- [ ] Portal set to External Portal Server.
- [ ] Portal URL set correctly.
- [ ] Pre-Authentication Access includes portal domain/IP.
- [ ] Guest network client isolation enabled.
- [ ] Staff network separate from guest network.
- [ ] Guest speed/rate limits configured if required.

## Live test

- [ ] Connect iPhone to guest Wi-Fi.
- [ ] Captive portal opens.
- [ ] Form submits.
- [ ] Session appears in Django admin.
- [ ] Omada marks client authorised.
- [ ] Internet works.
- [ ] Marketing consent is stored correctly.
- [ ] Terms acceptance timestamp is stored.
- [ ] Repeat on Android.
- [ ] Repeat on Windows/Mac if available.
- [ ] Test invalid/missing form fields.
- [ ] Test portal when Omada API temporarily fails.

## Handover

- [ ] Document admin URL.
- [ ] Document support contact.
- [ ] Document how to export CSV.
- [ ] Document how to change portal text/logo.
- [ ] Document how to disable portal temporarily.
- [ ] Document how to switch to a simple guest password if emergency fallback is needed.

## Emergency fallback

If the external portal fails during guest hours:

1. In Omada, disable External Portal on `Hotel_Guest`, or switch temporarily to WPA password.
2. Keep guest network isolation enabled.
3. Use a temporary password at reception.
4. Restore external portal after fixing the issue.

Record when the fallback was enabled, who approved it, and when the external
portal was restored.
