# Omada Setup Guide

Use a test phone and a small guest network window before enabling this for all
guests.

## 1. Confirm the guest SSID

Create or confirm the hotel guest SSID, for example `Hotel_Guest`.

## 2. Configure external portal

In Omada Controller:

1. Open the guest network portal settings.
2. Set portal type to **External Portal Server**.
3. Set the portal URL to:

```text
https://wifi.hotel-domain.co.uk/portal/
```

The controller should append client redirect parameters such as `clientMac`,
`apMac`, `ssidName`, `radioId`, `gatewayMac`, `vid`, `site`, and `redirectUrl`.

## 3. Add pre-authentication access

Add pre-authentication access for:

- `wifi.hotel-domain.co.uk`
- The portal server IP address if Omada requires an IP rule
- Any private tunnel endpoint needed for the controller path

The portal must be reachable before the guest is authorised.

## 4. Create a Hotspot Operator account

Create a dedicated Hotspot Operator account in Omada. Do not use the main
controller admin account.

Add these credentials to Dokploy:

```env
OMADA_OPERATOR_USERNAME=<hotspot-operator-username>
OMADA_OPERATOR_PASSWORD=<hotspot-operator-password>
```

Also set:

```env
OMADA_ENABLED=True
OMADA_CONTROLLER_URL=<private-controller-url-over-vpn>
OMADA_CONTROLLER_ID=<controller-id>
OMADA_DEFAULT_SITE=<site-name>
OMADA_VERIFY_SSL=True
OMADA_TIMEOUT_SECONDS=5
```

## 5. Test with one phone

1. Forget the guest network on the phone.
2. Join the `Hotel_Guest` SSID.
3. Confirm the phone is redirected to the portal.
4. Submit the guest form.
5. Confirm the device is authorised and can browse.
6. Confirm the session appears in Django admin.
7. Confirm `auth_status` is `authorized`.

If the session is `failed`, inspect `omada_response` and `failure_reason` in
Django admin. Do not expose those details to guests.
