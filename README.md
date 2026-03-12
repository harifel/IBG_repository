## Repository description

This repository contains helper scripts to create and update MARC21 publication records in the TU Graz institutional repository via its HTTP API. The scripts read metadata from Excel files in the `data` folder, generate JSON records, send them as drafts to the repository and update the corresponding DOIs.  
It was created by Haris Felić from IBG @ TU Graz (`https://www.tugraz.at/en/institutes/ibg/home/`, `https://www.linkedin.com/company/ibg-tu-graz/`).

The scripts support both the TU Graz **test** instance (`https://invenio-test.tugraz.at`) and the **production** instance (`https://repository.tugraz.at`) via configuration. API access (token and domain information) must be requested from TU Graz (see contacts below); no tokens are stored in this repository.

## Structure

```
IBG_repository
├── data/                  # Excel input / output files (not tracked here)
├── src/
│   ├── repo_create_api.py # Create MARC21 drafts from Excel data
│   └── repo_update_api.py # Update JSON files with DOIs and upload
├── environment.txt        # Python dependencies
├── LICENSE
└── README.md
```

## Setup and installation (Windows / Python)

- **Create a virtual environment** (example name: `venv`):
  ```bash
  py -m venv venv
  venv\Scripts\activate
  ```

- **Install dependencies**:
  ```bash
  py -m pip install -r environment.txt
  ```

## Configuration (domains and token)

- **Token**: set the environment variable `TUGRAZ_REPO_TOKEN` to the API token you received from the repository team.  
- **Domain**:
  - For testing: set `TUGRAZ_REPO_DOMAIN` to `https://invenio-test.tugraz.at`.
  - For production: set `TUGRAZ_REPO_DOMAIN` to `https://repository.tugraz.at` (default if the variable is not set).

On Windows PowerShell you can set them like:

```powershell
$env:TUGRAZ_REPO_TOKEN = "YOUR_TOKEN_HERE"
$env:TUGRAZ_REPO_DOMAIN = "https://invenio-test.tugraz.at"
```

## Usage (high level)

- Place the required Excel files (e.g. `List_DOI.xlsx`) in the `data` folder.
- Run `repo_create_api.py` to generate JSON records and create drafts in the selected repository instance.
- Run `repo_update_api.py` to enrich JSON records with DOIs and upload them.

## What you may need to adapt

For users who are not familiar with the code, the following points are the most important to check and, if necessary, change before running the scripts:

- **Excel filenames and location**
  - Ensure your input file for creating records is named like `List_DOI.xlsx` and placed in the `data` folder (same level as `src`).
  - Ensure your file containing DOIs is named like `Liste_DOI_Fel_DOI.xlsx` and is also in the `data` folder.
  - If your filenames differ, update the `data` variable and/or the explicit filename in:
    - `repo_create_api.py` (variable `data` near the top and the `pd.read_excel(...)` call in the `__main__` block).
    - `repo_update_api.py` (the `pd.read_excel(...)` call in the `__main__` block).

- **Excel column structure**
  - `repo_create_api.py` expects, at minimum, the columns: `id`, `title`, `lang`, `given_name`, `family_name`, `identifier`, `affiliation`.
  - `repo_update_api.py` expects a column `id` and a column `DOI_suf` (the DOI suffix) for each record.
  - If your column names are different, either rename the columns in Excel or adjust the corresponding column names in the code where `groupby` and `data_df[...]` are used.

- **Metadata constants**
  - Conference-related text such as:
    - Publisher (`"Technische Universität Graz, Institut für Bodenmechanik, Grundbau und Numerische Geotechnik"`),
    - Conference name (`"40. Christian Veder Kolloquium"`),
    - Conference year (`"2026"`),
    - Publication date (`"April 2026"`),
    - Creative Commons license text and URL,
  - can all be changed in `repo_create_api.py` in the call to `create_json_record(...)` at the bottom of the file.

- **Language and access settings**
  - The language code (`lang = 'de'`) and MARC21 fields (e.g. `041`, `540`, `856`) are currently set for a specific German-language use case.
  - If you need different languages or access settings, adjust the values in the `create_json_record(...)` function in `repo_create_api.py` and in the added `024`/`856` fields in `repo_update_api.py`.

- **Repository domain (test vs production)**
  - To use the **test** repository: set `TUGRAZ_REPO_DOMAIN` to `https://invenio-test.tugraz.at`.
  - To use the **production** repository: set `TUGRAZ_REPO_DOMAIN` to `https://repository.tugraz.at` or leave it unset (default).

- **API token**
  - Always keep your API token secret and **never** hardcode it into the scripts.
  - Only set it via the environment variable `TUGRAZ_REPO_TOKEN` as described above.

If you are unsure about any of these settings, please contact the maintainers listed below before using the scripts in production.

## Support / contacts

- Technical / domain questions: `h.felic@tugraz.at`
- Repository operations and API access: `repository-support@tugraz.at` (Christoph Ladurner)

