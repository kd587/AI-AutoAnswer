import keyring


SERVICE = "AI AutoAnswer DeepSeek"


def save_api_key(key: str) -> None:
    keyring.set_password(SERVICE, "default", key)


def load_api_key() -> str:
    return keyring.get_password(SERVICE, "default") or ""
