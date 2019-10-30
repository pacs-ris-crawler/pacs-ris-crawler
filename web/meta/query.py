import logging
from datetime import datetime

DEFAULT_PAYLOAD = {'offset': 0, 'limit': 1,
                   'params': {'group': 'true', 'group.field': 'PatientID',
                              'group.limit': 100, 'group.ngroups': 'true'}
                  }


def query_body(args, limit=100):
    body = DEFAULT_PAYLOAD.copy()
    body['limit'] = limit
    if ('RisReport' not in args) or ('RisReport' in args and args.get('RisReport') == '*'):
        # Old exams have no report that is why we must match all documents.
        body['query'] = 'Category:parent'
    elif args.get("RisReport"):
        body['query'] = 'RisReport:({})'.format(args.get('RisReport','*'))
    else:
        body['query'] = 'RisReport:*'

    if args.getlist('Modality'):
        modalities = '(' + " OR ".join(args.getlist('Modality')) + ')'
        filters2 = '{!parent which=Category:parent}(+Modality:' + modalities + ')'
        if args.get('SeriesDescription'):
            body['params']['fl'] = "*,[child parentFilter=Category:parent childFilter='(Modality:{} OR SeriesDescription:{})' limit=200]".format(modalities,args.get('SeriesDescription'))
            filters1 = '{!parent which=Category:parent}(+SeriesDescription:%s)' % args.get('SeriesDescription')
            body['filter'] = _create_filter_query(args) + [filters2] + [filters1]
        else:
            body['params']['fl'] = "*,[child parentFilter=Category:parent childFilter='Modality:{}' limit=200]".format(modalities)
            body['filter'] = _create_filter_query(args) + [filters2]
    elif args.get('SeriesDescription'):
        body['params']['fl'] = "*,[child parentFilter=Category:parent childFilter='SeriesDescription:{}' limit=200]".format(args.get('SeriesDescription'))
        filters1 = '{!parent which=Category:parent}(+SeriesDescription:%s)' % args.get('SeriesDescription')
        body['filter'] = _create_filter_query(args) + [filters1]
    else:
        body['params']['fl'] = '*,[child parentFilter=Category:parent limit=200]'
        body['filter'] = _create_filter_query(args)


    body['offset'] = int(args.get('offset', '0'))
    sort_field = args.get('sort_field')
    if sort_field and sort_field != 'Default':
        body['sort'] = '{} desc'.format(sort_field)
    else:
        body['sort'] = 'StudyDate desc'
    return body


def _create_filter_query(args):
    result = [_filter('StudyDescription', args),
              _filter('PatientID', args),
              _filter('PatientName', args),
              _filter('AccessionNumber', args),
              _filter('ReferringPhysicianName', args),
              _filter('ProtocolName', args),
              _create_date('PatientBirthDate', args),
              _create_date('StudyDate', args),
              _create_date_range(args.get('StartDate'), args.get('EndDate')),
              _create_age_range(args.get('AgeFrom'), args.get('AgeTo')) ]
    return [x for x in result if x is not None]


def _filter(element, args):
    if args.get(element):
        return element + ':(' + args.get(element) + ')'


def _filter_list(element, args):
    if args.getlist(element):
        a_list = args.getlist(element)
        joined = ' OR '.join(a_list)
        return element + ':(' + joined + ')'


def _create_date(element, args):
    if args.get(element):
        return element + ':' + args.get(element)


def _create_date_range(start_date, end_date):
    if not (start_date or end_date):
        return None
    _start_date = _convert(start_date)
    _end_date = _convert(end_date)
    return 'StudyDate:[' + _start_date + ' TO ' + _end_date + ']'


def _create_age_range(age_from, age_to):
    if not (age_from or age_to):
        return None
    elif not age_to:
        return 'PatientAge:[' + age_from + ' TO *]'
    elif not age_from:
        return 'PatientAge:[* TO ' + age_to + ']'
    else:
        return 'PatientAge:[' + age_from + ' TO ' + age_to + ']'


def _convert(date):
    """
    Converts a date from the frontend which is passed in the following format
    31.12.2016 to 20161231. This is how it is stored in solr.
    """
    if date is None:
        return '*'

    try:
        return datetime.strptime(date, '%d.%m.%Y').strftime('%Y%m%d')
    except ValueError:
        logging.warning('Could not parse date %s, setting it to "*"', date)
        return '*'


def query_indexed_dates(base_query):
    return base_query + "?fl=StudyDate&q=*:*&stats.field=StudyDate&stats=true"