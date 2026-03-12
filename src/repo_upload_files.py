import json
import os
from pathlib import Path

import pandas as pd
import requests


base_dir = Path(__file__).resolve().parent.parent
config_path = base_dir / "data" / "config.json"
config = {}
if config_path.is_file():
    with config_path.open("r", encoding="utf8") as f:
        config = json.load(f)

TOKEN = config.get("token") or os.getenv("TUGRAZ_REPO_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "No API token configured. Set it in data/config.json (token) or via the "
        "TUGRAZ_REPO_TOKEN environment variable. If you need access, contact "
        "h.felic@tugraz.at or repository-support@tugraz.at."
    )

DOMAIN = config.get("domain") or os.getenv("TUGRAZ_REPO_DOMAIN", "https://repository.tugraz.at")
DATA_MODEL = "marc21"
data = "Liste_DOI_template"


def header(token: str) -> dict:
    """Basic JSON header with authorization."""
    return {
        "Authorization": f"Bearer {token}",
    }


def upload_single_pdf(record_id: str, pdf_path: Path) -> None:
    """Upload a single PDF file to an existing MARC21 draft."""
    if not pdf_path.is_file():
        print(f"PDF not found for record {record_id}: {pdf_path}")
        return

    # For MARC21 publications we use the /api/publications endpoint (analogous to draft creation).
    base_url = f"{DOMAIN}/api/publications/{record_id}/draft/files"
    file_key = pdf_path.name

    # 1) Register the file in the draft
    files_payload = [{"key": file_key}]
    r = requests.post(
        base_url,
        headers={**header(TOKEN), "Content-Type": "application/json"},
        data=json.dumps(files_payload),
    )
    if r.status_code not in (200, 201):
        # If the file key already exists, we treat this as non-fatal and continue.
        try:
            err = r.json()
        except Exception:
            err = {}
        msg = err.get("message", "")
        if r.status_code == 400 and "already exists" in msg:
            print(f"[{record_id}] File {file_key} is already registered; skipping registration.")
        else:
            print(f"[{record_id}] Failed to register file: {r.status_code} {r.text}")
            return

    # 2) Upload the binary content
    content_url = f"{base_url}/{file_key}/content"
    with pdf_path.open("rb") as fp:
        r = requests.put(
            content_url,
            headers=header(TOKEN),
            data=fp,
        )
    if r.status_code not in (200, 201):
        print(f"[{record_id}] Failed to upload content: {r.status_code} {r.text}")
        return

    # 3) Commit the files to the draft
    commit_url = f"{base_url}/commit"
    r = requests.post(commit_url, headers=header(TOKEN))
    # Some backends may not support an explicit commit endpoint for MARC21;
    # in that case we ignore 405 and similar responses.
    if r.status_code not in (200, 201):
        try:
            err = r.json()
        except Exception:
            err = {}
        msg = err.get("message", "")
        if r.status_code == 405:
            print(f"[{record_id}] Commit endpoint not allowed ({r.status_code}): {msg} – continuing.")
        else:
            print(f"[{record_id}] Failed to commit files: {r.status_code} {r.text}")
            return

    print(f"[{record_id}] Successfully uploaded PDF: {file_key}")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    pdf_dir = base_dir / "pdf"

    if not pdf_dir.exists():
        raise RuntimeError(f"PDF folder not found: {pdf_dir}")

    # Expect the same Excel file that was produced by repo_create_api.py
    excel_path = data_dir / f"{data}_DOI.xlsx"
    if not excel_path.is_file():
        raise RuntimeError(f"Excel file with DOIs not found: {excel_path}")

    data_df = pd.read_excel(excel_path)

    # Expect columns:
    # - 'DOI_suf' : repository identifier (same as used in draft creation, e.g. 10.3217/... suffix)
    # - 'pdf_filename' : name of the PDF file in the pdf/ folder
    required_cols = {"DOI_suf", "pdf_filename"}
    missing = required_cols - set(data_df.columns)
    if missing:
        raise RuntimeError(
            f"Missing required columns in Excel file {excel_path}: {', '.join(sorted(missing))}"
        )

    processed_ids = set()

    for _, row in data_df.iterrows():
        record_id = str(row["DOI_suf"])
        pdf_name = str(row["pdf_filename"])

        if not record_id or not pdf_name or record_id.lower() == "nan":
            continue

        # Ensure each record_id is handled at most once per run
        if record_id in processed_ids:
            print(f"[{record_id}] Skipping duplicate row in Excel (already processed).")
            continue

        pdf_path = pdf_dir / pdf_name
        upload_single_pdf(record_id, pdf_path)
        processed_ids.add(record_id)

