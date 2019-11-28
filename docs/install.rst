Installation guide
==================

Requirements
------------

Hardware
--------
The application can run on commodity or virtualized hardware.
Typical server specs are:
* 4 Cores
* 16 GB Ram
* 100 GB System disk
* X TB Shared network drive where the images from the PACS will be stored.


Software
--------
The operation system needs to be Ubuntu 18 LTS. The following
applications/libaries are also needed:
* Solr 7.x (not compatible with Solr 8.x)
* Dcmtk
* Python 3.6
* Nginx

Interface to PACS
-----------------
For querying a PACS the PACS-RIS Crawler needs to be registered at the PACS
and the following permissions are needed:
* Right to query the PACS (C-Find)
* Right to retrieve images from the PACS (C-MOVE)

Dicom Connection properties needed
- AE_TITLE = AE-Title of the PACS-RIS registered at PACS
- AE_CALLED = AE-Title of the PACS
- PEER_ADDRESS = IP-Adress of the PACS
- PEER_PORT = Peer port of the PACS
- INCOMING_PORT = Incoming port for the images

Interface to RIS
----------------
To retrieve the RIS reports a HTTP rest interface is needed. As the query
parameter the accession number is passed.