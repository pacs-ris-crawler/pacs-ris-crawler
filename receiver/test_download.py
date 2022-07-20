from requests import post

data = {
    "data": [
        {
            "study_uid": "1.2.840.113619.6.95.31.0.3.4.1.4285.13.30196292",
            "series_uid": "1.3.12.2.1107.5.1.4.76100.30000022070602280046600129887",
            "patient_id": "USB0002314883",
            "accession_number": "30196292",
            "series_number": "5"
        },
    ],
    "dir": "foo",
}


def run():
    print("running post")

    headers = {
        "content-type": "application/json",
    }
    x = post("http://localhost:9001/download", json=data, headers=headers)
    print(x)


if __name__ == "__main__":
    run()
