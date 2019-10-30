import pandas as pd

Main = ['UNISPITAL BASEL, HNO', 'Universitaetsspital Basel', 'Universitaetsspital',
        'RADIOLOGIE UNI BASEL', 'BILDDIAGNOSTIK BASEL', 'Universitätsspital Basel',
        'Universitätsspial Basel', 'Universitätsspital, Radiologie, Basel', 'Universitätsspital']
Pediatric = ['UKBB', 'Kinderspital UKBB', 'Kinderspital Basel']
Geriatric = ['Felix Platter Spital', 'Felixplatter Spital']


def calculate(df):
    df = df.dropna()
    df['year'] = df.apply(lambda x: str(x['StudyDate'])[0:4], axis=1)
    df['institution_type'] = df.apply(lambda x : mapping(x['InstitutionName']), axis=1)
    return df.groupby(['year','institution_type']).agg('count').reset_index()


def mapping(input):
    institution_name = input.strip()
    if institution_name in Main:
        return 'Main'
    elif 'USB' in institution_name:
        return 'Main'
    elif 'UKBB' in institution_name:
        return 'Pediatric'
    elif 'Universitaetsspital' and 'Basel' in institution_name:
        return 'Main'
    elif institution_name in Pediatric:
        return 'Pediatric'
    elif institution_name in Geriatric:
        return 'Geriatric'
    else:
        return 'Extern'