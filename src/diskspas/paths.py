"""Local path handling: make Yandex Disk names safe on Windows/macOS/Linux."""
import os

# Extended-length prefix on Windows (\\?\), built from char codes to avoid escaping mistakes.
LP = chr(92) * 2 + "?" + chr(92)

_BAD = '<>:"|?*' + "".join(chr(c) for c in range(32))
_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}


def safe_part(name):
    """Make one path component valid everywhere.

    Replaces characters Windows forbids, trailing dots/spaces (Windows silently strips them, which
    breaks later file operations) and reserved device names.
    """
    cleaned = "".join("_" if c in _BAD else c for c in name)
    stripped = cleaned.rstrip(" .")
    if stripped != cleaned:
        stripped += "_"
    if stripped.split(".")[0].upper() in _RESERVED:
        stripped = "_" + stripped
    return stripped or "_"


def longpath(path):
    """Absolute path; on Windows with the extended-length prefix so paths over 260 chars work."""
    path = os.path.abspath(path)
    if os.name != "nt" or path.startswith(LP):
        return path
    return LP + path


def local_path(dest, rel_posix):
    """Map a Disk-relative path like 'a/b/c.jpg' to a safe absolute local path under dest."""
    parts = [safe_part(p) for p in rel_posix.split("/") if p]
    return longpath(os.path.join(dest, *parts))
