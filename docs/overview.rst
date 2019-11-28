Systems Overview
================

Data collection
---------------

All the patient imaging metadata is retrieved with a batch process from the PACS. That’s information about the patient and the exams. This includeds e.g. modality and series information. In a second step the information is merged with the RIS Report, based on the accession number and sent to Apache Solr. Solr is a search server with a REST API. It allows to query on all stored attributes and text with advanced full-text search like wildcards and range queries.

User interface
--------------

As the default interface to Apache Solr is not very user friendly a web application was build on top of it. It is a Python web application, the Backend is build with the Flask microframework and a HTML/JS/jQuery Frontend. It is a user friendly interface which is self explanatory. All the possible search fields are visible and e.g. multiple choice options are presented as HTML checkboxes. On the search result the user has the option to send to data to another PACS node in the network, download the images for further processing or to export the result as Excel for e.g. statistical analysis.

Receiving images
----------------
TBD