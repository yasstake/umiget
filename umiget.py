from requests_html import HTMLSession
import urllib
import json
from time import sleep
'''
See request_html docummentation at;
https://html.python-requests.org/
'''


class Umi:
    LAYER_LIST='https://www.msil.go.jp/msilgisapi/api/layer/layer'


    def __init__(self):
        self.session = HTMLSession()
        self.headers = {'Content-Type': 'application/json', 'Origin': 'https://www.msil.go.jp',
           'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) Chrome/74.0.3729.131 Safari/537.36',
            'X-Requested-With':'XMLHttpRequest'}
        self.token = None
        self.base_url = 'https://www.msil.go.jp/arcgis/rest/services/Msil/'

    def login(self):
        SESSION =  'https://www.msil.go.jp/msilgisapi/api/common/session'
        r = self.session.post(SESSION, headers=self.headers)

        TOKEN ='https://www.msil.go.jp/msilwebtoken/api/token/new';
        r = self.session.post(TOKEN, headers=self.headers)

        self.token = r.json()['token']

    def make_params(self, params, query=False):
        if self.token:
            params['token'] = self.token

        params['f'] = 'json'

        if query:
            params['returnGeometry']='true'
            params['spatialRel']='esriSpatialRelIntersects'
            params['geometryType'] = 'esriGeometryEnvelope'
            params['inSR'] = '4326'
            params['outSR'] = '4326'

        encode = urllib.parse.urlencode(params)
        return encode

    def get(self, path, params, query=True):
        url = self.base_url + path + '?' + self.make_params(params, query)
        r = self.session.get(url, headers=self.headers)
        print(r.text)
        return r

    def get_inventory(self, path):
        url = self.base_url + path + '?f=json&token=' + self.token
        r = self.session.get(url, headers=self.headers)

        print(r.text)
        return r

    def parse_inventory(self, inventory):
        j = json.loads(inventory)
        print(j)

        extent = j['extent']
        extents = (extent['xmin'], extent['ymin'], extent['xmax'], extent['ymax'])

        fields = j['fields']

        field = []
        for f in fields:
            if f['name'] != 'OBJECTID' and f['name'] != 'Shape':
                field.append(f['name'])

        return extents, field

    def query_data(self, path):
        r = self.get_inventory(path)
        extent, fields = self.parse_inventory(r.text)

        params = {}
        params['geometry'] = ",".join(map(str, extent))
        params['outFields']= ",".join(map(str, fields))

        result  = None
        for x in range(int(extent[0]), int(extent[2])+2):
            for y in range(int(extent[1]), int(extent[3])+2):
                print(x, y)

                sleep(0.5)
                params['geometry'] = ",".join(map(str, (x, y, x+1, y+1)))
                r = self.get(path + '/query', params, True)

                if result is None:
                    result = r.json()
                else:
                    features = r.json()['features']

                    if len(features) != 0:
                        result['features'].extend(features)

        return result


    def get_light_house(self):
        r = self.query_data('Maritime/MapServer/15')
        print(r)


        '''
        r = self.get_inventory('Maritime/MapServer/15')
        print(r)

        path = 'Maritime/MapServer/15/query'

        params={'geometry': '122.93441666700005, 20.40138888900003, 147.9173333330001, 45.52161111100003'}
        #params= {'geometry': '15195116.527334847,3907016.8728159033,15977831.696974836,4689732.0424559'}
        params['outFields'] = '航路標識番号, 名称, 読み, 出典, データ年度, 調査年度, 標識種別, 灯フラグ, F9, F11'
        r = self.get(path, params, True)

        print(r)
        '''

    def get_query(self, url):
        URL = 'https://www.msil.go.jp/arcgis/rest/services/Msil/Society/MapServer/7/query?'
        param = '&f=json&returnGeometry=true&spatialRel=esriSpatialRelIntersects&geometry=15155980.768862816,3711338.080405904,22%3A15938695.938502813,4494053.250045901&geometryType=esriGeometryEnvelope&inSR=102100&outSR=102100'

        url = URL + 'token=' + self.token + param

        r = self.session.post(url, headers=self.headers)

        URL=  'https://www.msil.go.jp/arcgis/rest/services/Msil/Maritime/MapServer/15/query?'
        param='&f=json&returnGeometry=true&spatialRel=esriSpatialRelIntersects&geometryType=esriGeometryEnvelope&inSR=102100&outSR=102100'

        geometry='&geometry=127.71372222200011,26.191027778000034,145.83574788900012,45.526393796000036'
        geometry='&geometry="15195116.527334847,3907016.8728159033,15977831.696974836,4689732.0424559"'
        #geometry='{"xmin":15195116.527334847,"ymin":3907016.8728159033,"xmax":15977831.696974836,"ymax":4689732.0424559,"spatialReference":{"wkid":102100}}'

        outfeilds='&outFields=所在地,免許番号,漁業権の種類,営む漁業種類,操業_養殖_時期,免許有効期間,面積,外周,備考,出典・情報提供者,データ年度'

        url = URL + 'token=' + self.token + param + geometry + outfeilds
        url = URL + 'token=' + self.token + param + geometry

        r = self.session.post(url, headers=self.headers)

        print('--------------------')
        print(r.headers)
        print(r.text)




'''
https://www.msil.go.jp/arcgis/rest/services/Msil/Society/MapServer/7/query
token: <token>
f: json
returnGeometry: true
spatialRel: esriSpatialRelIntersects
geometry: {"xmin":15155980.768862816,"ymin":3789609.5973699037,"xmax":15938695.938502813,"ymax":4572324.767009901,"spatialReference":{"wkid":102100}}
geometryType: esriGeometryEnvelope
inSR: 102100
outFields: 所在地,免許番号,漁業権の種類,営む漁業種類,操業_養殖_時期,免許有効期間,面積,外周,備考,出典・情報提供者,データ年度
orderByFields: objectid
outSR: 102100

'''


'''


https://www.msil.go.jp/arcgis/rest/services/Msil/Society/MapServer/7/query?token=1UJm66l--0PxAyqtBNk44hrvqaP20wIvUt77ElWSLxIvcHf1i0YCWSKoeEGWsB2ft1c8u7rWGGToBcwzFyfesG-EKb7npdM2vmx4kNvASlsvCRsXHXtU7-Y62PAWgrh6xSGVT83gTQ-3RhaX-vu9PJjps-zFvqMnccIn_Vh_1Ng.&f=json&returnGeometry=true&spatialRel=esriSpatialRelIntersects&geometry=%7B%22xmin%22%3A15155980.768862816%2C%22ymin%22%3A3711338.080405904%2C%22xmax%22%3A15938695.938502813%2C%22ymax%22%3A4494053.250045901%2C%22spatialReference%22%3A%7B%22wkid%22%3A102100%7D%7D&geometryType=esriGeometryEnvelope&inSR=102100&outFields=%E6%89%80%E5%9C%A8%E5%9C%B0%2C%E5%85%8D%E8%A8%B1%E7%95%AA%E5%8F%B7%2C%E6%BC%81%E6%A5%AD%E6%A8%A9%E3%81%AE%E7%A8%AE%E9%A1%9E%2C%E5%96%B6%E3%82%80%E6%BC%81%E6%A5%AD%E7%A8%AE%E9%A1%9E%2C%E6%93%8D%E6%A5%AD_%E9%A4%8A%E6%AE%96_%E6%99%82%E6%9C%9F%2C%E5%85%8D%E8%A8%B1%E6%9C%89%E5%8A%B9%E6%9C%9F%E9%96%93%2C%E9%9D%A2%E7%A9%8D%2C%E5%A4%96%E5%91%A8%2C%E5%82%99%E8%80%83%2C%E5%87%BA%E5%85%B8%E3%83%BB%E6%83%85%E5%A0%B1%E6%8F%90%E4%BE%9B%E8%80%85%2C%E3%83%87%E3%83%BC%E3%82%BF%E5%B9%B4%E5%BA%A6&orderByFields=objectid&outSR=102100
token: <token>
f: json
returnGeometry: true
spatialRel: esriSpatialRelIntersects
geometry: {"xmin":15155980.768862816,"ymin":3672202.321923904,"xmax":15938695.938502813,"ymax":4454917.491563901,"spatialReference":{"wkid":102100}}
geometryType: esriGeometryEnvelope
inSR: 102100
outFields: 航路標識番号,名称,読み,出典,データ年度,調査年度
orderByFields: OBJECTID
outSR: 102100
'''



