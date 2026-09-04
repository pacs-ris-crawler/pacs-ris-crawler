#!/bin/bash

if [[ $# -ne 2 ]] ; then
    echo "No or not enough arguments supplied, please supply name of solr core and port, e.g. ./update-schema.sh pacs_core 8984"
    exit 1
fi

CORE=$1
PORT=$2
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
     "type":"string",
     "docValues":true },
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
     "type":"string",
     "docValues":true },
   {
     "name":"ReferringPhysicianName",
     "type":"string",
     "docValues":true },
   {
     "name":"SeriesDescription",
     "type":"string",
     "docValues":true },
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
     "name":"StudyDate",
     "type":"plong" },
   {
     "name":"StudyTime",
     "type":"plong" },
   {
     "name":"StudyDescription",
     "type":"string",
     "docValues":true },
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
}' http://localhost:$PORT/solr/$CORE/schema