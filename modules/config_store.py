import json
import os
from typing import Dict

STORE_PATH = os.environ.get("TRENDIQ_CONFIG_PATH", "trendiq_config.json")


def _ensure_store():
    dirpath = os.path.dirname(os.path.abspath(STORE_PATH))
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    if not os.path.exists(STORE_PATH):
        with open(STORE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)


def load_keys() -> Dict[str, str]:
    try:
        _ensure_store()
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_key(provider: str, key: str) -> bool:
    try:
        _ensure_store()
        data = load_keys()
        data[provider] = key
        with open(STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception:
        return False


def get_key(provider: str) -> str:
    return load_keys().get(provider, "")


def save_provider_for_market(market: str, provider_label: str) -> bool:
    try:
        _ensure_store()
        data = load_keys()
        providers = data.get("market_providers", {})
        providers[market] = provider_label
        data["market_providers"] = providers
        with open(STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception:
        return False


def get_provider_for_market(market: str) -> str:
    return load_keys().get("market_providers", {}).get(market, "")
