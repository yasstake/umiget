
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

        return r

    def get_inventory(self, path):
        url = self.base_url + path + '?f=json&token=' + self.token
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

    def query_data(self, path, loop = True, all_data=True, query_extent=None):
        r = self.get_inventory(path)
        extent, fields = self.parse_inventory(r.text)

        if query_extent:
            extent = query_extent

        params = {}
        params['geometry'] = ",".join(map(str, extent))
        if all_data:
            params['outFields']= ",".join(map(str, fields))
        print(extent)
        print(fields)

        result  = None

        if loop:
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
        else:

            r = self.get(path + '/query', params, True)
            print(r)
            result = r.json()

        return result

    def logout(self):
        self.session.close()

    def get_obstacle(self, loop = True):
        '''
        海底障害物
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/9', loop, False)
        print(r)

        return r


    def get_light_house(self, loop = True):
        '''
        灯台
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/15', loop)
        print(r)

        return r

    def get_float_lights(self, loop = True):
        '''
        灯浮標
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/16', loop)
        print(r)

        return r

    def get_pillar_lights(self, loop = True):
        '''
        灯標
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/17', loop)
        print(r)

        return r


    def get_other_lights(self, loop = True):
        '''
        灯(その他)
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/18', loop)
        print(r)

        return r


    def get_traffic_route_major(self, loop = True):
        '''
        海交法航路
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/20', loop)
        print(r)

        return r


    def get_traffic_route_minor(self, loop = True):
        '''
        港測法航路
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/21', loop)
        print(r)

        return r


    def get_fisher(self, loop = True):
        '''
        漁港
        :param loop:
        :return:
        '''
        r = self.query_data('Maritime/MapServer/32', loop)
        print(r)

        return r

    def get_fisher_fix_net(self, loop = True):
        '''
        低地漁業権
        :param loop:
        :return:
        '''
        r = self.query_data('Society/MapServer/7', loop)
        print(r)

        return r

    def get_marina(self, loop = True):
        '''
        マリーナ
        :param loop:
        :return:
        '''
        r = self.query_data('Society/MapServer/5', loop)
        print(r)

        return r


    def get_swimming_beach(self, loop = True):
        '''
        海水浴場
        :param loop:
        :return:
        '''
        r = self.query_data('Society/MapServer/3', loop)
        print(r)

        return r

    def get_tide_probe(self, loop = True):
        '''
        潮汐観測所
        :param loop:
        :return:
        '''
        r = self.query_data('Ocean/MapServer/184', loop)
        print(r)

        return r

    def get_safety_notice(self, loop=True):
        '''
        海上安全通報
        :param loop:
        :return:
        '''
        r = self.query_data('Safety/MapServer/0', loop)
        print(r)

        return r


