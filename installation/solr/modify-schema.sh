#!/bin/bash

# Additive schema update for an existing Solr 7.7 core.
# Adds SOPInstanceUID and InstanceNumber only; does not require a full reindex.
# Existing documents stay valid and get these fields when those studies are re-uploaded.

if [[ $# -ne 2 ]] ; then
    echo "No or not enough arguments supplied, please supply name of solr core and port, e.g. ./modify-schema.sh pacs_crawler 8983"
    exit 1
fi

CORE=$1
PORT=$2

curl -X POST -H 'Content-type:application/json' --data-binary '{
  "add-field":[
   {
     "name":"SOPInstanceUID",
     "type":"string",
     "docValues":true },
   {
     "name":"InstanceNumber",
     "type":"string",
     "docValues":true }]
}' "http://localhost:${PORT}/solr/${CORE}/schema"
echo
