"""Download order: real content first, service/temporary files last."""
import os

JUNK = ("/appdata/", "/node_modules/", "/.git/", "/cache", "/$recycle.bin/", "/system volume information/",
        "/windows/", "/program files", "/sendto/", "/leveldb/", "/service worker/", "/ntuser", "/.idea/",
        "/steamapps/", "/temp/", "/tmp/")

JUNK_NAMES = ("desktop.ini", "thumbs.db", ".ds_store")

MEDIA = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".raw", ".dng",
         ".cr2", ".nef", ".arw", ".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".mts", ".wmv", ".mp3", ".m4a",
         ".wav", ".flac", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".odt", ".rtf",
         ".zip", ".rar", ".7z"}

MIN_MEDIA_SIZE = 20 * 1024


def tier(path, size):
    """0 = photos/video/documents, 1 = everything else, 2 = temp files and system junk (last)."""
    p = path.lower()
    name = os.path.basename(p)
    if name.startswith("~$") or name in JUNK_NAMES or any(j in p for j in JUNK):
        return 2
    ext = os.path.splitext(p)[1]
    return 0 if (ext in MEDIA and size >= MIN_MEDIA_SIZE) else 1
