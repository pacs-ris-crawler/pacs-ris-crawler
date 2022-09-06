#!/bin/bash

if [[ $# -eq 0 ]] ; then
    echo "No argument supplied, please supply name of solr core, e.g. ./update-schema.sh pacs_core"
    exit 1
fi

CORE=$1
curl -X POST -H 'Content-type:application/json' --data-binary '{
  "add-field":[
   
   {
     "name":"PatientConsent",
     "type":"string" }]
}' http://localhost:8984/solr/$CORE/schema