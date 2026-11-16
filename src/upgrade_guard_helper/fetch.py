"""Optional download of a PyPI sdist or npm tarball. Tests use local fixtures instead."""

from __future__ import annotations

import json
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

USER_AGENT = "upgrade-guard-helper/0.1.0 (+https://github.com/fitzyracing1/upgrade-guard-helper)"


def _urlopen(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=60)  # noqa: S310 — explicit http(s) URLs only


def fetch_pypi_sdist(name: str, version: str, dest: Path) -> Path:
    """Download a package from PyPI and extract it under dest. Prefer an sdist, else a wheel."""
    meta_url = f"https://pypi.org/pypi/{name}/{version}/json"
    with _urlopen(meta_url) as response:
        data = json.load(response)
    urls = data.get("urls") or []
    sdist = [u for u in urls if u.get("packagetype") == "sdist"]
    wheels = [u for u in urls if u.get("packagetype") == "bdist_wheel"]
    chosen = (sdist or wheels)
    if not chosen:
        raise FileNotFoundError(f"No sdist or wheel for {name}=={version} on PyPI")
    file_url = chosen[0]["url"]
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / Path(file_url).name
    with _urlopen(file_url) as response, archive.open("wb") as handle:
        handle.write(response.read())
    extracted = dest / "src"
    extracted.mkdir(exist_ok=True)
    _extract(archive, extracted)
    return extracted


def fetch_npm_tarball(name: str, version: str, dest: Path) -> Path:
    """Download an npm package tarball and extract it under dest."""
    # Scoped packages use the encoded form in the registry URL path.
    encoded = name.replace("/", "%2F")
    meta_url = f"https://registry.npmjs.org/{encoded}/{version}"
    with _urlopen(meta_url) as response:
        data = json.load(response)
    file_url = (data.get("dist") or {}).get("tarball")
    if not file_url:
        raise FileNotFoundError(f"No tarball for npm {name}@{version}")
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / Path(file_url).name
    with _urlopen(file_url) as response, archive.open("wb") as handle:
        handle.write(response.read())
    extracted = dest / "src"
    extracted.mkdir(exist_ok=True)
    _extract(archive, extracted)
    return extracted



def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    # filter="data" exists on 3.12+; fall back on 3.10.
    try:
        tar.extractall(dest, filter="data")
    except TypeError:
        tar.extractall(dest)


def _extract(archive: Path, dest: Path) -> None:
    if archive.suffixes[-2:] == [".tar", ".gz"] or archive.suffix in {".tgz", ".tar"}:
        with tarfile.open(archive, "r:*") as tar:
            _safe_extract(tar, dest)
    elif archive.suffix == ".whl" or archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
    else:
        # Some sdists are .tar.bz2 or .zip named unusually.
        try:
            with tarfile.open(archive, "r:*") as tar:
                _safe_extract(tar, dest)
        except tarfile.TarError:
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(dest)


def fetch_package(name: str, version: str, dest: Path, ecosystem: str) -> Path:
    if ecosystem == "npm":
        return fetch_npm_tarball(name, version, dest)
    if ecosystem == "pypi":
        return fetch_pypi_sdist(name, version, dest)
    raise ValueError(f"Unknown ecosystem {ecosystem!r}; use pypi or npm")


# Re-export urllib.error so the CLI can catch network errors without importing urllib.
URLError = urllib.error.URLError
HTTPError = urllib.error.HTTPError
