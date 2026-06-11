"""Collect ANA HidroWeb conventional station series (CSV) without an account.

The public HidroWeb SPA (https://www.snirh.gov.br/hidroweb/serieshistoricas)
serves station downloads through ``rest/api/documento/download/files``. Every
anonymous visitor's browser authorizes that call with a short-lived JWT that the
front-end itself mints from a secret shipped in the public JS bundle (header
``HidroWeb-Front: Bearer <jwt>``). There is no login or user account: the token
is just the front-end's anti-CSRF handshake for an open-data portal. This script
reproduces that same handshake so a station's CSV can be fetched headlessly.

Run it yourself (it performs the network calls):

    python eda/jupia_bacia/collect_hidroweb_series.py 63003300

Raw zips and the extracted CSVs land under data/runs (gitignored); the run id
prefix is ``operational-hidroweb-jupia-``. process_context_sources.py reads the
extracted CSVs and folds them into the monthly station series (fig11).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "data" / "runs"
API = "https://www.snirh.gov.br/hidroweb/rest/api/"
# Public front-end secret, extracted from the HidroWeb JS bundle config
# (environment.TOKENSECRETKEY). It signs the anonymous "HidroWeb-Front" token
# the SPA sends on every open-data request; it is not a user credential.
FRONT_SECRET = "7f-j&CKk=coNzZc0y7_4obMP?#TfcYq%fcD0mDpenW2nc!lfGoZ|d?f&RNbDHUX6HIDROWEBBACK"

# Coletor generico: passe os codigos como argumentos de linha de comando.
# (63003300 foi verificada e NAO tem serie publicada na ANA - export vazio.)
DEFAULT_STATIONS: list[str] = []


def _b64url(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def front_token() -> str:
    """Reproduz environment-front geraToken(): JWT HS256, exp +60s."""
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64url(
        json.dumps(
            {
                "sub": str(int(time.time() * 1000) % 1_000_000),
                "iss": "HidroWeb-Front",
                "permissions": ["read", "write"],
                "exp": int(time.time()) + 60,
            },
            separators=(",", ":"),
        ).encode()
    )
    signature = hmac.new(FRONT_SECRET.encode(), header + b"." + payload, hashlib.sha256).digest()
    return (header + b"." + payload + b"." + _b64url(signature)).decode()


def headers() -> dict[str, str]:
    bearer = "Bearer " + front_token()
    return {
        "HidroWeb-Front": bearer,
        "Authorization": bearer,
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0",
    }


def download_station_zip(client: httpx.Client, code: str) -> bytes:
    """GET the CSV bundle for one station. Tries the cached file first, then
    forces a fresh server-side generation if the cache is empty."""
    last = b""
    for force in ("N", "S"):
        response = client.get(
            API + "documento/download/files",
            params={"codigoestacao": code, "tipodocumento": "csv", "forcenewfiles": force},
            headers=headers(),
            timeout=httpx.Timeout(300, connect=60),
        )
        response.raise_for_status()
        content = response.content
        # A valid bundle is a non-trivial zip (an empty zip is 22 bytes: EOCD only).
        if content[:2] == b"PK" and len(content) > 200:
            return content
        last = content
        time.sleep(1.5)
    raise RuntimeError(f"estacao {code}: download vazio (status ok, {len(last)} bytes)")


def main(stations: list[str]) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / f"operational-hidroweb-jupia-{timestamp}"
    csv_dir = run_dir / "collection" / "ana_hidroweb_csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, object]] = []
    with httpx.Client(follow_redirects=True) as client:
        for code in stations:
            try:
                blob = download_station_zip(client, code)
            except Exception as exc:  # noqa: BLE001 - segue nas demais estacoes
                print(f"  {code}: ERRO {exc}")
                results.append({"station": code, "status": "error", "notes": str(exc)[:200]})
                continue
            (run_dir / f"{code}.zip").write_bytes(blob)
            station_dir = csv_dir / code
            station_dir.mkdir(parents=True, exist_ok=True)
            extracted: list[str] = []
            with zipfile.ZipFile(BytesIO(blob)) as archive:
                for member in archive.namelist():
                    if member.lower().endswith(".csv"):
                        target = station_dir / Path(member).name
                        target.write_bytes(archive.read(member))
                        extracted.append(target.name)
            print(f"  {code}: {len(blob)} bytes, CSVs: {', '.join(extracted) or '(nenhum)'}")
            results.append({"station": code, "status": "collected", "bytes": len(blob), "csvs": extracted})

    manifest = {
        "run_id": run_dir.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "ANA HidroWeb conventional-station CSV bundles (anonymous public download).",
        "stations": stations,
        "results": results,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"collected": sum(r["status"] == "collected" for r in results), "run": str(run_dir)}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT_STATIONS)
