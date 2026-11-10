import json
from urllib.parse import urlparse, parse_qs
import pytest
from iphone_location.geocode import search_url, parse

def test_search_url_encodes_query_and_limits_result():
    q = parse_qs(urlparse(search_url('  天安门  广场 ')).query)
    assert q['q'] == ['天安门 广场'] and q['limit'] == ['1'] and q['format'] == ['jsonv2']

def test_empty_query_rejected():
    with pytest.raises(ValueError):
        search_url('   ')

def test_parse_first_result_as_wgs84():
    payload = json.dumps([{'lat': '39.9087', 'lon': '116.3975', 'display_name': '天安门'}, {'lat': '0', 'lon': '0'}])
    assert parse(payload) == (39.9087, 116.3975, '天安门')

@pytest.mark.parametrize('payload', ['[]', '{}'])
def test_no_result(payload):
    with pytest.raises(LookupError):
        parse(payload)

def test_out_of_range_result_rejected():
    with pytest.raises(ValueError):
        parse(json.dumps([{'lat': '-89.9', 'lon': '0'}]))
