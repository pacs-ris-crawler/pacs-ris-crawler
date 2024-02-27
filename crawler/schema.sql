
-- inspiration from https://github.com/commontk/CTK/blob/aa4a717152052812627a020c7f4110ccb8f7bfc8/Libs/DICOM/Core/Resources/dicom-schema.sql#L2

DROP TABLE IF EXISTS Patients;
CREATE  TABLE IF NOT EXISTS Patients (
  UID INTEGER PRIMARY KEY AUTOINCREMENT,
  PatientID VARCHAR(255) NULL ,
  PatientName VARCHAR(255) NULL ,
  PatientBirthDate DATE NULL ,
  PatientSex VARCHAR(1) NULL,
  InsertTimestamp VARCHAR(20) NOT NULL 
 );

DROP TABLE IF EXISTS Studies;
CREATE TABLE IF NOT EXISTS Studies (
  StudyInstanceUID VARCHAR(64) NOT NULL,
  PatientsUID INT NOT NULL ,
  StudyID VARCHAR(255),
  AccessionNumber VARCHAR(255) NULL,
  StudyDescription VARCHAR(255) NULL,
  StudyDate DATE NULL ,
  StudyTime TIME NULL ,
  ModalitiesInStudy VARCHAR(255) NULL ,
  InstitutionName VARCHAR(255) NULL ,
  ReferringPhysicianName VARCHAR(255) NULL ,
  RadiologyReport TEXT,
  InsertTimestamp VARCHAR(20) NOT NULL,
  PRIMARY KEY (StudyInstanceUID))
;

DROP TABLE IF EXISTS Series;
CREATE  TABLE IF NOT EXISTS Series (
  SeriesInstanceUID VARCHAR(64) NOT NULL ,
  SeriesDescription VARCHAR(255) NULL , 
  Modality VARCHAR(45) NULL,
  ProtocolName VARCHAR(255) NULL,
  BodyPartExamined VARCHAR (255) NULL,
  SeriesDate DATE NULL ,
  SeriesTime VARCHAR(20) NULL,
  SeriesNumber INT NULL,
  InsertTimestamp VARCHAR(20) NOT NULL,
  PRIMARY KEY (SeriesInstanceUID))
;