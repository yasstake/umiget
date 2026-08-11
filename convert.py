import glob
import json
import os
import sys
import xml.etree.ElementTree as ET

'''
https://wiki.openstreetmap.org/wiki/Seamarks/Seamark_Objects
'''

'''
https://wiki.openstreetmap.org/wiki/Tag:seamark:type%3Dharbour
マリーナ
seamark:type=harbour
seamark:category=marina
name:en  英語名
name     ローカル名

漁港
seamark:category=fishing


'''


# SEAMARK_NS = 'seamark:'
SEAMARK_NS = ''
PROPERTIES = 'properties'

SEAMARK_MARINA = ''

def load(file):
    with open(file, 'r') as f:
        j = json.load(f)

    return j

def process(file, filter, outfile):
    j = load(file)

    with open(outfile, 'w') as f:
        for line in j['features']:
            p = filter(line)
            f.write(json.dumps(p, ensure_ascii=False))
            f.write('\n')


def basic_property(line, p=None):
    if not p:
        p = {}

    p['type'] = line['type']
    p['geometry'] = line['geometry']
    p[PROPERTIES] = {}

    return p


def marina_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'harbour'
    p[PROPERTIES][SEAMARK_NS + 'category'] = 'marina'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['マリーナの名称']

    return p


def fisher_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'harbour'
    p[PROPERTIES][SEAMARK_NS + 'category'] = 'fishing'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['漁港名']

    return p


def fisher_fixnet_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'marine_farm'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['ラベル追加文字']

    return p

def float_lights_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'buoy'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['名称']
    p[PROPERTIES]['light_id'] = line_p['航路標識番号']

    return p


def light_house_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'light_minor'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['名称']
    p[PROPERTIES]['light_id'] = line_p['航路標識番号']

    return p

def pillar_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'light_minor'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['名称']
    p[PROPERTIES]['light_id'] = line_p['航路標識番号']

    return p

def other_lights_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'light'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['名称']
    p[PROPERTIES]['light_id'] = line_p['航路標識番号']

    return p


'''
Google Earth (KML) 変換

umiget.py が data/*.json に保存する生のGeoJSONを、Google Earthで直接開ける
KMLファイルに変換する。データセットごとに正確な名前フィールドは分からない
ものもあるため、既知のフィールド名を優先順位付きで試す方式にしている。
'''

KML_NAMESPACE = 'http://www.opengis.net/kml/2.2'

# Placemarkの名前として使うフィールド候補(優先順)。
# 灯台等は「名称」、漁港は「漁港名」、マリーナは「マリーナの名称」、
# 航路は「航路名」、定置漁業権は「ラベル追加文字」で確認済み。
DEFAULT_NAME_FIELDS = ('名称', '漁港名', 'マリーナの名称', '航路名', 'ラベル追加文字', '港名', '読み')

# KMLの色は aabbggrr (アルファ,青,緑,赤) の順。
RED = '0000ff'
ORANGE = '00a5ff'
YELLOW = '00ffff'
BLUE = 'ff0000'

# Google Earthが標準で参照できる共有アイコン(http://maps.google.com/mapfiles/kml/)。
GOOGLE_ICONS = 'http://maps.google.com/mapfiles/kml/shapes/'


def _alpha_hex(opacity):
    """0.0-1.0の不透明度をKMLのアルファ2桁16進に変換する。"""
    return format(round(255 * opacity), '02x')


# ファイル名(拡張子抜き) -> スタイル。
# KMLの PolyStyle は単色塗りつぶしのみで斜線ハッチ等のパターンは表現できないため、
# 定置漁業権と区画漁業権は透過率と外枠の有無で区別する。
KML_STYLES = {
    # 定置漁業権: 赤、透過65%(不透明度35%)、外枠1px
    'fisher_fix_net': {
        'id': 'fixedNetStyle',
        'poly_color': _alpha_hex(0.35) + RED,
        'outline': True,
        'line_color': _alpha_hex(1.0) + RED,
        'line_width': 1,
    },
    # 区画漁業権: 赤、透過75%(不透明度25%)、枠なし
    'fisher_demarcated_net': {
        'id': 'demarcatedNetStyle',
        'poly_color': _alpha_hex(0.25) + RED,
        'outline': False,
    },
    # 共同漁業権: 定置・区画漁業権(赤系)と区別するためオレンジ、透過75%(不透明度25%)、外枠1px
    'fisher_common_net': {
        'id': 'commonNetStyle',
        'poly_color': _alpha_hex(0.25) + ORANGE,
        'outline': True,
        'line_color': _alpha_hex(1.0) + ORANGE,
        'line_width': 1,
    },
    # 海交法航路: 青、透過75%(不透明度25%)、外枠1px
    'traffic_route_major': {
        'id': 'trafficRouteMajorStyle',
        'poly_color': _alpha_hex(0.25) + BLUE,
        'outline': True,
        'line_color': _alpha_hex(1.0) + BLUE,
        'line_width': 1,
    },
    # 港則法航路: 青、透過85%(不透明度15%)、枠なし
    'traffic_route_minor': {
        'id': 'trafficRouteMinorStyle',
        'poly_color': _alpha_hex(0.15) + BLUE,
        'outline': False,
    },
    # 灯台: 簡易な星印アイコンで表す。黄色にし、他の灯(黄・小)とは大きさで区別する。
    'light_house': {
        'id': 'lightHouseStyle',
        'icon': GOOGLE_ICONS + 'star.png',
        'icon_color': _alpha_hex(1.0) + YELLOW,
        'icon_scale': 1.2,
    },
    # 灯標: 海図の記号にならい、三角形アイコンで表す。
    'pillar_lights': {
        'id': 'pillarLightStyle',
        'icon': GOOGLE_ICONS + 'triangle.png',
        'icon_color': _alpha_hex(1.0) + ORANGE,
        'icon_scale': 1.0,
    },
    # 灯(その他): 海図の灯火記号(光芒)にならい、星形アイコンで表す。
    'other_lights': {
        'id': 'otherLightStyle',
        'icon': GOOGLE_ICONS + 'star.png',
        'icon_color': _alpha_hex(1.0) + YELLOW,
        'icon_scale': 0.8,
    },
    # 灯浮標(ブイ): 水上の浮体標識であることが分かるよう、菱形アイコンで表す。
    'float_lights': {
        'id': 'floatLightStyle',
        'icon': GOOGLE_ICONS + 'open-diamond.png',
        'icon_color': _alpha_hex(1.0) + YELLOW,
        'icon_scale': 1.0,
    },
}


def _coord_text(coord):
    return ','.join(str(c) for c in coord)


def _ring_text(ring):
    return ' '.join(_coord_text(c) for c in ring)


def _build_polygon(parent, rings):
    polygon = ET.SubElement(parent, 'Polygon')
    outer = ET.SubElement(polygon, 'outerBoundaryIs')
    ET.SubElement(ET.SubElement(outer, 'LinearRing'), 'coordinates').text = _ring_text(rings[0])
    for inner_ring in rings[1:]:
        inner = ET.SubElement(polygon, 'innerBoundaryIs')
        ET.SubElement(ET.SubElement(inner, 'LinearRing'), 'coordinates').text = _ring_text(inner_ring)


def build_geometry(parent, geometry):
    if not geometry:
        return

    gtype = geometry.get('type')
    coordinates = geometry.get('coordinates')

    if gtype == 'Point':
        ET.SubElement(ET.SubElement(parent, 'Point'), 'coordinates').text = _coord_text(coordinates)
    elif gtype == 'MultiPoint':
        multi = ET.SubElement(parent, 'MultiGeometry')
        for point in coordinates:
            ET.SubElement(ET.SubElement(multi, 'Point'), 'coordinates').text = _coord_text(point)
    elif gtype == 'LineString':
        ET.SubElement(ET.SubElement(parent, 'LineString'), 'coordinates').text = _ring_text(coordinates)
    elif gtype == 'MultiLineString':
        multi = ET.SubElement(parent, 'MultiGeometry')
        for line in coordinates:
            ET.SubElement(ET.SubElement(multi, 'LineString'), 'coordinates').text = _ring_text(line)
    elif gtype == 'Polygon':
        _build_polygon(parent, coordinates)
    elif gtype == 'MultiPolygon':
        multi = ET.SubElement(parent, 'MultiGeometry')
        for polygon_rings in coordinates:
            _build_polygon(multi, polygon_rings)
    # GeometryCollection はこのデータセットには現れないため未対応


def _build_style(document, style):
    kml_style = ET.SubElement(document, 'Style', {'id': style['id']})

    if 'icon' in style:
        icon_style = ET.SubElement(kml_style, 'IconStyle')
        if 'icon_color' in style:
            ET.SubElement(icon_style, 'color').text = style['icon_color']
        if 'icon_scale' in style:
            ET.SubElement(icon_style, 'scale').text = str(style['icon_scale'])
        icon = ET.SubElement(icon_style, 'Icon')
        ET.SubElement(icon, 'href').text = style['icon']

    if 'poly_color' in style:
        outline = style.get('outline', True)
        if outline:
            line_style = ET.SubElement(kml_style, 'LineStyle')
            ET.SubElement(line_style, 'color').text = style['line_color']
            ET.SubElement(line_style, 'width').text = str(style['line_width'])
        poly_style = ET.SubElement(kml_style, 'PolyStyle')
        ET.SubElement(poly_style, 'color').text = style['poly_color']
        ET.SubElement(poly_style, 'fill').text = '1'
        ET.SubElement(poly_style, 'outline').text = '1' if outline else '0'


# 灯台・灯標・灯・灯浮標(名前フィールドが「名称」のデータセット)は、
# 名称に「防波堤」を含む場合はラベルを表示しない(空白にする)。
SUPPRESS_NAME_KEYWORD = '防波堤'


def _placemark_name(properties, name_fields):
    for field in name_fields:
        value = properties.get(field)
        if value not in (None, '', 'null'):
            value = str(value)
            if field == '名称' and SUPPRESS_NAME_KEYWORD in value:
                return ''
            return value

    return ''


def geojson_to_kml(geojson, name_fields=DEFAULT_NAME_FIELDS, document_name='umiget', style=None):
    kml = ET.Element('kml', {'xmlns': KML_NAMESPACE})
    document = ET.SubElement(kml, 'Document')
    ET.SubElement(document, 'name').text = document_name

    if style:
        _build_style(document, style)

    for feature in geojson.get('features', []):
        placemark = ET.SubElement(document, 'Placemark')
        properties = feature.get(PROPERTIES) or {}

        name = _placemark_name(properties, name_fields)
        if name:
            ET.SubElement(placemark, 'name').text = name

        if style:
            ET.SubElement(placemark, 'styleUrl').text = '#' + style['id']

        if properties:
            extended_data = ET.SubElement(placemark, 'ExtendedData')
            for key, value in properties.items():
                data = ET.SubElement(extended_data, 'Data', {'name': str(key)})
                ET.SubElement(data, 'value').text = '' if value is None else str(value)

        build_geometry(placemark, feature.get('geometry'))

    return kml


def save_kml(file, outfile, name_fields=DEFAULT_NAME_FIELDS, style=None):
    geojson = load(file)
    kml = geojson_to_kml(geojson, name_fields=name_fields,
                          document_name=os.path.splitext(os.path.basename(outfile))[0],
                          style=style)

    tree = ET.ElementTree(kml)
    ET.indent(tree, space='  ')
    tree.write(outfile, encoding='utf-8', xml_declaration=True)


def convert_all_to_kml(data_dir='./data'):
    for file in sorted(glob.glob(os.path.join(data_dir, '*.json'))):
        outfile = os.path.splitext(file)[0] + '.kml'
        basename = os.path.splitext(os.path.basename(file))[0]
        print('{} -> {}'.format(file, outfile))
        save_kml(file, outfile, style=KML_STYLES.get(basename))


if __name__ == '__main__':
    if '--kml' in sys.argv:
        convert_all_to_kml()
    else:
        # マリーナは https://portal.msil.go.jp/msil-api-list の公開APIカタログに
        # 掲載されておらず、umiget.py はもう marina.json を生成しないため対象外にしている。
        process('./data/fisher_fix_net.json', fisher_fixnet_property, 'fisher_net.out.json')
        process('./data/float_lights.json', float_lights_property, 'float.out.json')
        process('./data/light_house.json', light_house_property, 'light_house.out.json')
        process('./data/other_lights.json', other_lights_property, 'light.out.json')



