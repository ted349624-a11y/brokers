// Elysium Broker WL — Google Apps Script backend
// 1) Create a Google Sheet. 2) Extensions → Apps Script, paste this file.
// 3) Deploy → New deployment → Web app, Execute as: Me, Who has access: Anyone.
// 4) Copy the web app URL into SUBMIT_URL in index.html.

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(["Time", "X handle", "Wallet", "Tasks", "Status"]);
    }
    const d = JSON.parse(e.postData.contents);
    const handle = String(d.handle || "").replace(/^@/, "").toLowerCase();
    const wallet = String(d.wallet || "").toLowerCase();

    if (!/^[a-z0-9_]{1,15}$/.test(handle) || !/^0x[a-f0-9]{40}$/.test(wallet)) {
      return out({ ok: false, error: "invalid" });
    }

    const rows = sheet.getLastRow() > 1 ? sheet.getRange(2, 2, sheet.getLastRow() - 1, 2).getValues() : [];
    const dup = rows.some(r => String(r[0]).toLowerCase() === handle || String(r[1]).toLowerCase() === wallet);
    if (dup) return out({ ok: false, error: "duplicate" });

    sheet.appendRow([new Date(), "@" + handle, wallet, d.tasks || "", "Pending review"]);
    return out({ ok: true, n: sheet.getLastRow() - 1 });
  } finally {
    lock.releaseLock();
  }
}

// Used by the site's "remaining" meter
function doGet() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  return out({ count: Math.max(0, sheet.getLastRow() - 1) });
}

function out(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
