# Google Sheets Integration

The Django database remains the source of truth. Google Sheets is an optional
copy/export destination. If posting to Google Sheets fails, the guest still
continues to the success page.

## 1. Create the Google Sheet

1. Open Google Sheets.
2. Create a new spreadsheet for guest Wi-Fi submissions.
3. Create a first sheet named `Submissions`.
4. Add these headers in row 1:

```text
session_id, created_at, full_name, email, phone, room_number,
terms_accepted, terms_accepted_at, marketing_consent, marketing_consent_at,
client_mac, ap_mac, gateway_mac, vlan_id, ssid_name, radio_id, site_name,
redirect_url, auth_status, ip_address, user_agent
```

## 2. Create the Apps Script webhook

In the sheet, open **Extensions > Apps Script** and add:

```javascript
const SHARED_SECRET = "replace-with-a-long-random-secret";

function doPost(e) {
  const payload = JSON.parse(e.postData.contents);
  if (payload.secret !== SHARED_SECRET) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: "unauthorized" }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Submissions");
  sheet.appendRow([
    payload.session_id,
    payload.created_at,
    payload.full_name,
    payload.email,
    payload.phone,
    payload.room_number,
    payload.terms_accepted,
    payload.terms_accepted_at,
    payload.marketing_consent,
    payload.marketing_consent_at,
    payload.client_mac,
    payload.ap_mac,
    payload.gateway_mac,
    payload.vlan_id,
    payload.ssid_name,
    payload.radio_id,
    payload.site_name,
    payload.redirect_url,
    payload.auth_status,
    payload.ip_address,
    payload.user_agent
  ]);

  return ContentService
    .createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

## 3. Deploy Apps Script as a Web App

1. Click **Deploy > New deployment**.
2. Choose **Web app**.
3. Set **Execute as** to yourself.
4. Set access to the appropriate external access option for your Google account.
5. Deploy and copy the Web App URL.

## 4. Configure Dokploy

Set these environment variables in Dokploy:

```env
GOOGLE_SHEETS_ENABLED=True
GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
GOOGLE_SHEETS_WEBHOOK_SECRET=replace-with-the-same-long-random-secret
GOOGLE_SHEETS_TIMEOUT_SECONDS=5
```

Keep the shared secret out of source control.

## 5. Test a form submission

1. Deploy the app with the variables above.
2. Open `/portal/`.
3. Submit the form.
4. Confirm the guest reaches `/success/`.
5. Confirm the row appears in the `Submissions` sheet.
6. In Django admin, check the session's `google_sheets_status`.

## 6. Retry failed posts

From Django admin:

1. Open **Guest wifi sessions**.
2. Select one or more records.
3. Choose **Retry sending selected sessions to Google Sheets**.
4. Confirm the `google_sheets_status`, `google_sheets_sent_at`, and
   `google_sheets_error` fields after the action runs.

From the command line:

```bash
uv run python manage.py resend_google_sheets_failed --dry-run
uv run python manage.py resend_google_sheets_failed --limit 100
```

Retries only affect rows whose `google_sheets_status` is `failed`.
