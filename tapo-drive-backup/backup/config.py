import os
import yaml

_DEFAULTS = {
    "lookback_days": 2,
    "local_retention_days": 0,
    "download_dir": "./downloads",
    "log_dir": "./logs",
}


def load_config(path="config.yaml"):
    with open(path) as f:
        cfg = yaml.safe_load(f)

    cfg = _DEFAULTS | cfg  # config file values override defaults

    cfg["tapo_password"] = os.environ.get("TAPO_PASSWORD", "")

    srv = cfg.setdefault("server", {})
    for env_key, cfg_key in [
        ("SSH_HOST", "host"),
        ("SSH_USER", "username"),
        ("SSH_PASSWORD", "password"),
        ("SSH_KEY_PATH", "key_path"),
        ("SSH_REMOTE_DIR", "remote_dir"),
    ]:
        if os.environ.get(env_key):
            srv[cfg_key] = os.environ[env_key]
    if os.environ.get("SSH_PORT"):
        srv["port"] = int(os.environ["SSH_PORT"])

    if not cfg.get("cameras"):
        raise ValueError("No cameras configured in config.yaml")
    if not cfg.get("tapo_password"):
        raise ValueError("TAPO_PASSWORD not set — add it to your .env file")

    return cfg
