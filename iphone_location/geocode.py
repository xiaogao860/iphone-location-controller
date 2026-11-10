"""地名搜索：OpenStreetMap Nominatim，返回 WGS-84，可直接作为起点或跑道中心。
只做 URL 构造与结果解析（纯函数，便于测试）；网络请求由界面层发起。"""
import json
from urllib.parse import urlencode
from .motion import validate

ENDPOINT = 'https://nominatim.openstreetmap.org/search'
# Nominatim 使用政策要求标明应用身份
USER_AGENT = 'iPhoneLocationController/2.1 (+https://github.com/xiaogao860/iphone-location-controller)'

def search_url(query):
    q = ' '.join(str(query).split())
    if not q:
        raise ValueError('请输入地名')
    return ENDPOINT + '?' + urlencode({'q': q, 'format': 'jsonv2', 'limit': 1, 'accept-language': 'zh-CN'})

def parse(payload):
    data = json.loads(payload)
    if not isinstance(data, list) or not data:
        raise LookupError('没有找到这个地点')
    first = data[0]
    lat, lon = validate((first['lat'], first['lon']))
    return lat, lon, first.get('display_name', '')
