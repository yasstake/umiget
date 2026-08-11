import argparse
import json
import sys
import xml.etree.ElementTree as ET

'''
GPXファイル(ウェイポイント/トラック/ルート)からバウンディングボックスを算出して表示する。

出力は "west south east north" (経度最小 緯度最小 経度最大 緯度最大) の順で、
ogr2ogr の -clipsrc や kml_clip.py の引数とそのまま組み合わせられる:

    python kml_clip.py in.kml out.kml $(python gpx_bbox.py track.gpx)
'''

POINT_TAGS = ('wpt', 'trkpt', 'rtept')


def _local(tag):
    return tag.rsplit('}', 1)[-1]


def iter_points(root):
    for elem in root.iter():
        if _local(elem.tag) in POINT_TAGS:
            lat = elem.get('lat')
            lon = elem.get('lon')
            if lat is not None and lon is not None:
                yield float(lon), float(lat)


def bbox(file, margin=0.0):
    tree = ET.parse(file)
    root = tree.getroot()

    lons = []
    lats = []
    for lon, lat in iter_points(root):
        lons.append(lon)
        lats.append(lat)

    if not lons:
        raise ValueError('GPXファイルに座標点(wpt/trkpt/rtept)が見つかりません: {}'.format(file))

    return (min(lons) - margin, min(lats) - margin, max(lons) + margin, max(lats) + margin)


def _parse_args(argv):
    parser = argparse.ArgumentParser(description='GPXファイルのバウンディングボックス(west south east north)を表示する')
    parser.add_argument('gpx', help='入力GPXファイル')
    parser.add_argument('--margin', type=float, default=0.0,
                         help='バウンディングボックスの四辺に追加する余白(度単位、既定0)')
    parser.add_argument('--json', action='store_true',
                         help='"west south east north" の代わりにJSON形式で出力する')
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)

    west, south, east, north = bbox(args.gpx, margin=args.margin)

    if args.json:
        print(json.dumps({'west': west, 'south': south, 'east': east, 'north': north}, ensure_ascii=False))
    else:
        print('{} {} {} {}'.format(west, south, east, north))


if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
