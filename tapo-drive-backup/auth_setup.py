#!/usr/bin/env python3
"""
Run this ONCE interactively to generate credentials/token.json.
After that, main.py uses the cached token silently.

Usage:
    python auth_setup.py
"""
import os
import sys
import yaml
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive.file']


def main():
    if not os.path.exists('config.yaml'):
        print("ERROR: config.yaml not found. Run from the project root.")
        sys.exit(1)

    with open('config.yaml') as f:
        cfg = yaml.safe_load(f)

    credentials_dir = cfg.get('credentials_dir', './credentials')
    creds_path = os.path.join(credentials_dir, 'credentials.json')
    token_path = os.path.join(credentials_dir, 'token.json')

    if not os.path.exists(creds_path):
        print(f"\nERROR: credentials.json not found at {creds_path}")
        print(
            "\nSteps to get it:\n"
            "  1. Go to console.cloud.google.com\n"
            "  2. Create a project and enable 'Google Drive API'\n"
            "  3. APIs & Services → Credentials → Create Credentials → OAuth Client ID\n"
            "  4. Application type: Desktop app\n"
            "  5. Download JSON → rename to credentials.json → place in ./credentials/\n"
        )
        sys.exit(1)

    print("Opening browser for Google OAuth consent...")
    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
    creds = flow.run_local_server(port=0)

    os.makedirs(credentials_dir, exist_ok=True)
    with open(token_path, 'w') as f:
        f.write(creds.to_json())

    print(f"\ntoken.json saved to {token_path}")
    print("You can now run main.py unattended.")


if __name__ == '__main__':
    main()
