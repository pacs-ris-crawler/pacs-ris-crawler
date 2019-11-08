from requests import post

data = {"data":[{"patient_id":"MF-0000012", "study_id":"1.3.6.1.4.1.5962.1.2.5012.1166546115.14677", "series_id":"1.3.6.1.4.1.5962.1.3.5012.2.1166546115.14677", "accession_number":"9995012", "series_number":"2"}, {"patient_id":"MF-0000008", "study_id":"1.3.6.1.4.1.5962.1.2.5008.1166546115.14677", "series_id":"1.3.6.1.4.1.5962.1.3.5008.1.1166546115.14677", "accession_number":"9995008", "series_number":"1"}, {"patient_id":"MF-0000008", "study_id":"1.3.6.1.4.1.5962.1.2.5008.1166546115.14677", "series_id":"1.3.6.1.4.1.5962.1.3.5008.1.1166546115.1467700", "accession_number":"9995008", "series_number":"1"}],
        "dir":"foo"}


def run():
  print('running post')

  headers = {
    'content-type': 'application/json',
  }
  x  = post('http://localhost:5001/receive', json=data, headers=headers)
  print(x)

if __name__ == '__main__':
  run()