# PACS/RIS Crawler — agent notes

Hospital radiology tool that indexes PACS studies with RIS reports into Solr and lets users search, download, and transfer DICOM. Public docs: https://pacs-ris-crawler.github.io/

## Layout

Three Flask apps plus shared code. Each app loads `default_config` then overlays `instance/config.cfg` (gitignored).

| Path | Role |
|------|------|
| `crawler/` | Indexer: C-FIND / accession fetch, PACS+RIS merge, Solr JSON upload, RQ queues `index` and `prefetch` |
| `web/` | Search UI against Solr; optional download/transfer via receiver; optional LLM filter |
| `receiver/` | DICOM retrieve/transfer (`movescu` or DICOMweb); RQ queues for download/transfer |
| `common/` | Shared helpers (`text.py`, RQ dashboard patch). Apps add repo root to `sys.path` |
| `installation/` | Solr schema scripts, systemd units, nginx snippets |
| `docs/` | Sphinx sources |

Do not commit `instance/`, `receiver/image_data/`, `crawler/crawler/data/`, logs, or env files. They can contain credentials and patient data.

## Stack and commands

- Python **>= 3.12**, lockfile via **uv** (not pip/venv).
- Solr (schema under `installation/solr/`), Redis + RQ, DCMTK for DICOM C-FIND/C-MOVE.
- Tests (CI on 3.12):

```bash
uv sync
cd crawler && uv run python -m pytest
cd web && uv run python -m pytest
```

Add dependencies with `uv add`. Run one-off scripts with `uv run`.

Gunicorn working dirs match systemd: `web.app:app` from `web/`, crawler and receiver similarly. Receiver needs DCMTK; local PACS testing often uses Orthanc (`receiver/README.md`).

## Code conventions

- Keep Flask `create_app` / instance-config pattern. Secrets and AE titles belong in `instance/config.cfg`, not `default_config.py`.
- Solr nested studies use `_childDocuments_` for series (see `crawler/crawler/convert.py` and crawler tests with `tests/example.json`).
- Prefer existing `structlog` / Flask logger usage; do not print PHI.
- Web UI: Jinja + flask-assets; Swiss date (`dd.mm.yyyy`) and number formatting already exist as template filters.
- Tests: unittest/pytest style under `crawler/tests` and `web/tests`. Mock PACS/RIS/Solr; do not hit live clinical systems.

## PHI and safety

This processes identifiable clinical data (accession numbers, reports, DICOM).

- Never copy real patient identifiers, reports, or DICOM into commits, issues, logs, or chat.
- Do not run C-FIND/C-MOVE/DICOMweb or Solr uploads against production unless the user explicitly asks and config is clearly a non-prod instance.
- Treat `instance/config.cfg`, SQL/RIS credentials, and AE titles as secrets.

## Out of scope unless asked

Do not bump hardcoded `VERSION` strings in apps, rewrite Solr cores, or change DICOM AE/peer settings without an explicit request.
