# tapo-drive-backup

Daily pipeline: Tapo Cloud → Google Drive with automatic rotation.

Downloads the previous day's clips from Tapo Care via `tapo-cli`, uploads
new ones to a dedicated Google Drive folder, and deletes the oldest files
to keep the folder under a configurable size cap (default 12 GB).

---

## Prerequisites

- Python 3.11+
- The patched `tapo-cli` repo already checked out (see Step A1 in the project brief)
- A Google account with at least ~13 GB free

---

## 1. Install dependencies

```bash
cd tapo-drive-backup
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# WSL / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 2. Configure

Edit `config.yaml`:

```yaml
tapo_cli_path: "C:/Users/Windows 10/Desktop/Tapo/tapo-cli.py"  # adjust to your path
gdrive_folder_id: "YOUR_FOLDER_ID_HERE"   # from Drive URL: /folders/<ID>
```

The other fields have sensible defaults (see `config.yaml` for all options).

---

## 3. Google Cloud setup  ⚠️ REQUIRES CREDENTIALS (Phase B)

> Do this on the machine where you have access to your Google account.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → enable **Google Drive API**
3. **APIs & Services → Credentials → Create Credentials → OAuth Client ID**
4. Application type: **Desktop app** → Download JSON
5. Rename the downloaded file to `credentials.json`
6. Place it in `./credentials/`

---

## 4. First-run authentication  ⚠️ REQUIRES CREDENTIALS (Phase B)

Run once interactively (opens a browser):

```bash
python auth_setup.py
```

This generates `credentials/token.json`. Subsequent runs of `main.py` use the
cached token silently. If the refresh token ever expires or is revoked, rerun
`auth_setup.py` — `main.py` logs a clear ERROR and stops rather than hanging.

---

## 5. Tapo login  ⚠️ REQUIRES CREDENTIALS (Phase B)

In the patched `tapo-cli` folder (on the `patched` branch):

```bash
python tapo-cli.py login
# Enter your TP-Link ID email and password (+ MFA code if enabled)
python tapo-cli.py list-videos --days 1
# Should list yesterday's clips. If you see -20212, see troubleshooting below.
```

---

## 6. Run manually for testing

```bash
python main.py
```

Check `logs/backup.log` and your Drive folder.

---

## 7. Schedule (Windows Task Scheduler)

Create a daily trigger that runs at, say, 03:00 AM:

```
Program/script:    C:\Users\Windows 10\Desktop\tapo-drive-backup\.venv\Scripts\python.exe
Add arguments:     main.py
Start in:          C:\Users\Windows 10\Desktop\tapo-drive-backup
```

Or via `schtasks` (run once from an elevated prompt to register):

```bat
schtasks /create /tn "TapoDriveBackup" /tr "\"C:\Users\Windows 10\Desktop\tapo-drive-backup\.venv\Scripts\python.exe\" main.py" /sc daily /st 03:00 /sd 01/01/2024 /ru "Windows 10" /rp /f
```

> Before relying on the daily trigger, use the Task Scheduler "Run" button once
> to confirm it works non-interactively (no console, no browser pop-ups).

### WSL alternative

If running under WSL, add to crontab (`crontab -e`):

```
0 3 * * * cd /mnt/c/Users/Windows\ 10/Desktop/tapo-drive-backup && .venv/bin/python main.py >> logs/cron.log 2>&1
```

---

## 8. Run tests (no credentials needed)

```bash
python -m pytest tests/ -v
# or without pytest:
python -m unittest discover tests
```

All tests mock the Drive API and use a fake tapo-cli executable — no real
credentials or network access required.

---

## Project layout

```
tapo-drive-backup/
├── main.py               # entry point — runs the full pipeline
├── auth_setup.py         # run once to generate credentials/token.json
├── config.yaml           # all configuration (edit this)
├── requirements.txt
├── state.json            # auto-created; tracks uploaded filenames
├── backup/
│   ├── config.py         # loads + validates config.yaml
│   ├── tapo.py           # subprocess wrapper for tapo-cli
│   ├── gdrive.py         # Drive upload, list, rotate
│   └── state.py          # idempotency state
├── tests/
│   ├── test_tapo.py      # tapo-cli wrapper tests (fake executable)
│   ├── test_gdrive.py    # upload + rotation tests (mocked Drive API)
│   └── fixtures/
│       └── fake_tapo_cli.py
├── credentials/          # gitignored — put credentials.json here
├── downloads/            # gitignored — staging area for clips
└── logs/                 # gitignored — backup.log lives here
```

---

## Troubleshooting

**`-20212 Incorrect service entry address`**
The region patch (PR #19) should fix this by deriving the Tapo Care URL from
the regional `appServerUrl` returned at login. If it persists, check
`~/.tapo-cli/.config` and look at the `appServerUrl` value — the hostname
encodes your region (e.g. `n-aps1-wap-gw` → Asia Pacific, `n-euw1-wap-gw` →
EU West).

**`0 videos` returned consistently**
Tapo Care cloud recording may not be enabled for your camera, or the
subscription has lapsed. Confirm in the Tapo app that recordings appear for
yesterday before debugging the script.

**Google auth error on unattended run**
Rerun `python auth_setup.py` interactively. The refresh token has been revoked
(this happens if you change your Google password or revoke app access). After
re-auth, the scheduled task will work again.

**Drive folder over quota**
Adjust `gdrive_cap_bytes` in `config.yaml`. Check your actual quota at
[drive.google.com/settings/storage](https://drive.google.com/settings/storage)
— some accounts default to 5 GB until a phone number is linked.
