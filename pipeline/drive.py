"""Minimal Google Drive v3 client (user OAuth refresh token).

Why not a service account: service accounts have no storage quota in a personal "My Drive",
so uploads into the owner's folder fail. A refresh token for the owner's own account is used instead.
Required env: GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN (scope: drive).

Safety: this module only creates files/folders and moves files that this pipeline created.
It never deletes. Existing names are reused instead of creating duplicates.
"""
from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = json.loads((ROOT / "config/drive_folders.json").read_text())["folders"]
API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
_token: str | None = None


def token() -> str:
    global _token
    if _token:
        return _token
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GDRIVE_CLIENT_ID"], "client_secret": os.environ["GDRIVE_CLIENT_SECRET"],
        "refresh_token": os.environ["GDRIVE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    _token = r.json()["access_token"]
    return _token


def _h():
    return {"Authorization": f"Bearer {token()}"}


def find(name: str, parent: str, folder: bool | None = None) -> dict | None:
    q = [f"name = '{name.replace(chr(39), chr(92) + chr(39))}'", f"'{parent}' in parents", "trashed = false"]
    if folder is True:
        q.append("mimeType = 'application/vnd.google-apps.folder'")
    r = requests.get(f"{API}/files", headers=_h(), params={"q": " and ".join(q), "fields": "files(id,name,mimeType)"},
                     timeout=30)
    r.raise_for_status()
    files = r.json()["files"]
    return files[0] if files else None


def ensure_folder(name: str, parent: str) -> str:
    f = find(name, parent, folder=True)
    if f:
        return f["id"]
    r = requests.post(f"{API}/files", headers=_h(), json={"name": name, "parents": [parent],
                                                          "mimeType": "application/vnd.google-apps.folder"}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def upload(local: Path, parent: str, name: str | None = None) -> str:
    """Resumable upload; if a file with the same name exists in `parent`, its content is updated
    (new revision) rather than creating a duplicate."""
    name = name or local.name
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    existing = find(name, parent)
    meta = {"name": name} if existing else {"name": name, "parents": [parent]}
    url = f"{UPLOAD}/{existing['id']}" if existing else UPLOAD
    method = "PATCH" if existing else "POST"
    init = requests.request(method, url, headers={**_h(), "X-Upload-Content-Type": mime},
                            params={"uploadType": "resumable"}, json=meta, timeout=30)
    init.raise_for_status()
    with open(local, "rb") as f:
        r = requests.put(init.headers["Location"], data=f, headers={"Content-Type": mime}, timeout=600)
    r.raise_for_status()
    return r.json()["id"]


def download(file_id: str, dest: Path) -> Path:
    with requests.get(f"{API}/files/{file_id}", headers=_h(), params={"alt": "media"}, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return dest


def move(file_id: str, new_parent: str) -> None:
    r = requests.get(f"{API}/files/{file_id}", headers=_h(), params={"fields": "parents"}, timeout=30)
    r.raise_for_status()
    old = ",".join(r.json().get("parents", []))
    r = requests.patch(f"{API}/files/{file_id}", headers=_h(), params={"addParents": new_parent, "removeParents": old},
                       timeout=30)
    r.raise_for_status()


def web_link(file_id: str, folder: bool = False) -> str:
    return f"https://drive.google.com/drive/folders/{file_id}" if folder else f"https://drive.google.com/file/d/{file_id}/view"
