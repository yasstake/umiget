import hashlib
import json
import os
import time
from urllib.parse import urlencode

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


class CachedResponse:
    """ディスクキャッシュから復元したレスポンス。requestsのResponseと同じ最小限のインタフェースを持つ。"""

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


class Umi:
    API_BASE = 'https://api.msil.go.jp/'
    PAGE_SIZE = 1000
    REQUEST_WAIT = 1.0  # 過度なアクセスを避けるため、APIへのリクエストは1秒間隔に制限する
    CACHE_DIR = './cache'  # APIレスポンスのキャッシュ先。同じURL・パラメータへのリクエストはここから読む

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

    def __init__(self, api_key=None, cache_dir=None):
        self.session = requests.Session()
        self.api_key = api_key or os.environ.get('MSIL_API_KEY', Umi.TRIAL_KEY)
        self.headers = {'Ocp-Apim-Subscription-Key': self.api_key}
        self.cache_dir = cache_dir or Umi.CACHE_DIR

    def _cache_path(self, url, params):
        key = url + '?' + urlencode(sorted(params.items()))
        digest = hashlib.sha256(key.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, digest + '.json')

    def get(self, name, params, force_refresh=False):
        path, version, layer = Umi.LAYERS[name]
        url = '{base}{path}/{version}/MapServer/{layer}/query'.format(
            base=Umi.API_BASE, path=path, version=version, layer=layer)

        cache_path = self._cache_path(url, params)
        if not force_refresh and os.path.exists(cache_path):
            print('cache->', url, params)
            with open(cache_path, 'r', encoding='utf-8') as f:
                return CachedResponse(json.load(f))

        time.sleep(Umi.REQUEST_WAIT)
        print('get->', url, params)
        r = self.session.get(url, headers=self.headers, params=params)
        r.raise_for_status()

        os.makedirs(self.cache_dir, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(r.json(), f, ensure_ascii=False)

        return r

    def query_data(self, name, where='1=1', force_refresh=False):
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
            r = self.get(name, params, force_refresh=force_refresh)
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

    def get_obstacle(self, force_refresh=False):
        '''
        海底障害物(point)
        '''
        return self.query_data('obstacle', force_refresh=force_refresh)

    def get_obstacle_area(self, force_refresh=False):
        '''
        海底障害物(polygon)
        '''
        return self.query_data('obstacle_area', force_refresh=force_refresh)

    def get_light_house(self, force_refresh=False):
        '''
        灯台
        '''
        return self.query_data('light_house', force_refresh=force_refresh)

    def get_float_lights(self, force_refresh=False):
        '''
        灯浮標
        '''
        return self.query_data('float_lights', force_refresh=force_refresh)

    def get_pillar_lights(self, force_refresh=False):
        '''
        灯標
        '''
        return self.query_data('pillar_lights', force_refresh=force_refresh)

    def get_other_lights(self, force_refresh=False):
        '''
        灯(その他)
        '''
        return self.query_data('other_lights', force_refresh=force_refresh)

    def get_traffic_route_major(self, force_refresh=False):
        '''
        海交法航路
        '''
        return self.query_data('traffic_route_major', force_refresh=force_refresh)

    def get_traffic_route_minor(self, force_refresh=False):
        '''
        港則法航路
        '''
        return self.query_data('traffic_route_minor', force_refresh=force_refresh)

    def get_fisher(self, force_refresh=False):
        '''
        漁港
        '''
        return self.query_data('fisher', force_refresh=force_refresh)

    def get_fisher_fix_net(self, force_refresh=False):
        '''
        定置漁業権
        '''
        return self.query_data('fisher_fix_net', force_refresh=force_refresh)

    def get_fisher_common_net(self, force_refresh=False):
        '''
        共同漁業権
        '''
        return self.query_data('fisher_common_net', force_refresh=force_refresh)

    def get_fisher_demarcated_net(self, force_refresh=False):
        '''
        区画漁業権
        '''
        return self.query_data('fisher_demarcated_net', force_refresh=force_refresh)

    def get_wrected_ship_point(self, force_refresh=False):
        '''
        沈船(point)
        '''
        return self.query_data('wrected_ship_point', force_refresh=force_refresh)

    def get_wrected_ship_area(self, force_refresh=False):
        '''
        沈船(polygon)
        '''
        return self.query_data('wrected_ship_area', force_refresh=force_refresh)

    def get_notices_to_mariners(self, force_refresh=False):
        '''
        水路通報
        '''
        return self.query_data('notices_to_mariners', force_refresh=force_refresh)

    def get_navigational_warnings(self, force_refresh=False):
        '''
        航行警報
        '''
        return self.query_data('navigational_warnings', force_refresh=force_refresh)

    def get_notices_to_mariners_en(self, force_refresh=False):
        '''
        英文水路通報
        '''
        return self.query_data('notices_to_mariners_en', force_refresh=force_refresh)

    def get_navigational_warnings_en(self, force_refresh=False):
        '''
        英文航行警報
        '''
        return self.query_data('navigational_warnings_en', force_refresh=force_refresh)

    # マリーナ・海水浴場・潮汐観測所は https://portal.msil.go.jp/msil-api-list の
    # 公開APIカタログに掲載されておらず、この公式APIからは取得できない。

    @staticmethod
    def save_info(data_name, force_refresh=False):
        umi = Umi()

        r = getattr(umi, 'get_' + data_name)(force_refresh=force_refresh)
        with open('data/' + data_name + '.json', mode='w', encoding='utf-8') as f:
            f.write(json.dumps(r, ensure_ascii=False))

        umi.logout()


if __name__ == '__main__':
    import sys

    # APIのデータは頻繁に更新されないため、既定ではキャッシュ(./cache)があれば
    # それを使い、実際のAPIへは初回のみアクセスする。--refresh を指定したときだけ
    # キャッシュを無視して明示的に再取得する。
    force_refresh = '--refresh' in sys.argv

    Umi.save_info('fisher_fix_net', force_refresh=force_refresh)
    Umi.save_info('fisher_common_net', force_refresh=force_refresh)
    Umi.save_info('fisher_demarcated_net', force_refresh=force_refresh)
    Umi.save_info('fisher', force_refresh=force_refresh)
    Umi.save_info('traffic_route_minor', force_refresh=force_refresh)
    Umi.save_info('traffic_route_major', force_refresh=force_refresh)
    Umi.save_info('other_lights', force_refresh=force_refresh)
    Umi.save_info('pillar_lights', force_refresh=force_refresh)
    Umi.save_info('float_lights', force_refresh=force_refresh)
    Umi.save_info('light_house', force_refresh=force_refresh)

#    Umi.save_info('obstacle', force_refresh=force_refresh)
#    Umi.save_info('obstacle_area', force_refresh=force_refresh)
#    Umi.save_info('wrected_ship_point', force_refresh=force_refresh)
#    Umi.save_info('wrected_ship_area', force_refresh=force_refresh)
#    Umi.save_info('notices_to_mariners', force_refresh=force_refresh)
#    Umi.save_info('navigational_warnings', force_refresh=force_refresh)
