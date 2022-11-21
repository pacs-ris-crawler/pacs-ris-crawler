DROP TABLE IF EXISTS Patient;
CREATE  TABLE IF NOT EXISTS Patient (
  `id_Patient` INTEGER,
  `PatientName` VARCHAR(45) NULL ,
  `PatientID` VARCHAR(50) NULL ,
  `PatientBirthDate` DATE NULL ,
  `PatientAge` INT NULL,
  `PatientSex` VARCHAR(1),
  PRIMARY KEY (`id_Patient`),
  UNIQUE (`id_Patient`)
 );

DROP TABLE IF EXISTS `Study`;
CREATE  TABLE IF NOT EXISTS `Study` (
  `id_Study` INTEGER ,
  `StudyInstanceUID` VARCHAR(64) NOT NULL ,
  `StudyID` VARCHAR(32) NULL ,
  `AccessionNumber` VARCHAR(12) NOT NULL,
  `StudyDescription` VARCHAR(45) NULL,
  `StudyDate` DATE NULL ,
  `StudyTime` TIME NULL ,
  `Modality` VARCHAR(45) NULL ,
  `InstitutionName` VARCHAR(45) NULL ,
  `ReferringPhysicianName` VARCHAR(45) NULL ,
  `FK_Patient_id_Patient` INT,
  FOREIGN KEY (`FK_Patient_id_Patient`) REFERENCES `Patient` (`id_Patient`)
  PRIMARY KEY (`id_Study`),
  UNIQUE (`StudyInstanceUID`))
;

DROP TABLE IF EXISTS `Report`;
CREATE VIRTUAL TABLE IF NOT EXISTS `Report` USING FTS5(acc, radiology_report);

DROP TABLE IF EXISTS `Series`;
CREATE  TABLE IF NOT EXISTS `Series` (
  `id_Series` INTEGER ,
  `SeriesInstanceUID` VARCHAR(64) NOT NULL ,
  `SeriesDescription` VARCHAR(45) NULL ,
  `ProtocolName` VARCHAR(32) NULL,
  `BodyPartExamined` VARCHAR (12) NULL,
  `SeriesDate` DATE NULL ,
  `SeriesTime` TIME NULL ,
  `SeriesNumber` VARCHAR(4),
  `FK_Study_id_Study` INT NOT NULL ,
  FOREIGN KEY (`FK_Study_id_Study` ) REFERENCES `Study` (`id_Study` )
  PRIMARY KEY (`id_Series`),
  UNIQUE (`SeriesInstanceUID`))
;
DROP TABLE IF EXISTS `Image`;

CREATE  TABLE IF NOT EXISTS `Image` (
  `id_Image` INTEGER ,
  `SOPInstanceUID` VARCHAR(64) NOT NULL ,
  `Number` INT NULL ,
  `PatientPosition` VARCHAR(64) NULL ,
  `SliceThickness` FLOAT NULL ,
  `FileName` VARCHAR(4096) NULL ,
  `FK_Series_id_Series` INT NOT NULL ,
  FOREIGN KEY (`FK_Series_id_Series` ) REFERENCES `Series` (`id_Series` )
  PRIMARY KEY (`id_Image`),
  UNIQUE (`SOPInstanceUID`))
;