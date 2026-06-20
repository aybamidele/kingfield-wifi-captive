# OC200 Connectivity Notes

The portal server must reach the OC200 or Omada Controller API to authorise
guest devices.

## Do not expose OC200 publicly

Do not put the OC200 controller directly on the public internet. Keep the
controller on the hotel network and reach it from the Dokploy VPS using a
private network path.

## Use a VPN or tunnel

Recommended options:

- Site-to-site VPN between the Dokploy VPS and the hotel network.
- WireGuard tunnel from the hotel network to the VPS.
- Private reverse tunnel that exposes only the controller API to the VPS.

Set `OMADA_CONTROLLER_URL` to the private controller URL over that tunnel, not a
public internet URL.

## Test before enabling the portal

Before setting `OMADA_ENABLED=True`, test from inside the Dokploy container:

```bash
python - <<'PY'
import os
import requests

url = os.environ["OMADA_CONTROLLER_URL"]
response = requests.get(url, timeout=5, verify=os.environ.get("OMADA_VERIFY_SSL", "True") == "True")
print(response.status_code)
PY
```

Then test the Hotspot Operator login path with the real controller ID. Keep the
operator password in Dokploy environment variables only.

## Operational checks

- The VPS can resolve the private controller hostname.
- Firewall rules allow the VPS/tunnel IP to reach the OC200 API port.
- TLS verification matches your controller certificate setup.
- `OMADA_TIMEOUT_SECONDS` is short enough that guests do not wait too long if
  the controller is unavailable.
