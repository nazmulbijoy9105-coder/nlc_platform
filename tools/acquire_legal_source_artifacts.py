#!/usr/bin/env python3
"""Acquire official-source artifacts from the NLC legal interval register.

This utility preserves downloaded bytes and computes SHA-256. It does NOT
authenticate legal validity, issuer competence, OCR, commencement, or scope.
Those require human/source review and must remain separate release gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_HOSTS = {
    "dpp.gov.bd", "www.dpp.gov.bd",
    "bdlaws.minlaw.gov.bd", "www.bdlaws.minlaw.gov.bd",
    "bsec.gov.bd", "www.bsec.gov.bd",
    "bb.org.bd", "www.bb.org.bd",
    "bangladesh-bank.org", "www.bangladesh-bank.org",
    "nbr.gov.bd", "www.nbr.gov.bd",
    "bida.gov.bd", "www.bida.gov.bd",
}
MAX_BYTES = 40 * 1024 * 1024
TIMEOUT_SECONDS = 45


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(source_id: str, url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in {".pdf", ".html", ".htm", ".doc", ".docx", ".zip"}:
        suffix = ".bin"
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_id)[:100]
    return clean + suffix


def fetch(url: str, destination: Path) -> dict:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS:
        return {"url": url, "status": "REJECTED_URL", "error": "HTTPS and allowlisted official host required"}

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "NLC-Legal-Source-Acquisition/1.0"},
    )
    started = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            final_host = (urlparse(response.geturl()).hostname or "").lower()
            if final_host not in ALLOWED_HOSTS:
                return {"url": url, "status": "REJECTED_REDIRECT", "final_url": response.geturl()}
            content_type = response.headers.get("Content-Type", "")
            length_header = response.headers.get("Content-Length")
            if length_header and int(length_header) > MAX_BYTES:
                return {"url": url, "status": "REJECTED_SIZE", "content_length": int(length_header)}
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return {"url": url, "status": "REJECTED_SIZE", "bytes_read": len(data)}
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation avoids silently overwriting an acquired artifact.
            with destination.open("xb") as output:
                output.write(data)
            return {
                "url": url,
                "retrieved_at_utc": started,
                "http_status": response.status,
                "final_url": response.geturl(),
                "content_type": content_type,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "local_path": str(destination),
                "status": "DOWNLOADED_BYTES_UNAUTHENTICATED",
            }
    except FileExistsError:
        return {
            "url": url, "status": "FILE_EXISTS_NOT_OVERWRITTEN",
            "local_path": str(destination), "existing_sha256": sha256_file(destination),
        }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"url": url, "status": "DOWNLOAD_FAILED", "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--source-id", action="append", help="Acquire only selected source IDs; repeatable")
    args = parser.parse_args()

    register = json.loads(args.register.read_text(encoding="utf-8"))
    sources = register.get("located_primary_record_anchors", [])
    selected = set(args.source_id or [])
    records = []
    for source in sources:
        source_id = source.get("source_id", "UNKNOWN")
        if selected and source_id not in selected:
            continue
        url = source.get("gazette_pdf_url") or source.get("official_document_url")
        if not url:
            records.append({"source_id": source_id, "status": "NO_ARTIFACT_URL"})
            continue
        path = args.out / safe_name(source_id, url)
        result = fetch(url, path)
        result["source_id"] = source_id
        result["instrument"] = source.get("instrument")
        records.append(result)

    manifest = {
        "manifest_type": "NLC_ORIGINAL_SOURCE_BYTE_ACQUISITION",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "register_as_of": register.get("as_of_date"),
        "warning": "Downloaded bytes and SHA-256 do not establish legal authenticity, validity, commencement, scope, or operative effect.",
        "records": records,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out / "acquisition_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(manifest_path)
    print(f"records={len(records)} downloaded={sum(r.get('status') == 'DOWNLOADED_BYTES_UNAUTHENTICATED' for r in records)} failed={sum(r.get('status') != 'DOWNLOADED_BYTES_UNAUTHENTICATED' for r in records)}")
    return 0 if records and all(r.get("status") == "DOWNLOADED_BYTES_UNAUTHENTICATED" for r in records) else 2


if __name__ == "__main__":
    sys.exit(main())
