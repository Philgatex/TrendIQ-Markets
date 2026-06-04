import os


def get_env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


APP_ENV = os.environ.get("APP_ENV", "production").strip().lower()
IS_STAGING = APP_ENV == "staging"
IS_DEVELOPMENT = APP_ENV in {"development", "dev"}
IS_PRODUCTION = APP_ENV == "production"

BINANCE_TESTNET = get_env_bool("BINANCE_TESTNET", False)
BINANCE_ALLOW_LIVE_ORDERS = get_env_bool("BINANCE_ALLOW_LIVE_ORDERS", False)
