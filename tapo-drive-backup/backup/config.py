import os
import yaml

_DEFAULTS = {
    'lookback_days': 1,
    'local_retention_days': 0,
    'gdrive_cap_bytes': 12 * 1024 ** 3,
    'download_dir': './downloads',
    'log_dir': './logs',
    'credentials_dir': './credentials',
}

_REQUIRED = ['tapo_cli_path', 'gdrive_folder_id']


def load_config(path='config.yaml'):
    with open(path, 'r') as f:
        cfg = yaml.safe_load(f)

    for key, value in _DEFAULTS.items():
        cfg.setdefault(key, value)

    for field in _REQUIRED:
        if not cfg.get(field):
            raise ValueError(f"Missing required config field: '{field}'")

    if cfg['gdrive_folder_id'] == 'YOUR_FOLDER_ID_HERE':
        raise ValueError("Set gdrive_folder_id in config.yaml before running.")

    return cfg
