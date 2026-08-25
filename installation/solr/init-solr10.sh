#!/bin/bash
set -euo pipefail

# Create a Solr 10 standalone core and upload the PACScrawler schema.
# Defaults match the Solr 10 instance tunneled at localhost:8984.
#
# Solr 10 must be started with --user-managed (not the default SolrCloud):
#   bin/solr start --user-managed -p 8984
# Cloud mode CREATE fails with: coreNodeName missing {configSet=_default}
#
# Usage:
#   ./init-solr10.sh
#   ./init-solr10.sh pacs_crawler 8984
#   ./init-solr10.sh pacs_crawler 8984 /data/solr/pacs_crawler

CORE="${1:-pacs_crawler}"
PORT="${2:-8984}"
DATADIR="${3:-}"
BASE="http://localhost:${PORT}/solr"

echo "Solr 10 target: ${BASE} core=${CORE}"
if [[ -n "${DATADIR}" ]]; then
    echo "dataDir: ${DATADIR}"
fi

if curl -sS -f "${BASE}/${CORE}/admin/ping?wt=json" >/dev/null 2>&1; then
    echo "Core ${CORE} already exists, skipping CREATE"
    if [[ -n "${DATADIR}" ]]; then
        echo "Note: dataDir is only applied on CREATE. UNLOAD the core first to use a new path."
    fi
else
    echo "Creating core ${CORE} from configSet=_default (V2 /api/cores)"
    # Solr 10 standalone V1 /admin/cores?action=CREATE often fails with
    # "coreNodeName missing"; the V2 API works.
    create_body="$(DATADIR="${DATADIR}" CORE="${CORE}" python3 - <<'PY'
import json, os
body = {"name": os.environ["CORE"], "configSet": "_default"}
datadir = os.environ.get("DATADIR") or ""
if datadir:
    body["dataDir"] = datadir
print(json.dumps(body))
PY
)"
    create_resp="$(curl -sS -X POST -H 'Content-type: application/json' \
        --data-binary "${create_body}" "http://localhost:${PORT}/api/cores")"
    echo "${create_resp}"
    CREATE_RESP="${create_resp}" DATADIR="${DATADIR}" python3 - <<'PY'
import json, os, sys
resp = json.loads(os.environ["CREATE_RESP"])
if resp.get("responseHeader", {}).get("status", 1) != 0:
    err = (resp.get("error") or {}).get("msg", os.environ["CREATE_RESP"])
    print("CREATE failed:", err, file=sys.stderr)
    datadir = os.environ.get("DATADIR", "")
    if "allow.paths" in err and datadir:
        print("On the Solr host, allow the dataDir (then restart Solr), e.g. in solr.in.sh:", file=sys.stderr)
        print(f'  SOLR_OPTS="$SOLR_OPTS -Dsolr.security.allow.paths={datadir}"', file=sys.stderr)
        print("Or set SOLR_DATA_HOME in solr.in.sh and omit dataDir; confirm solr.data.home after restart.", file=sys.stderr)
    sys.exit(1)
if not resp.get("core"):
    print("CREATE failed:", os.environ["CREATE_RESP"], file=sys.stderr)
    sys.exit(1)
PY
    echo
fi

echo "Uploading PACScrawler fields to ${CORE}"
curl -sS -f -X POST -H 'Content-type:application/json' --data-binary '{
  "add-field":[
   {
     "name":"AccessionNumber",
     "type":"string",
     "docValues":true },
   {
     "name":"BodyPartExamined",
     "type":"string",
     "docValues":true },
   {
     "name":"Category",
     "type":"string",
     "docValues":true },
   {
     "name":"InstitutionName",
     "type":"text_de"},
   {
     "name":"Modality",
     "type":"string",
     "docValues":true },
   {
     "name":"PatientBirthDate",
     "type":"plong"},
   {
     "name":"PatientID",
     "type":"string",
     "docValues":true },
   {
     "name":"PatientName",
     "type":"string",
     "docValues":true },
   {
     "name":"PatientSex",
     "type":"string",
     "docValues":true },
   {
     "name":"PatientAge",
     "type":"pint",
     "docValues":true },
   {
     "name":"ProtocolName",
     "type":"text_de"},
   {
     "name":"ReferringPhysicianName",
     "type":"text_de"},
   {
     "name":"SeriesDescription",
     "type":"text_de"},
   {
     "name":"SeriesInstanceUID",
     "type":"string",
     "docValues":true },
   {
     "name":"SOPInstanceUID",
     "type":"string",
     "docValues":true },
   {
     "name":"InstanceNumber",
     "type":"string",
     "docValues":true },
   {
     "name":"StationName",
     "type":"string",
     "docValues":true },
   {
     "name":"StudyDate",
     "type":"plong" },
   {
     "name":"StudyTime",
     "type":"plong" },
   {
     "name":"StudyDescription",
     "type":"text_de"},
   {
     "name":"StudyID",
     "type":"string",
     "docValues":true },
   {
     "name":"InstanceAvailability",
     "type":"string",
     "docValues":true },
   {
     "name":"SeriesDate",
     "type":"plong" },
   {
     "name":"SeriesTime",
     "type":"plong" },
   {
     "name":"SeriesNumber",
     "type":"string",
     "docValues":true },
   {
     "name":"StudyInstanceUID",
     "type":"string",
     "docValues":true },
   {
     "name":"RisReport",
     "type":"text_de"},
   {
     "name":"Tags",
     "type":"string",
     "docValues":true }]
}' "${BASE}/${CORE}/schema"
echo

# Solr 10 _default includes _nest_path_. That marks the schema as "nested" and
# [child parentFilter=Category:parent] (Solr 7 / this app) returns 400:
# "Parent filter should not be sent when the schema is nested".
# Drop it so anonymous _childDocuments_ + parentFilter work like Solr 7.
echo "Removing _nest_path_ for Solr 7-style parent/child queries"
curl -sS -X POST -H 'Content-type:application/json' --data-binary '{
  "delete-field":{"name":"_nest_path_"}
}' "${BASE}/${CORE}/schema" || true
curl -sS -X POST -H 'Content-type:application/json' --data-binary '{
  "delete-field-type":{"name":"_nest_path_"}
}' "${BASE}/${CORE}/schema" || true
echo

echo "Done. Schema fields:"
curl -sS -f "${BASE}/${CORE}/schema/fields?wt=json" | python3 -c "import json,sys; print('\n'.join(sorted(f['name'] for f in json.load(sys.stdin)['fields'])))"
