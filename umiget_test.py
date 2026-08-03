import os
import unittest
from unittest.mock import patch, MagicMock

from umiget import Umi


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception('HTTP {}'.format(self.status_code))


class UmiUnitTestCase(unittest.TestCase):
    """ネットワークに一切アクセスしない、純粋なロジックのテスト。"""

    @patch('umiget.time.sleep')
    def test_get_builds_expected_url_and_headers(self, mock_sleep):
        umi = Umi(api_key='test-key')
        umi.session = MagicMock()
        umi.session.get.return_value = FakeResponse({'features': []})

        umi.get('light_house', {'f': 'geojson', 'where': '1=1', 'resultOffset': 0})

        args, kwargs = umi.session.get.call_args
        self.assertEqual(args[0], 'https://api.msil.go.jp/lights/lighthouse/v2/MapServer/1/query')
        self.assertEqual(kwargs['headers'], {'Ocp-Apim-Subscription-Key': 'test-key'})
        self.assertEqual(kwargs['params']['where'], '1=1')
        mock_sleep.assert_called_once_with(Umi.REQUEST_WAIT)

    @patch('umiget.time.sleep')
    def test_query_data_single_page(self, mock_sleep):
        umi = Umi()
        expected_features = [{'type': 'Feature', 'properties': {}, 'geometry': None}]

        with patch.object(umi, 'get', return_value=FakeResponse({'features': expected_features})):
            result = umi.query_data('light_house')

        self.assertEqual(result['type'], 'FeatureCollection')
        self.assertEqual(result['features'], expected_features)

    @patch('umiget.time.sleep')
    def test_query_data_paginates_with_result_offset(self, mock_sleep):
        umi = Umi()
        page1 = [{'id': i} for i in range(3)]
        page2 = [{'id': i} for i in range(3, 5)]
        calls = []

        def fake_get(name, params):
            calls.append(dict(params))
            if params['resultOffset'] == 0:
                return FakeResponse({'features': page1, 'exceededTransferLimit': True})
            return FakeResponse({'features': page2})

        with patch.object(umi, 'get', side_effect=fake_get):
            result = umi.query_data('light_house')

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]['resultOffset'], 0)
        self.assertEqual(calls[1]['resultOffset'], len(page1))
        self.assertEqual(result['features'], page1 + page2)

    @patch('umiget.time.sleep')
    def test_query_data_stops_when_a_page_is_empty(self, mock_sleep):
        """
        exceededTransferLimit が true のままでも、ページが空になったら
        resultOffset が進まず無限ループになるのを防ぐ回帰テスト。
        """
        umi = Umi()
        call_count = {'n': 0}

        def fake_get(name, params):
            call_count['n'] += 1
            return FakeResponse({'features': [], 'exceededTransferLimit': True})

        with patch.object(umi, 'get', side_effect=fake_get):
            result = umi.query_data('light_house')

        self.assertEqual(call_count['n'], 1)
        self.assertEqual(result['features'], [])

    @patch('umiget.time.sleep')
    def test_query_data_raises_on_http_error(self, mock_sleep):
        umi = Umi()

        with patch.object(umi, 'get', return_value=FakeResponse({}, status_code=500)):
            with self.assertRaises(Exception):
                umi.query_data('light_house')


@unittest.skipUnless(
    os.environ.get('UMIGET_RUN_INTEGRATION') == '1',
    'set UMIGET_RUN_INTEGRATION=1 to run tests that hit the live api.msil.go.jp API'
)
class UmiIntegrationTestCase(unittest.TestCase):
    """https://api.msil.go.jp の実サーバーへアクセスする結合テスト。既定ではスキップされる。"""

    def setUp(self):
        self.umi = Umi()

    def tearDown(self):
        self.umi.logout()

    def _assert_feature_collection(self, r):
        self.assertIsInstance(r, dict)
        self.assertIn('features', r)
        self.assertIsInstance(r['features'], list)

    def test_get_light_house(self):
        self._assert_feature_collection(self.umi.get_light_house())

    def test_get_float_lights(self):
        self._assert_feature_collection(self.umi.get_float_lights())

    def test_get_pillar_lights(self):
        self._assert_feature_collection(self.umi.get_pillar_lights())

    def test_get_other_lights(self):
        self._assert_feature_collection(self.umi.get_other_lights())

    def test_get_traffic_route_major(self):
        self._assert_feature_collection(self.umi.get_traffic_route_major())

    def test_get_traffic_route_minor(self):
        self._assert_feature_collection(self.umi.get_traffic_route_minor())

    def test_get_fisher(self):
        self._assert_feature_collection(self.umi.get_fisher())

    def test_get_fisher_fix_net(self):
        self._assert_feature_collection(self.umi.get_fisher_fix_net())

    def test_get_fisher_common_net(self):
        self._assert_feature_collection(self.umi.get_fisher_common_net())

    def test_get_fisher_demarcated_net(self):
        self._assert_feature_collection(self.umi.get_fisher_demarcated_net())

    def test_get_obstacle(self):
        self._assert_feature_collection(self.umi.get_obstacle())

    def test_get_obstacle_area(self):
        self._assert_feature_collection(self.umi.get_obstacle_area())

    def test_get_wrected_ship_point(self):
        self._assert_feature_collection(self.umi.get_wrected_ship_point())

    def test_get_wrected_ship_area(self):
        self._assert_feature_collection(self.umi.get_wrected_ship_area())

    def test_get_notices_to_mariners(self):
        self._assert_feature_collection(self.umi.get_notices_to_mariners())

    def test_get_navigational_warnings(self):
        self._assert_feature_collection(self.umi.get_navigational_warnings())


if __name__ == '__main__':
    unittest.main()
