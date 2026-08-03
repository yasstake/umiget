import json
import os
import time

import requests

'''
海洋状況表示システム(海しる/MSIL) 公開API

https://portal.msil.go.jp/howtouse で案内されている、海上保安庁が公式に提供する
サブスクリプションキー認証のREST API。旧来の www.msil.go.jp 内部エンドポイント
(msilgisapi/msilwebtoken, arcgis/rest/services/Msil/...) はすべて廃止されているため、
このAPIに全面的に移行した。

URL構造の例(灯台):
    https://api.msil.go.jp/lights/lighthouse/v2/MapServer/1/query?f=geojson&where=1=1

認証はHTTPヘッダー `Ocp-Apim-Subscription-Key` にサブスクリプションキーを指定する。
各データセットのパス・バージョン・レイヤー番号(LayerSelection)は、開発者ポータルの
公開メタデータAPI (https://portal.msil.go.jp/mapi/apis, .../operations) から確認した。

1回の応答は最大1000レコードで、超過時は "exceededTransferLimit": true が付与される。
その場合は resultOffset を進めて追加リクエストする(ページネーション)。
出力はGeoJSON(f=geojson)なので、常にWGS84経緯度で返り、座標系変換やArcGIS JSON
からの変換(arcgis2geojson)は不要になった。

マリーナ・海水浴場・潮汐観測所は、このAPIカタログ (https://portal.msil.go.jp/msil-api-list)
には現時点で掲載されておらず、公式APIからは取得できない。
'''


class Umi:
    API_BASE = 'https://api.msil.go.jp/'
    PAGE_SIZE = 1000
    REQUEST_WAIT = 1.0  # 過度なアクセスを避けるため、APIへのリクエストは1秒間隔に制限する

    # https://portal.msil.go.jp/howtouse に掲載されている試用サブスクリプションキー。
    # 利用者への通知なく停止・変更されることがあるため、本格利用時は
    # https://portal.msil.go.jp から正式キーを申請し、環境変数 MSIL_API_KEY に設定すること。
    TRIAL_KEY = '0e83ad5d93214e04abf37c970c32b641'

    # 名前 -> (パス, APIバージョン, レイヤー番号)
    # レイヤー番号は https://portal.msil.go.jp/mapi/apis/<api-id>/operations で
    # 確認した LayerSelection の有効値(点データ=1, 面データ=3 が多い)。
    LAYERS = {
        'light_house': ('lights/lighthouse', 'v2', 1),
        'float_lights': ('lights/buoy', 'v2', 1),
        'pillar_lights': ('lights/beacon', 'v2', 1),
        'other_lights': ('lights/other', 'v2', 1),
        'fisher': ('fishing-port-point', 'v2', 1),
        'fisher_fix_net': ('fixed-gear-fishery-right2024', 'v2', 3),
        'fisher_common_net': ('common-fishery-right2024', 'v2', 3),
        'fisher_demarcated_net': ('demarcated-fishery-right2024', 'v2', 3),
        'traffic_route_major': ('maritime-traffic-safety-act/traffic-route', 'v2', 3),
        'traffic_route_minor': ('act-on-port-regulations/traffic-route', 'v2', 3),
        'obstacle': ('seabed-obstruction', 'v2', 1),
        'obstacle_area': ('seabed-obstruction', 'v2', 3),
        'wrected_ship_point': ('wrecks', 'v2', 1),
        'wrected_ship_area': ('wrecks', 'v2', 3),
        # 水路通報・航行警報はレイヤー1〜3が存在するが、各番号が具体的に
        # 何を指すかは未確認のため、デフォルト(1)のみを対象にしている。
        'notices_to_mariners': ('notices-to-mariners', 'v2', 1),
        'navigational_warnings': ('navigational-warnings', 'v2', 1),
        'notices_to_mariners_en': ('notices-to-mariners-en', 'v2', 1),
        'navigational_warnings_en': ('navigational-warnings-en', 'v2', 1),
    }

    def __init__(self, api_key=None):
        self.session = requests.Session()
        self.api_key = api_key or os.environ.get('MSIL_API_KEY', Umi.TRIAL_KEY)
        self.headers = {'Ocp-Apim-Subscription-Key': self.api_key}

    def get(self, name, params):
        path, version, layer = Umi.LAYERS[name]
        url = '{base}{path}/{version}/MapServer/{layer}/query'.format(
            base=Umi.API_BASE, path=path, version=version, layer=layer)

        time.sleep(Umi.REQUEST_WAIT)
        print('get->', url, params)
        r = self.session.get(url, headers=self.headers, params=params)

        return r

    def query_data(self, name, where='1=1'):
        features = []
        crs = None
        offset = 0

        while True:
            params = {
                'f': 'geojson',
                'where': where,
                'returnGeometry': 'true',
                'resultOffset': offset,
            }
            r = self.get(name, params)
            r.raise_for_status()
            result = r.json()

            page = result.get('features', [])
            features.extend(page)
            crs = result.get('crs', crs)

            if not result.get('exceededTransferLimit') or not page:
                break

            offset += len(page)

        return {'type': 'FeatureCollection', 'features': features, 'crs': crs}

    def logout(self):
        self.session.close()

    def get_obstacle(self):
        '''
        海底障害物(point)
        '''
        return self.query_data('obstacle')

    def get_obstacle_area(self):
        '''
        海底障害物(polygon)
        '''
        return self.query_data('obstacle_area')

    def get_light_house(self):
        '''
        灯台
        '''
        return self.query_data('light_house')

    def get_float_lights(self):
        '''
        灯浮標
        '''
        return self.query_data('float_lights')

    def get_pillar_lights(self):
        '''
        灯標
        '''
        return self.query_data('pillar_lights')

    def get_other_lights(self):
        '''
        灯(その他)
        '''
        return self.query_data('other_lights')

    def get_traffic_route_major(self):
        '''
        海交法航路
        '''
        return self.query_data('traffic_route_major')

    def get_traffic_route_minor(self):
        '''
        港則法航路
        '''
        return self.query_data('traffic_route_minor')

    def get_fisher(self):
        '''
        漁港
        '''
        return self.query_data('fisher')

    def get_fisher_fix_net(self):
        '''
        定置漁業権
        '''
        return self.query_data('fisher_fix_net')

    def get_fisher_common_net(self):
        '''
        共同漁業権
        '''
        return self.query_data('fisher_common_net')

    def get_fisher_demarcated_net(self):
        '''
        区画漁業権
        '''
        return self.query_data('fisher_demarcated_net')

    def get_wrected_ship_point(self):
        '''
        沈船(point)
        '''
        return self.query_data('wrected_ship_point')

    def get_wrected_ship_area(self):
        '''
        沈船(polygon)
        '''
        return self.query_data('wrected_ship_area')

    def get_notices_to_mariners(self):
        '''
        水路通報
        '''
        return self.query_data('notices_to_mariners')

    def get_navigational_warnings(self):
        '''
        航行警報
        '''
        return self.query_data('navigational_warnings')

    def get_notices_to_mariners_en(self):
        '''
        英文水路通報
        '''
        return self.query_data('notices_to_mariners_en')

    def get_navigational_warnings_en(self):
        '''
        英文航行警報
        '''
        return self.query_data('navigational_warnings_en')

    # マリーナ・海水浴場・潮汐観測所は https://portal.msil.go.jp/msil-api-list の
    # 公開APIカタログに掲載されておらず、この公式APIからは取得できない。

    @staticmethod
    def save_info(data_name):
        umi = Umi()

        r = eval('umi.get_' + data_name + '()')
        with open('data/' + data_name + '.json', mode='w', encoding='utf-8') as f:
            f.write(json.dumps(r, ensure_ascii=False))

        umi.logout()


if __name__ == '__main__':
    Umi.save_info('fisher_fix_net')
    Umi.save_info('fisher_common_net')
    Umi.save_info('fisher_demarcated_net')
    Umi.save_info('fisher')
    Umi.save_info('traffic_route_minor')
    Umi.save_info('traffic_route_major')
    Umi.save_info('other_lights')
    Umi.save_info('pillar_lights')
    Umi.save_info('float_lights')
    Umi.save_info('light_house')

#    Umi.save_info('obstacle')
#    Umi.save_info('obstacle_area')
#    Umi.save_info('wrected_ship_point')
#    Umi.save_info('wrected_ship_area')
#    Umi.save_info('notices_to_mariners')
#    Umi.save_info('navigational_warnings')
