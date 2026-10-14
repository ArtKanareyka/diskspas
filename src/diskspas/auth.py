"""Хранение токена. Токен остаётся на этом компьютере и никогда не пишется в логи."""
import os

AUTHORIZE_URL = "https://oauth.yandex.ru/authorize?response_type=token&client_id={client_id}"


def config_dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "diskspas")


def token_file(directory=None):
    return os.path.join(directory or config_dir(), "token")


def load_token(directory=None):
    """Сначала переменная окружения YADISK_TOKEN, затем файл, сохранённый при входе."""
    env = os.environ.get("YADISK_TOKEN", "").strip()
    if env:
        return env
    try:
        with open(token_file(directory), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def save_token(token, directory=None):
    os.makedirs(directory or config_dir(), exist_ok=True)
    path = token_file(directory)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)   # доступ только владельцу
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(token.strip())
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def delete_token(directory=None):
    try:
        os.remove(token_file(directory))
        return True
    except OSError:
        return False


def authorize_url(client_id):
    return AUTHORIZE_URL.format(client_id=client_id)
