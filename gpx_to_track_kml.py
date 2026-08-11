import argparse
import os
import sys
import xml.etree.ElementTree as ET

'''
GPXのトラック(<trk>/<trkseg>/<trkpt>)を、Google Earthでアニメーション再生できる
gx:Track形式のKMLに変換する。

各trkptに<time>が必要(ないと時刻順のアニメーションにならない)。
生成したKMLをGoogle Earth Pro(デスクトップ版)で開くと画面上部にタイムスライダーが
表示され、再生すると矢印アイコンが軌跡に沿って時刻通りに動く。KMLの名前空間まわりは
convert.py と同じく、xmlns/xmlns:gx をルート要素の属性として直接書き込み、子要素も
"gx:Track" のようなプレフィックス付きの文字列タグのまま出力する簡易な方式にしている。
'''

KML_NAMESPACE = 'http://www.opengis.net/kml/2.2'
GX_NAMESPACE = 'http://www.google.com/kml/ext/2.2'

# gx:Track の先頭(現在地)に表示する、Google Earth標準の進行方向つき矢印アイコン。
TRACK_ICON = 'http://earth.google.com/images/kml-icons/track-directional/track-0.png'

# KMLの色は aabbggrr (アルファ,青,緑,赤) の順。黄緑色 = RGB(154,205,50) = #9ACD32。
YELLOW_GREEN = 'ff32cd9a'
GREEN = 'ff00ff00'
RED = 'ff0000ff'

# スタート/ゴール地点に立てる、Google Earth標準の共有アイコン。
START_ICON = 'http://maps.google.com/mapfiles/kml/shapes/flag.png'
GOAL_ICON = 'http://maps.google.com/mapfiles/kml/shapes/target.png'

START_NAME = 'START'
GOAL_NAME = 'GOAL'


def _local(tag):
    return tag.rsplit('}', 1)[-1]


def _child_text(elem, tag):
    for child in elem:
        if _local(child.tag) == tag:
            return child.text
    return None


def iter_tracks(root):
    """<trk>ごとに (名前, [(lon, lat, ele, time), ...]) を返す。timeのない点は除外する。"""
    for trk in root.iter():
        if _local(trk.tag) != 'trk':
            continue

        name = _child_text(trk, 'name') or ''
        points = []
        for trkpt in trk.iter():
            if _local(trkpt.tag) != 'trkpt':
                continue

            lat = trkpt.get('lat')
            lon = trkpt.get('lon')
            time = _child_text(trkpt, 'time')
            if lat is None or lon is None or time is None:
                continue

            ele = _child_text(trkpt, 'ele')
            points.append((float(lon), float(lat), float(ele) if ele else 0.0, time))

        if points:
            yield name, points


def _build_icon_style(document, style_id, icon, color):
    style = ET.SubElement(document, 'Style', {'id': style_id})

    icon_style = ET.SubElement(style, 'IconStyle')
    ET.SubElement(icon_style, 'color').text = color
    ET.SubElement(icon_style, 'scale').text = '1.2'
    icon_elem = ET.SubElement(icon_style, 'Icon')
    ET.SubElement(icon_elem, 'href').text = icon


def _build_style(document):
    style = ET.SubElement(document, 'Style', {'id': 'trackStyle'})

    icon_style = ET.SubElement(style, 'IconStyle')
    ET.SubElement(icon_style, 'scale').text = '1.2'
    icon = ET.SubElement(icon_style, 'Icon')
    ET.SubElement(icon, 'href').text = TRACK_ICON

    line_style = ET.SubElement(style, 'LineStyle')
    ET.SubElement(line_style, 'color').text = YELLOW_GREEN
    ET.SubElement(line_style, 'width').text = '4'

    _build_icon_style(document, 'startStyle', START_ICON, GREEN)
    _build_icon_style(document, 'goalStyle', GOAL_ICON, RED)


def _build_track_placemark(document, name, points):
    placemark = ET.SubElement(document, 'Placemark')
    ET.SubElement(placemark, 'name').text = name or 'track'
    ET.SubElement(placemark, 'styleUrl').text = '#trackStyle'

    track = ET.SubElement(placemark, 'gx:Track')
    ET.SubElement(track, 'altitudeMode').text = 'clampToGround'

    for lon, lat, ele, time in points:
        ET.SubElement(track, 'when').text = time

    for lon, lat, ele, time in points:
        ET.SubElement(track, 'gx:coord').text = '{} {} {}'.format(lon, lat, ele)


def _build_endpoint_placemark(document, name, style_id, point):
    """スタート/ゴール地点用の、通常のPlacemarkを追加する。

    gx:Trackの点と違い、Google Earth上で右クリック->プロパティから
    後で自由に名前を編集できる独立したPlacemarkにしている。
    """
    lon, lat, ele, _time = point

    placemark = ET.SubElement(document, 'Placemark')
    ET.SubElement(placemark, 'name').text = name
    ET.SubElement(placemark, 'styleUrl').text = '#' + style_id
    ET.SubElement(ET.SubElement(placemark, 'Point'), 'coordinates').text = '{},{},{}'.format(lon, lat, ele)


def gpx_to_track_kml(gpx_file, document_name='track'):
    tree = ET.parse(gpx_file)
    root = tree.getroot()

    kml = ET.Element('kml', {'xmlns': KML_NAMESPACE, 'xmlns:gx': GX_NAMESPACE})
    document = ET.SubElement(kml, 'Document')
    ET.SubElement(document, 'name').text = document_name

    _build_style(document)

    found = False
    for name, points in iter_tracks(root):
        _build_track_placemark(document, name, points)
        _build_endpoint_placemark(document, START_NAME, 'startStyle', points[0])
        _build_endpoint_placemark(document, GOAL_NAME, 'goalStyle', points[-1])
        found = True

    if not found:
        raise ValueError(
            'GPXファイルに時刻付きのトラックポイント(<trkpt><time>)が見つかりません: {}'.format(gpx_file))

    return kml


def save_track_kml(gpx_file, outfile):
    kml = gpx_to_track_kml(gpx_file, document_name=os.path.splitext(os.path.basename(outfile))[0])

    tree = ET.ElementTree(kml)
    ET.indent(tree, space='  ')
    tree.write(outfile, encoding='utf-8', xml_declaration=True)


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        description='GPXのトラックをGoogle Earthでアニメーション再生できるgx:Track入りKMLに変換する')
    parser.add_argument('gpx', help='入力GPXファイル')
    parser.add_argument('-o', '--output', help='出力KMLファイル(既定: 入力と同名の.kml)')
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    outfile = args.output or os.path.splitext(args.gpx)[0] + '.kml'

    save_track_kml(args.gpx, outfile)
    print('{} -> {}'.format(args.gpx, outfile))


if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
