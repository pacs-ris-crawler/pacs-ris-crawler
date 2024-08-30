#!/bin/bash

# Check if the script is run as root
if [ "$EUID" -ne 0 ]
then 
  echo "Please run as root"
  exit
fi

# Define the full path to the prefect command
PREFECT_PATH="/var/www/pacs-ris-crawler/.venv/bin/prefect"

# Build PrefetchTask Deployment
$PREFECT_PATH deployment build -n "PrefetchTask Deployment" tasks/accession.py:PrefetchTask -a

# Build AccessionTask Deployment
$PREFECT_PATH deployment build -n "AccessionTask Deployment" tasks/accession.py:AccessionTask -a

# Build TriggerTask Deployment
$PREFECT_PATH deployment build -n "TriggerTask Deployment" tasks/ris_pacs_merge_upload.py:trigger_task_flow -a

# Build MergePacsRis Deployment
$PREFECT_PATH deployment build -n "MergePacsRis Deployment" tasks/ris_pacs_merge_upload.py:merge_pacs_ris_flow -a

echo "All deployments have been built."
