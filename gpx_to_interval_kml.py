import argparse
import datetime
import os
import sys
import xml.etree.ElementTree as ET

import gpx_to_track_kml

'''
GPXのトラックから、一定間隔(既定15分)ごとに実際の記録点のうち最も近いものを
選び出し、時刻ラベル付きのPlacemarkとしてKMLに出力する。

開始点・終了点は記録された最初/最後の点をそのまま使い、その間は記録開始時刻からの
オフセットではなく、時計の00分/15分/30分/45分(interval_minutesの倍数)に揃えた
目標時刻ごとに最も近い実測点を選ぶ。

補間はせず、各目標時刻に最も近い実測点(緯度・経度・標高)をそのまま使う。
ラベルはGPXの記録時刻(UTC)を日本時間(UTC+9)に変換して表示する
(UTC-JSTの差は9時間=15分の倍数のため、UTC基準で15分区切りに揃えればJST表示上でも
00/15/30/45分に揃う)。
'''

KML_NAMESPACE = gpx_to_track_kml.KML_NAMESPACE
JST = datetime.timezone(datetime.timedelta(hours=9))

INTERVAL_ICON = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
INTERVAL_ICON_COLOR = 'ff0080ff'  # aabbggrr


def _parse_time(text):
    return datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)


_EPOCH_UTC = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


def _ceil_to_clock_mark(dt, step):
    """dt以上で、時計(エポック起点)のstep間隔に揃った直近の時刻を返す
    (interval_minutes=15なら00分/15分/30分/45分)。"""
    elapsed = dt - _EPOCH_UTC
    remainder = elapsed % step
    if remainder == datetime.timedelta(0):
        return dt
    return dt + (step - remainder)


def _nearest_point(parsed, j, t):
    """parsed[j:]の中から時刻tに最も近い点を探し、そのインデックスを返す
    (parsed・tはともに時刻昇順で呼ばれる前提の二分探索的な逐次移動)。"""
    n = len(parsed)
    while j + 1 < n and abs(parsed[j + 1][3] - t) < abs(parsed[j][3] - t):
        j += 1
    return j


def sample_points_by_interval(points, interval_minutes):
    """points: [(lon, lat, ele, time文字列), ...] を受け取り、(lon, lat, ele, datetime)の
    リストを返す。

    最初と最後の点はそのまま含め、その間は時計のinterval_minutes分刻み
    (00/15/30/45等)の目標時刻ごとに最も近い実測点を選ぶ。
    """
    if not points:
        return []

    parsed = sorted(
        ((lon, lat, ele, _parse_time(t)) for lon, lat, ele, t in points),
        key=lambda p: p[3],
    )

    t0 = parsed[0][3]
    t_last = parsed[-1][3]
    step = datetime.timedelta(minutes=interval_minutes)

    result = [parsed[0]]
    j = 0

    t = _ceil_to_clock_mark(t0, step)
    if t <= t0:
        t += step

    while t < t_last:
        j = _nearest_point(parsed, j, t)
        if parsed[j] != result[-1]:
            result.append(parsed[j])
        t += step

    if parsed[-1] != result[-1]:
        result.append(parsed[-1])

    return result


def _build_style(document):
    style = ET.SubElement(document, 'Style', {'id': 'intervalPointStyle'})

    icon_style = ET.SubElement(style, 'IconStyle')
    ET.SubElement(icon_style, 'color').text = INTERVAL_ICON_COLOR
    ET.SubElement(icon_style, 'scale').text = '0.8'
    icon = ET.SubElement(icon_style, 'Icon')
    ET.SubElement(icon, 'href').text = INTERVAL_ICON

    label_style = ET.SubElement(style, 'LabelStyle')
    ET.SubElement(label_style, 'scale').text = '0.8'


def _build_placemark(document, lon, lat, ele, dt_utc):
    dt_local = dt_utc.astimezone(JST)

    placemark = ET.SubElement(document, 'Placemark')
    ET.SubElement(placemark, 'name').text = dt_local.strftime('%m/%d %H:%M')
    ET.SubElement(placemark, 'styleUrl').text = '#intervalPointStyle'
    ET.SubElement(ET.SubElement(placemark, 'Point'), 'coordinates').text = '{},{},{}'.format(lon, lat, ele)


def gpx_to_interval_kml(gpx_file, interval_minutes=15, document_name='interval_points'):
    tree = ET.parse(gpx_file)
    root = tree.getroot()

    kml = ET.Element('kml', {'xmlns': KML_NAMESPACE})
    document = ET.SubElement(kml, 'Document')
    ET.SubElement(document, 'name').text = document_name
    _build_style(document)

    found = False
    for _name, points in gpx_to_track_kml.iter_tracks(root):
        for lon, lat, ele, dt in sample_points_by_interval(points, interval_minutes):
            _build_placemark(document, lon, lat, ele, dt)
            found = True

    if not found:
        raise ValueError(
            'GPXファイルに時刻付きのトラックポイント(<trkpt><time>)が見つかりません: {}'.format(gpx_file))

    return kml


def save_interval_kml(gpx_file, outfile, interval_minutes=15):
    kml = gpx_to_interval_kml(gpx_file, interval_minutes=interval_minutes,
                               document_name=os.path.splitext(os.path.basename(outfile))[0])

    tree = ET.ElementTree(kml)
    ET.indent(tree, space='  ')
    tree.write(outfile, encoding='utf-8', xml_declaration=True)


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        description='GPXのトラックから一定間隔(既定15分)ごとの記録点をKMLに出力する')
    parser.add_argument('gpx', help='入力GPXファイル')
    parser.add_argument('-o', '--output', help='出力KMLファイル(既定: 入力と同名の_interval.kml)')
    parser.add_argument('--interval', type=float, default=15.0, help='間隔(分、既定15)')
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    outfile = args.output or os.path.splitext(args.gpx)[0] + '_interval.kml'

    save_interval_kml(args.gpx, outfile, interval_minutes=args.interval)
    print('{} -> {}'.format(args.gpx, outfile))


if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
