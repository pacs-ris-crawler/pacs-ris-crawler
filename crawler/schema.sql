-- Create pacscrawler_studydata table
BEGIN
    CREATE TABLE curalogic.dbo.pacscrawler_studydata (
        id INT IDENTITY(1,1) PRIMARY KEY,
        acc NVARCHAR(255) NOT NULL,
        studydescription NVARCHAR(255),
        studydate NVARCHAR(50),
        start_time DATETIME2 NOT NULL,
        end_time DATETIME2 NOT NULL,
        duration_seconds FLOAT NOT NULL,
        merged_json NVARCHAR(MAX),
        created_at DATETIME2 DEFAULT GETDATE()
    )
END

