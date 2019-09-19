
from requests_html import HTMLSession
import urllib
import json
from time import sleep
'''
See request_html docummentation at;
https://html.python-requests.org/
'''

#https://github.com/chris48s/arcgis2geojson
#pip install arcgis2geojson
from arcgis2geojson import arcgis2geojson

class Umi:
    LAYER_LIST = 'https://www.msil.go.jp/msilgisapi/api/layer/layer'
    REQUEST_WAIT = 0.5

    def __init__(self):
        self.session = HTMLSession()
        self.headers = {'Content-Type': 'application/json', 'Origin': 'https://www.msil.go.jp',
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) Chrome/74.0.3729.131 Safari/537.36',
                        'X-Requested-With':'XMLHttpRequest'}
        self.token = None
        self.base_url = 'https://www.msil.go.jp/arcgis/rest/services/Msil/'

    def login(self):
        SESSION = 'https://www.msil.go.jp/msilgisapi/api/common/session'
        r = self.session.post(SESSION, headers=self.headers)

        TOKEN = 'https://www.msil.go.jp/msilwebtoken/api/token/new';
        r = self.session.post(TOKEN, headers=self.headers)

        self.token = r.json()['token']

    def make_params(self, params, query=False):
        if self.token:
            params['token'] = self.token

        params['f'] = 'json'
        params['inSR'] = '4326'
        params['outSR'] = '4326'

        if query:
            params['returnGeometry'] = 'true'
            params['spatialRel'] = 'esriSpatialRelIntersects'
            params['geometryType'] = 'esriGeometryEnvelope'

        encode = urllib.parse.urlencode(params)

        return encode

    def get(self, path, params, query=True):
        url = self.base_url + path + '?' + self.make_params(params, query)
        r = self.session.get(url, headers=self.headers)

        return r

    def get_inventory(self, path):
        url = self.base_url + path + '?f=json&inSR=4326&outSR=4326&token=' + self.token
        r = self.session.get(url, headers=self.headers)

        return r

    def parse_inventory(self, inventory):
        j = json.loads(inventory)

        extent = j['extent']
        extents = (extent['xmin'], extent['ymin'], extent['xmax'], extent['ymax'])

        fields = j['fields']

        field = []
        for f in fields:
            if f['name'] != 'OBJECTID' and f['name'] != 'Shape':
                field.append(f['name'])

        return extents, field

    AREA_SIZE = 10

    def query_data(self, path, all_data=True):
        r = self.get_inventory(path)
        extent, fields = self.parse_inventory(r.text)

        print(extent, fields)

        params = {}

        if all_data:
            params['outFields'] = ",".join(map(str, fields))

        result = self.query_data_with_extent(path + '/query', params,
                      int(extent[0]-1), int(extent[1]-1), int(extent[2]+1), int(extent[3]+1))

        return result

    def query_data_with_extent(self, path, params, x0, y0, x1, y1):
        params['geometry'] = ",".join(map(str, (x0, y0, x1, y1)))
        print(path, params)
        r = self.get(path, params, True)
        print(r)
        result = r.json()

        if 'exceededTransferLimit' not in result:
            return result

        # retry with divide 4 area
        dx = int((x1 - x0)/2)
        dy = int((y1 - y0)/2)

        x00 = x0
        y00 = y0
        x01 = x0 + dx
        y01 = y0 + dy
        x02 = x1
        y02 = y1

        sleep(Umi.REQUEST_WAIT)
        result = self.query_data_with_extent(path, params, x00, y00, x01, y01)

        sleep(Umi.REQUEST_WAIT)
        r = self.query_data_with_extent(path, params, x00, y01, x01, y02)
        features = r['features']
        if len(features) != 0:
            result['features'].extend(features)

        sleep(Umi.REQUEST_WAIT)
        r = self.query_data_with_extent(path, params, x01, y00, x02, y01)
        features = r['features']
        if len(features) != 0:
            result['features'].extend(features)

        sleep(Umi.REQUEST_WAIT)
        r = self.query_data_with_extent(path, params, x01, y01, x02, y02)
        features = r['features']
        if len(features) != 0:
            result['features'].extend(features)

        return result

    def logout(self):
        self.session.close()

    def get_obstacle(self):
        '''
        海底障害物
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/9')

        return r

    def get_light_house(self):
        '''
        灯台
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/15')

        return r

    def get_float_lights(self):
        '''
        灯浮標
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/16')

        return r

    def get_pillar_lights(self):
        '''
        灯標
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/17')

        return r

    def get_other_lights(self):
        '''
        灯(その他)
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/18')

        return r

    def get_traffic_route_major(self):
        '''
        海交法航路
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/20')

        return r

    def get_traffic_route_minor(self):
        '''
        港測法航路
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/21')

        return r

    def get_fisher(self):
        '''
        漁港
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/32')

        return r

    def get_fisher_fix_net(self):
        '''
        低地漁業権
        :param loop:
        :return:
        '''
        r = self.query_data('Society/MapServer/7')

        return r

    def get_marina(self):
        '''
        マリーナ
        :param loop:
        :return:
        '''
        r = self.query_data('Society/MapServer/5')

        return r

    def get_swimming_beach(self):
        '''
        海水浴場
        :param loop:
        :return:
        '''
        r = self.query_data('Society/MapServer/3')

        return r

    def get_tide_probe(self):
        '''
        潮汐観測所
        :param loop:
        :return:
        '''
        r = self.query_data('Ocean/MapServer/184')

        return r

    def get_safety_notice(self):
        '''
        海上安全通報
        :param loop:
        :return:
        '''
        r = self.query_data('SafetyInfo1/MapServer/4')

        return r


    '''
    SafetyInfo1/MapServer/4  水路通報
    
    '''

    @staticmethod
    def save_info(data_name):
        umi = Umi()
        umi.login()

        r = eval('umi.get_' + data_name + '()')
        r = arcgis2geojson(r)
        with open('data/' + data_name + '.json', mode='w', encoding='utf-8') as f:
            f.write(json.dumps(r, ensure_ascii=False))

        umi.logout()


if __name__ == '__main__':
    Umi.save_info('safety_notice')

#    Umi.save_info('swimming_beach')
#    Umi.save_info('marina')
#    Umi.save_info('fisher_fix_net')
#    Umi.save_info('fisher')
#    Umi.save_info('traffic_route_minor')
#    Umi.save_info('traffic_route_major')
#    Umi.save_info('other_lights')
#    Umi.save_info('pillar_lights')
#    Umi.save_info('float_lights')
#    Umi.save_info('light_house')



'''
    Umi.save_info('obstacle')
    Umi.save_info('tide_probe')
'''












