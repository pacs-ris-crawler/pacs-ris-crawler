#!/bin/bash

if [[ $# -eq 0 ]] ; then
    echo "No argument supplied, please supply name of solr core, e.g. ./update-schema.sh pacs_core"
    exit 1
fi

CORE=$1
curl -X POST -H 'Content-type:application/json' --data-binary '{
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
     "name":"PatientConsent",
     "type":"string" },
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
     "name":"StudyDate",
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
      "name":"Category",
      "type":"string",
      "docValues":true }]
}' http://localhost:8984/solr/$CORE/schema