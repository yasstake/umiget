import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

import convert

FISHER = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [125.46577379000007, 24.72446440100009]}, "properties": {"漁港名": "保良", "読み": "ほら", "管理者": "宮古島市", "区域変更": 'null', "漁港種類": "第1種", "作成機関": "海上保安庁", "データ年度": "H24(2012)", "港則法適用": "×", "調査年度": "H24(2012)", "更新年月日": -2209161600000, "備考": 'null', "管区": "第十一管区海上保安本部", "IDK": 11, "利用者_漁協": "宮古島漁協", "出典・情報提供者": "沖縄県", "所在地": "沖縄県宮古島市城辺字保良(宮古島）"}}
MARINA = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [131.95169440000006, 33.94905830000005]}, "properties": {"所在地": "山口県光市光井2-19-2", "マリーナの名称": "山口県スポーツ交流村", "よみ": "やまぐちけんすぽーつこうりゅうむら", "連絡先": "0833-71-1144", "最大保管可能隻数_陸上_水上_": "220", "最大係留可能隻数": "20", "マリーナのURL": "<a href=\"http://kouryumura.net/\" target=\"_blank\">http://kouryumura.net/</a>", "データ年度": "H28(2016)", "調査年度": "H28(2016)", "作成機関": "海上保安庁", "出典・情報提供者": "公益財団法人山口県人づくり財団", "備考": "最大保管隻数・陸上:ディンギーヨットのみ　最大保管隻数・海上:ディンギーヨット救助艇のみ", "flag": 'null', "更新日": 'null', "URL": "http://kouryumura.net/", "作業用メモ": 'null', "マリーナ事業者HPリンク": "<a href=\"http://kouryumura.net/\" target=\"_blank\">http://kouryumura.net/</a>", "施設名": "係留施設", "係留施設": "○", "クレーン": "×", "ウィンチ": "×", "フォークリフト": "×", "スロープ": "○", "結合用ID": 'null', "事業者_管理者_名": "公益財団法人山口県人づくり財団", "管区": "第六管区海上保安本部", "IDK": 6}}
FLOAT_LIGHTS = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [130.61603333300002, 31.125222222000048]}, "properties": {"航路標識番号": 6611, "灯フラグ": 2, "名称": "鹿児島湾口神瀬灯浮標", "読み": "Kagoshima Wan", "データ年度": "H29(2017)", "調査年度": "H29(2017)", "作成機関": "海上保安庁", "出典": "海上保安庁", "F9": "N", "緯度": 31.125222222222224, "F11": "E", "経度": 130.61603333333332, "標識種別": "灯浮標"}}
LIGHT_HOUSE = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [128.34991666700012, 31.99216666700005]}, "properties": {"航路標識番号": 6181, "灯フラグ": 1, "名称": "女島灯台", "読み": "Meshima", "データ年度": "H29(2017)", "調査年度": "H29(2017)", "作成機関": "海上保安庁", "出典": "海上保安庁", "F9": "N", "緯度": 31.992166666666666, "F11": "E", "経度": 128.34991666666667, "標識種別": "灯台"}}
OTHER_LIGHTS = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [130.22744444400007, 31.72011111100005]}, "properties": {"航路標識番号": 6573.3, "灯フラグ": 0, "名称": "串木野港国家石油備蓄基地ｼｰﾊﾞｰｽ灯", "読み": "Kushikino Ko", "データ年度": "H29(2017)", "調査年度": "H29(2017)", "作成機関": "海上保安庁", "出典": "海上保安庁", "F9": "N", "緯度": 31.72011111111111, "F11": "E", "経度": 130.22744444444444, "標識種別": "その他の灯"}}
PILLAR_LIGHTS = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [140.44227777800006, 41.58311111100005]}, "properties": {"航路標識番号": 7, "灯フラグ": 3, "名称": "北電知内発電第1号灯標", "読み": "Hokuden", "データ年度": "H29(2017)", "調査年度": "H29(2017)", "作成機関": "海上保安庁", "出典": "海上保安庁", "F9": "N", "緯度": 41.583111111111116, "F11": "E", "経度": 140.44227777777778, "標識種別": "灯標"}}
MAJOR_ROUTE = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[139.73787203104177, 35.3123153345353], [139.7487811004362, 35.34552639955393], [139.7767761003829, 35.40618689980346], [139.76969439985498, 35.40847220028701], [139.74153140025805, 35.34794250013141], [139.72303624917288, 35.32969142144776], [139.72303419961804, 35.32968939977184], [139.73092029963425, 35.32045719993806], [139.73787110024352, 35.312312499872235], [139.73787203104177, 35.3123153345353]]]}, "properties": {"ID": 2, "設定海域": "東京湾", "航路名": "中ノ瀬航路", "読み": "なかのせこうろ", "都道府県": "神奈川県_千葉県", "データ年": "H23(2011)", "調査年度": "H26（2014）", "作成機関": "海上保安庁海洋情報部", "出典・情報提供者": "海上交通安全法", "管区": "第三管区海上保安本部", "Shape_Length": 0.2248069811340437, "Shape_Area": 0.0009298792241130215}}
MINOR_ROUTE = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[138.5008726000001, 35.01722520000004], [138.50613940000005, 35.02061020000008], [138.5317116, 35.02546440000009], [138.53188290000003, 35.02815190000007], [138.50463720000005, 35.02298040000005], [138.4987658, 35.01920700000005], [138.4979327000001, 34.99956890000004], [138.5001235000001, 34.999569000000065], [138.5008726000001, 35.01722520000004]]]}, "properties": {"管区": "第三管区海上保安本部", "都道府県": "静岡", "港名": "清水", "航路名": "清水", "読み": "しみず", "データ年度": "H24(2012)", "調査年度": "H26（2014）", "作成機関": "海上保安庁海洋情報部", "出典・情報提供者": "港則法", "Shape_Length": 0.10921277512329106, "Shape_Area": 0.00012954995959511253}}
FISHER_NET = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[128.3142170970001, 26.733744990000048], [128.31411000000003, 26.733698332000074], [128.3133436060001, 26.733382224000025], [128.31321549900008, 26.73333333200003], [128.3130004720001, 26.73325126900005], [128.30954211000005, 26.73128583700003], [128.30957749700008, 26.731254161000038], [128.30955861200005, 26.73118916100003], [128.30946250300008, 26.731078053000033], [128.30937972800007, 26.731070558000056], [128.30934194600002, 26.731022774000053], [128.30924778200006, 26.730966386000034], [128.30919444900007, 26.730969161000075], [128.30914416300004, 26.731005828000036], [128.309084449, 26.73098333200005], [128.30903073900004, 26.730995215000064], [128.30566666700008, 26.729083332000073], [128.3172833330001, 26.71808333200005], [128.32460000000003, 26.72429999900004], [128.3142170970001, 26.733744990000048]], [[128.30774917000008, 26.730069720000074], [128.30775306100008, 26.730105278000053], [128.30777888500006, 26.73013194500004], [128.30779444900008, 26.730146107000053], [128.30781639400004, 26.730138891000024], [128.30784221800002, 26.730115828000066], [128.30782221800007, 26.73008027800006], [128.30779138800006, 26.730069999000023], [128.3077727760001, 26.730066107000027], [128.30774917000008, 26.730069720000074]]]}, "properties": {"objectid": 24569, "都道府県": "沖縄県", "免許番号": "定置第2号", "漁業権の種類": "定置漁業", "営む漁業種類": "雑魚定置漁業", "漁業開始": "1月1日", "漁業終了": "12月31日", "免許開始": 1535760000000, "免許終了": 1693440000000, "更新年月日": 1424995200000, "備考": "標識を設置しなければならない", "免許有効期間": "H30(2018)/09/01-H35(2023)/08/31", "データ年度": "H30(2018)", "調査年度": "H30(2018)", "作成機関": "海上保安庁", "出典・情報提供者": "沖縄県", "管区": "第十一管区海上保安本部", "idk": 11, "所在地": "沖縄県国頭郡国頭村字安田地先", "操業_養殖_時期": "1/1-12/31", "面積": "99.4(ha)", "外周": "3989.9(m)", "ラベル追加文字": "雑魚", "shape_Length": 0.049814064250907016, "shape_Area": 0.00014158426933257829}}


class MyTestCase(unittest.TestCase):
    def test_load(self):
        j = convert.load('../data/marina.json')

        for line in j['features']:
            print(line)

    def test_basic_property(self):
        r = convert.basic_property(MARINA)
        print(r)

    def test_marina_property(self):
        r = convert.marina_property(MARINA)
        print(r)

    def test_fisher_property(self):
        r = convert.fisher_property(FISHER)
        print(r)

    def test_fisher_net_property(self):
        r = convert.fisher_fixnet_property(FISHER_NET)
        print(r)


KML_NS = {'kml': convert.KML_NAMESPACE}


class KmlConversionTestCase(unittest.TestCase):
    """
    geojson_to_kml() が返すのは xmlns 属性を手動で設定しただけの、まだ
    シリアライズしていない ElementTree なので、この時点ではタグは
    名前空間なしの単純な文字列("Placemark"等)のまま。実際にファイルへ
    書き出して読み直したときに初めて xmlns が名前空間として解決される
    (test_save_kml_writes_valid_xml_file 参照)。
    """

    def test_point_geometry_and_name(self):
        geojson = {'features': [LIGHT_HOUSE]}
        kml = convert.geojson_to_kml(geojson)

        placemark = kml.find('.//Placemark')
        self.assertEqual(placemark.find('name').text, '女島灯台')

        coords = placemark.find('Point/coordinates').text
        self.assertEqual(coords, '128.34991666700012,31.99216666700005')

    def test_polygon_with_hole_geometry(self):
        geojson = {'features': [FISHER_NET]}
        kml = convert.geojson_to_kml(geojson)

        placemark = kml.find('.//Placemark')
        polygon = placemark.find('Polygon')

        self.assertIsNotNone(polygon.find('outerBoundaryIs'))
        self.assertIsNotNone(polygon.find('innerBoundaryIs'))

        # ラベル追加文字 が名前フィールド候補にヒットして名前になる
        self.assertEqual(placemark.find('name').text, '雑魚')

    def test_extended_data_contains_all_properties(self):
        geojson = {'features': [FISHER]}
        kml = convert.geojson_to_kml(geojson)

        placemark = kml.find('.//Placemark')
        data_names = {d.get('name') for d in placemark.findall('ExtendedData/Data')}

        self.assertEqual(data_names, set(FISHER['properties'].keys()))

    def test_name_field_priority_falls_back(self):
        properties = {'読み': 'よみがな'}
        name = convert._placemark_name(properties, convert.DEFAULT_NAME_FIELDS)

        self.assertEqual(name, 'よみがな')

    def test_name_field_missing_returns_empty(self):
        name = convert._placemark_name({'foo': 'bar'}, convert.DEFAULT_NAME_FIELDS)

        self.assertEqual(name, '')

    def test_light_name_with_breakwater_keyword_is_blank(self):
        properties = {'名称': '吉岡港第2西防波堤灯台'}
        name = convert._placemark_name(properties, convert.DEFAULT_NAME_FIELDS)

        self.assertEqual(name, '')

    def test_fisher_name_with_breakwater_keyword_is_not_blank(self):
        # 「防波堤」の抑制は名前フィールドが「名称」の場合のみ(灯台・灯標・灯・灯浮標)。
        # 他のデータセット(例: 漁港名)には適用しない。
        properties = {'漁港名': '防波堤漁港'}
        name = convert._placemark_name(properties, convert.DEFAULT_NAME_FIELDS)

        self.assertEqual(name, '防波堤漁港')

    def test_point_geometry_with_breakwater_keyword_has_no_placemark_name(self):
        light_house_with_breakwater = dict(LIGHT_HOUSE)
        light_house_with_breakwater['properties'] = dict(LIGHT_HOUSE['properties'])
        light_house_with_breakwater['properties']['名称'] = '吉岡港第2西防波堤灯台'

        geojson = {'features': [light_house_with_breakwater]}
        kml = convert.geojson_to_kml(geojson)

        placemark = kml.find('.//Placemark')
        self.assertIsNone(placemark.find('name'))

    def test_save_kml_writes_valid_xml_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            infile = os.path.join(tmp, 'in.json')
            outfile = os.path.join(tmp, 'out.kml')

            with open(infile, 'w', encoding='utf-8') as f:
                import json
                json.dump({'features': [LIGHT_HOUSE, MAJOR_ROUTE]}, f)

            convert.save_kml(infile, outfile)

            tree = ET.parse(outfile)
            placemarks = tree.findall('.//kml:Placemark', KML_NS)
            self.assertEqual(len(placemarks), 2)

    def test_style_adds_style_element_and_placemark_styleurl(self):
        geojson = {'features': [FISHER_NET]}
        style = convert.KML_STYLES['fisher_fix_net']

        kml = convert.geojson_to_kml(geojson, style=style)

        kml_style = kml.find('.//Style')
        self.assertEqual(kml_style.get('id'), style['id'])
        self.assertEqual(kml_style.find('PolyStyle/color').text, style['poly_color'])
        self.assertEqual(kml_style.find('PolyStyle/fill').text, '1')
        self.assertEqual(kml_style.find('LineStyle/color').text, style['line_color'])

        placemark = kml.find('.//Placemark')
        self.assertEqual(placemark.find('styleUrl').text, '#' + style['id'])

    def test_kml_styles_use_expected_red_opacity(self):
        # 定置漁業権: 赤、透過65%(不透明度35% -> alpha 255*0.35を丸めて59)
        self.assertEqual(convert.KML_STYLES['fisher_fix_net']['poly_color'], '590000ff')
        # 区画漁業権: 赤、透過75%(不透明度25% -> alpha 255*0.25を丸めて40)
        self.assertEqual(convert.KML_STYLES['fisher_demarcated_net']['poly_color'], '400000ff')

    def test_fisher_fix_net_has_thin_outline(self):
        style = convert.KML_STYLES['fisher_fix_net']
        kml = convert.geojson_to_kml({'features': [FISHER_NET]}, style=style)

        kml_style = kml.find('.//Style')
        self.assertEqual(kml_style.find('LineStyle/width').text, '1')
        self.assertEqual(kml_style.find('PolyStyle/outline').text, '1')

    def test_fisher_demarcated_net_has_no_outline(self):
        style = convert.KML_STYLES['fisher_demarcated_net']
        kml = convert.geojson_to_kml({'features': [FISHER_NET]}, style=style)

        kml_style = kml.find('.//Style')
        self.assertIsNone(kml_style.find('LineStyle'))
        self.assertEqual(kml_style.find('PolyStyle/outline').text, '0')

    def test_all_polygon_datasets_have_a_defined_style(self):
        # スタイル(PolyStyleのcolor)未定義のPolygon/MultiPolygonデータセットは、
        # Google EarthのデフォルトPolyStyle(不透明の白)で塗りつぶされてしまうため、
        # 面データを持つデータセットには必ずKML_STYLESにpoly_colorを定義しておく。
        polygon_datasets = ('fisher_fix_net', 'fisher_demarcated_net', 'fisher_common_net',
                             'traffic_route_major', 'traffic_route_minor')
        for name in polygon_datasets:
            with self.subTest(dataset=name):
                self.assertIn(name, convert.KML_STYLES)
                self.assertIn('poly_color', convert.KML_STYLES[name])
                # 先頭2桁はアルファ値。白({RGB}ffffff)そのものではないことを確認する。
                self.assertNotEqual(convert.KML_STYLES[name]['poly_color'][2:], 'ffffff')

    def test_icon_style_adds_icon_style_and_href(self):
        geojson = {'features': [LIGHT_HOUSE]}
        style = convert.KML_STYLES['light_house']

        kml = convert.geojson_to_kml(geojson, style=style)

        kml_style = kml.find('.//Style')
        self.assertEqual(kml_style.get('id'), style['id'])
        self.assertEqual(kml_style.find('IconStyle/Icon/href').text, style['icon'])
        self.assertIsNone(kml_style.find('LineStyle'))
        self.assertIsNone(kml_style.find('PolyStyle'))

        placemark = kml.find('.//Placemark')
        self.assertEqual(placemark.find('styleUrl').text, '#' + style['id'])

    def test_light_icon_styles_are_visually_distinct(self):
        # アイコン画像自体は使い回すことがあるため、(画像, 色, 大きさ)の組み合わせで区別できていればよい
        light_names = ('light_house', 'pillar_lights', 'other_lights', 'float_lights')
        appearances = {
            (convert.KML_STYLES[name]['icon'],
             convert.KML_STYLES[name].get('icon_color'),
             convert.KML_STYLES[name].get('icon_scale'))
            for name in light_names
        }
        self.assertEqual(len(appearances), len(light_names))


if __name__ == '__main__':
    unittest.main()
