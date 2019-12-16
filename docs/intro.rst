Introduction
=============================
What is the PACS-RIS Crawler?

Why is this tool necessary?
---------------------------

The usual usecase for PACS/RIS is single patient-oriented. This is sufficient
for the clinical routine. In the research setting, where patients cohorts are
the unit of work getting the data for the cohorts is cumbersome and very
time consuming. Exams are loaded one by one in the PACS and if it matches the
research criteria they are included in the cohort.

With the PACS-Ris tool it is possible to search all exams at once with the
corresponding RIS Report. So finding all x-ray images with a e.g.
wrist fracture now takes only seconds instead of days.


How does it work
------------------

The PACS-RIS Crawler consists of mainly three modules. The crawler modules is
reponsible to querying the PACS and RIS for data and storing them. The web
frontend is web application which is the main user interface for the doctor.
The receiver module is responsible for retrieving the images from the PACS.

