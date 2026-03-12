# -*- coding: utf-8 -*-
"""
Created on Tue Oct 22 13:16:35 2024

@author: haris
"""
import json
import os
import requests
import pandas as pd

from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from pathlib import Path
import numpy as np

import re


base_dir = Path(__file__).resolve().parent.parent
config_path = base_dir / "data" / "config.json"
config = {}
if config_path.is_file():
    with config_path.open("r", encoding="utf8") as f:
        config = json.load(f)

# Prefer local config.json, fall back to environment variables
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


def header(token):
    """Header."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def post(url, data, headers):
    """Post."""
    return requests.post(url, headers=headers, json=data)


def put(url, data, headers):
    """Put."""
    return requests.put(url, headers=headers, json=data)


def create_json_record(title, authors, publisher, publication_date, lang, long_creative_common, short_creative_common, url_creative_common, index, conference_name, conference_year):
    """Create JSON structure for a record."""
    # Sanitize the title for use in the filename
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)  # Replacing special characters with '_'

    # Erstelle das Subfield für den Hauptautor
    subfield_value = f"$$a {authors[0]['family_name']}, {authors[0]['given_name']} $$u {authors[0]['affiliation']}"
    if not pd.isna(authors[0]['identifier']) and authors[0]['identifier']:
        subfield_value += f" $$2 {authors[0]['identifier']}"

    # Base structure with dynamic values
    record = {
        "access": {
            "record": "public",
            "files": "public",
            "embargo": {
                "active": False,
                "reason": None
            },
            "status": "metadata-only",
        },
        "metadata": {
            "fields": [
                {
                    "id": "008",
                    "ind1": "",
                    "ind2": "",
                    "subfield": f"#######{conference_year}#############################"
                },
                {
                    "id": "041",
                    "ind1": "_",
                    "ind2": "_",
                    "subfield": f"$$a {lang}"
                },
                {
                    "id": "100",
                    "ind1": "1",
                    "ind2": "",
                   "subfield": f"{subfield_value}"
                },
                {
                    "id": "245",
                    "ind1": "1",
                    "ind2": "0",
                    "subfield": f"$$a {title}"
                },
                {
                    "id": "264",
                    "ind1": " ",
                    "ind2": "",
                    "subfield": f"$$b {conference_name}, {publisher} $$c {conference_year}"
                },
                {
                    "id": "300",
                    "ind1": "_",
                    "ind2": "_",
                    "subfield": f"$$a {publisher} $$b {publication_date}"
                },
                {
                    "id": "500",
                    "ind1": " ",
                    "ind2": " ",
                    "subfield": f"$$a {conference_name}, Konferenzbeitrag_{index}"
                },
                {
                    "id": "540",
                    "ind1": " ",
                    "ind2": " ",
                    "subfield": f"$$a {long_creative_common} $$f {short_creative_common} $$u {url_creative_common} $$2 cc"
                },
                {
                    "id": "970",
                    "ind1": "2",
                    "ind2": "",
                    "subfield": f"$$b {conference_year} $$c Technische Universität Graz $$d Konferenzbeitrag"
                },
            ],
            "leader": "00000nam a2200000zca4500"
        },
    }

    # Add any additional authors if present
    for author in authors[1:]:
        subfield_value = f"$$a {author['family_name']}, {author['given_name']} $$u {author['affiliation']}"
        if not pd.isna(author['identifier']) and author['identifier']:
            subfield_value += f" $$2 {author['identifier']}"

        record["metadata"]["fields"].append({
            "id": "700",
            "ind1": "1",
            "ind2": " ",
            "subfield": f"{subfield_value}"
        })


    # Save the JSON file with the sanitized title inside the data directory
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)
    json_path = data_dir / f"Paper_{index}_{safe_title}.json"
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"Record saved for title: {title}")



def draft(token, domain, data_model, input_json, input_metadata, directory):
    """Draft."""

    if data_model == "rdm":
        url_path = "/api/records"
    elif data_model == "marc21":
        url_path = "/api/publications"

    if input_json:
        with open(input_json, "r", encoding = "utf8") as file:
            data = json.load(file)
            # print(data)
    elif directory:
        with Path(directory + "/record.json").open("r", encoding = "utf8") as fp:
            data = json.load(fp)
            # print(data)

    if "id" in data:
        url = f"{domain}/{url_path}/{data['id']}/draft"
        response = put(url, data, header(token))
    else:
        url = f"{domain}/{url_path}"
        response = post(url, data, header(token))

    if str(response.status_code) in ["200", "201"]:
        # print(json.dumps(response.json(), indent=4))
        print(f"\t successfully created id: {response.json()['id']}")
        doi = response.json()['id']
        return doi
    else:
        print(json.dumps(response.json(), indent=4))
        print(f"error on creation: {response.status_code}")




if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"

    # Read the data from the Excel file located in the data directory
    data_df = pd.read_excel(data_dir / f"{data}.xlsx")  # Reading the file containing all relevant data
    data_df['DOI_pre'] = r"10.3217/"  # Initialize DOI column
    data_df['DOI_suf'] = None  # Initialize DOI column

    # Group authors by id and title
    grouped_data = data_df.groupby(['id', 'title', 'lang']).apply(
        lambda x: x[['given_name', 'family_name', 'identifier', 'affiliation', 'lang']].to_dict(orient='records')
    ).reset_index()

    # Loop through each group (unique id and title)
    for index, row in grouped_data.iterrows():
        record_id = row["id"]  # Get the ID for the current record
        title = row["title"]
        lang = 'de'
        authors = row[0]  # This will hold the list of authors for the current record

        json_record = create_json_record(
            title=title,
            authors=authors,
            publisher="Technische Universität Graz, Institut für Bodenmechanik, Grundbau und Numerische Geotechnik",
            publication_date="April 2026",
            lang=lang,
            long_creative_common="Creative Commons namensnennung",
            short_creative_common="CC By 4.0 DEED Lizenz",
            url_creative_common="https://creativecommons.org/license/by/4.0",
            index=record_id,
            conference_name="40. Christian Veder Kolloquium",
            conference_year="2026"
        )
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)  # Replacing special characters with '_'
        # Get the DOI for the current record
        json_input_path = data_dir / f"Paper_{record_id}_{safe_title}.json"
        doi = draft(TOKEN, DOMAIN, DATA_MODEL, input_json=str(json_input_path), input_metadata=None, directory="")

        # Assign DOI for each author in the current record
        if doi == None:
            None
        else:
            for author in authors:
                data_df.loc[data_df['id'] == record_id, 'DOI_suf'] = doi
                data_df.to_excel(data_dir / f"{data}_DOI.xlsx", index=False)
