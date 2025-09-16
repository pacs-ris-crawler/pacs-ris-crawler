import pytest

from crawler.command import accs_per_day, basic_query, prefetch_query, study_uid_query


def test_basic_query_with_custom_dcmtk_bin():
    config = {
        'DCMTK_BIN': '/custom/path/to/dcmtk',
        'AE_TITLE': 'TEST_AE',
        'AE_CALLED': 'TEST_CALLED',
        'PEER_ADDRESS': '192.168.1.100',
        'PEER_PORT': 104
    }
    
    query = basic_query(config)
    assert query.startswith('/custom/path/to/dcmtk/findscu')
    assert '-aec TEST_CALLED 192.168.1.100 104 -aet TEST_AE' in query


def test_study_uid_query_with_custom_dcmtk_bin():
    config = {
        'DCMTK_BIN': '/opt/dcmtk/bin',
        'AE_TITLE': 'TEST_AE',
        'AE_CALLED': 'TEST_CALLED',
        'PEER_ADDRESS': '10.0.0.1',
        'PEER_PORT': 4242
    }
    
    query = study_uid_query(config, 'ACC123456')
    assert query.startswith('/opt/dcmtk/bin/findscu')
    assert 'AccessionNumber=ACC123456' in query


def test_accs_per_day_with_custom_dcmtk_bin():
    config = {
        'DCMTK_BIN': '/usr/local/dcmtk',
        'AE_TITLE': 'TEST_AE',
        'AE_CALLED': 'TEST_CALLED',
        'PEER_ADDRESS': '127.0.0.1',
        'PEER_PORT': 11112
    }
    
    query = accs_per_day(config, '20231201', '0800-1600')
    assert query.startswith('/usr/local/dcmtk/findscu')
    assert 'StudyDate=20231201' in query
    assert 'StudyTime=0800-1600' in query


def test_prefetch_query_with_custom_dcmtk_bin():
    config = {
        'DCMTK_BIN': '/home/user/dcmtk/bin',
        'AE_TITLE': 'TEST_AE',
        'AE_CALLED': 'TEST_CALLED',
        'PEER_ADDRESS': '172.16.0.1',
        'PEER_PORT': 8080
    }
    
    query = prefetch_query(config, '1.2.3.4.5.6.7.8.9')
    assert query.startswith('/home/user/dcmtk/bin/movescu')
    assert 'StudyInstanceUID=1.2.3.4.5.6.7.8.9' in query


def test_default_dcmtk_bin_path():
    config = {
        'AE_TITLE': 'TEST_AE',
        'AE_CALLED': 'TEST_CALLED',
        'PEER_ADDRESS': '127.0.0.1',
        'PEER_PORT': 104
    }
    
    query = basic_query(config)
    # Should use default path when DCMTK_BIN is not specified
    assert query.startswith('/usr/bin/findscu') 