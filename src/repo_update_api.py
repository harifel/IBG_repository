import json
import os
import requests
import pandas as pd

import glob
import time

from collections import OrderedDict
from pathlib import Path
import numpy as np
import re

TOKEN = os.getenv("TUGRAZ_REPO_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "Environment variable TUGRAZ_REPO_TOKEN is not set. "
        "Request access via h.felic@tugraz.at or repository-support@tugraz.at."
    )

DOMAIN = os.getenv("TUGRAZ_REPO_DOMAIN", "https://repository.tugraz.at")
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


def update_json_record(directory, data_df):
    for json_file in Path(directory).glob("Paper_*.json"):
        # Extract index and title from the filename
        file_stem = json_file.stem  # Example: "Paper_1_Title"
        parts = file_stem.split("_", 2)  # Split to extract index and title
        if len(parts) < 3:
            print(f"Invalid file name format: {json_file}")
            continue

        _, index, title = parts

        matching_row = data_df[(data_df['id'].astype(str) == index)]
        if matching_row.empty:
            print(f"No matching DOI for file: {json_file}")
            continue

        doi = matching_row.iloc[0]["DOI_suf"]

        # Open and load JSON content
        with json_file.open("r", encoding="utf8") as fp:
            data = json.load(fp)

        # Create new fields with identifiers 024 and 856
        new_ids = [
            {
                "id": "024",
                "ind1": "7",
                "ind2": "",
                "subfield": f"$$2 doi $$a 10.3217/{doi}"
            },
            {
                "id": "856",
                "ind1": "4",
                "ind2": "0",
                "subfield": f"$$3 Volltext $$u https://doi.org/10.3217/{doi} $$z kostenfrei"
            }
        ]

        # Append the new IDs to metadata fields if not already present
        if isinstance(data, dict) and "metadata" in data:
            fields = data["metadata"].get("fields", [])

            # Check if the identifiers 024 and 856 already exist in fields
            existing_ids = {field["id"] for field in fields}
            if "024" not in existing_ids and "856" not in existing_ids:
                fields.extend(new_ids)
                data["metadata"]["fields"] = fields
            else:
                print(f"Identifiers already exist in file: {json_file}")
                continue
        else:
            print(f"Unexpected metadata structure in file: {json_file}")
            continue

        # Create a new OrderedDict with 'id' at the top level, followed by the rest of the data
        ordered_data = OrderedDict([("id", doi)] + list(data.items()))

        # Save the updated JSON back to the file
        with json_file.open("w", encoding="utf8") as fp:
            json.dump(ordered_data, fp, indent=4)
        print(f"Updated file: {json_file} with DOI: {doi}")




def draft(token, domain, data_model, input_json, input_metadata, directory):
    """Draft."""

    if data_model == "rdm":
        url_path = "/api/records"
    elif data_model == "marc21":
        url_path = "/api/publications"

    if input_json:
        with open(input_json, "r", encoding = "utf8") as file:
            data = json.load(file)
            #print(data)
    elif directory:
        with Path(directory + "/record.json").open("r", encoding = "utf8") as fp:
            data = json.load(fp)
            #print(data)

    if "id" in data:
        url = f"{domain}/{url_path}/{data['id']}/draft"
        time.sleep(5)
        response = put(url, data, header(token))
    else:
        url = f"{domain}/{url_path}"
        time.sleep(5)
        response = post(url, data, header(token))

    if str(response.status_code) in ["200", "201"]:
        # print(json.dumps(response.json(), indent=4))
        print(f"successfully uploaded id: {response.json()['id']}")
        # doi = response.json()['id']
    else:
        print(json.dumps(response.json(), indent=4))
        print(f"{data['id']} - error on creation: {response.status_code}")



if __name__ == "__main__":
    # Resolve data directory relative to the repository root
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"

    # Load data from the Excel file in the data directory
    data_df = pd.read_excel(data_dir / f"{data}_DOI.xlsx")

    # Call the function, specifying the directory containing the JSON files

    update_json_record(directory="", data_df=data_df)

    for json_file in Path("").glob("Paper_*.json"):
        draft(TOKEN, DOMAIN, DATA_MODEL, input_json=json_file, input_metadata=None, directory="")
