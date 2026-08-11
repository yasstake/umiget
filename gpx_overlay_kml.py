import argparse
import glob
import math
import os
import sys
import xml.etree.ElementTree as ET

import convert
import gpx_bbox
import gpx_to_track_kml
import kml_clip

'''
GPXの航跡のバウンディングボックスを一定距離(既定10km)拡大した範囲で、
海しる(MSIL)のデータ(data/*.json, convert.pyが変換するデータセット全部)を
クリップし、GPXの航跡(明るい黄緑色のライン)も合わせて1つのKMLファイルにまとめる。

各データセットのスタイル(convert.KML_STYLES、灯台のアイコン等)はStyle要素ごと
そのままコピーして保持する。クリップにはkml_clip.pyのPlacemark単位のクリップを
再利用する(Point/LineString/Polygonのクリップロジックを重複させないため)。
'''

KM_PER_DEGREE_LAT = 111.32  # 緯度1度あたりのおおよその距離(km)

# オーバーレイの出力から除外するデータセット(漁港名・共同漁業権・海交法/港則法航路)。
# 件数が多く表示すると煩雑になる、または不要との指摘を受けて除外している。
EXCLUDED_DATASETS = frozenset({'fisher', 'fisher_common_net', 'traffic_route_major', 'traffic_route_minor'})

# 航跡ラインのスタイル。KMLの色は aabbggrr の順。
# 明るい黄緑(GreenYellow, #ADFF2F)。gpx_to_track_kml.pyのYELLOW_GREEN(#9ACD32)より明るい色にしている。
TRACK_LINE_COLOR = 'ff2fffad'
TRACK_LINE_WIDTH = 4


def _margin_degrees(margin_km, center_lat):
    """指定した距離(km)に相当する、緯度方向・経度方向それぞれの度数を返す。

    経度方向は緯度によって1度あたりの距離が変わるため、範囲の中心緯度で近似する。
    """
    lat_margin = margin_km / KM_PER_DEGREE_LAT
    lon_margin = margin_km / (KM_PER_DEGREE_LAT * math.cos(math.radians(center_lat)))
    return lon_margin, lat_margin


def expanded_bbox(gpx_file, margin_km):
    """GPXのバウンディングボックスをmargin_km(既定10km)拡大した(west, south, east, north)を返す。"""
    west, south, east, north = gpx_bbox.bbox(gpx_file)
    center_lat = (south + north) / 2
    lon_margin, lat_margin = _margin_degrees(margin_km, center_lat)
    return west - lon_margin, south - lat_margin, east + lon_margin, north + lat_margin


def overlay_source_files(data_dir='./data', excluded=EXCLUDED_DATASETS):
    """convert.pyが変換対象とする海しるデータセット(data/*.json)に対応する、
    既に生成済みの*.kmlファイルの一覧を返す(GPX由来のKMLはdata/*.jsonを
    持たないため自然に除外される)。excludedに含まれるデータセット名は出力から除く。
    """
    files = []
    for json_file in sorted(glob.glob(os.path.join(data_dir, '*.json'))):
        name = os.path.splitext(os.path.basename(json_file))[0]
        if name in excluded:
            continue

        kml_file = os.path.splitext(json_file)[0] + '.kml'
        if os.path.exists(kml_file):
            files.append(kml_file)
    return files


def _strip_namespace(elem):
    """ET.parse()で読み込むと各タグに付く"{uri}Local"形式の名前空間を取り除く。

    このファイル群のKML生成(convert.py等)はルート要素のxmlns属性だけで名前空間を
    表す簡易な方式を使っており、子要素のタグには名前空間を付けない。ET.parse()で
    読み戻した要素をそのまま混ぜて出力すると、名前空間付きの要素だけ別prefix
    (ns0:等)で出力されて不格好になるため、統合前に剥がしておく。
    """
    elem.tag = kml_clip._local(elem.tag)
    for child in elem:
        _strip_namespace(child)
    return elem


def _build_track_style(document):
    style = ET.SubElement(document, 'Style', {'id': 'trackLineStyle'})
    line_style = ET.SubElement(style, 'LineStyle')
    ET.SubElement(line_style, 'color').text = TRACK_LINE_COLOR
    ET.SubElement(line_style, 'width').text = str(TRACK_LINE_WIDTH)


def add_track_overlay(document, gpx_file):
    """GPXの航跡を、明るい黄緑色のLineString Placemarkとしてdocumentに追加する。"""
    _build_track_style(document)

    tree = ET.parse(gpx_file)
    root = tree.getroot()

    for name, points in gpx_to_track_kml.iter_tracks(root):
        placemark = ET.SubElement(document, 'Placemark')
        ET.SubElement(placemark, 'name').text = name or '航跡'
        ET.SubElement(placemark, 'styleUrl').text = '#trackLineStyle'

        line_string = ET.SubElement(placemark, 'LineString')
        ET.SubElement(line_string, 'coordinates').text = ' '.join(
            '{},{},{}'.format(lon, lat, ele) for lon, lat, ele, _time in points)


def merge_clipped_overlays(sources, bbox, document_name='overlay'):
    """複数のKMLファイルをbboxでクリップし、1つのkml.Elementに統合して返す。"""
    kml = ET.Element('kml', {'xmlns': convert.KML_NAMESPACE})
    document = ET.SubElement(kml, 'Document')
    ET.SubElement(document, 'name').text = document_name

    total = 0
    kept = 0
    for src in sources:
        tree = ET.parse(src)
        root = tree.getroot()

        for style in root.iter():
            if kml_clip._local(style.tag) == 'Style':
                document.append(_strip_namespace(style))

        for placemark in root.iter():
            if kml_clip._local(placemark.tag) != 'Placemark':
                continue

            total += 1
            clipped = kml_clip.clip_placemark(placemark, bbox)
            if clipped is not None:
                document.append(clipped)
                kept += 1

    return kml, kept, total


def save_merged_overlay(gpx_file, outfile, margin_km=10.0, data_dir='./data', regenerate_sources=True):
    if regenerate_sources:
        convert.convert_all_to_kml(data_dir=data_dir)

    bbox = expanded_bbox(gpx_file, margin_km)
    sources = overlay_source_files(data_dir=data_dir)

    kml, kept, total = merge_clipped_overlays(
        sources, bbox, document_name=os.path.splitext(os.path.basename(outfile))[0])
    add_track_overlay(kml.find('Document'), gpx_file)

    tree = ET.ElementTree(kml)
    ET.indent(tree, space='  ')
    tree.write(outfile, encoding='utf-8', xml_declaration=True)

    return kept, total, bbox


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        description='GPXのバウンディングボックスを拡大した範囲で海しるデータをクリップし、1つのKMLにまとめる')
    parser.add_argument('gpx', help='入力GPXファイル')
    parser.add_argument('-o', '--output', help='出力KMLファイル(既定: 入力と同名の_overlay.kml)')
    parser.add_argument('--margin-km', type=float, default=10.0, help='バウンディングボックスの拡大距離(km、既定10)')
    parser.add_argument('--data-dir', default='./data', help='海しるデータ(*.json/*.kml)のディレクトリ(既定./data)')
    parser.add_argument('--no-regenerate', action='store_true',
                         help='data/*.jsonからのKML再生成を省略し、既存の*.kmlをそのまま使う')
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    outfile = args.output or os.path.splitext(args.gpx)[0] + '_overlay.kml'

    kept, total, bbox = save_merged_overlay(
        args.gpx, outfile, margin_km=args.margin_km, data_dir=args.data_dir,
        regenerate_sources=not args.no_regenerate)

    print('bbox(10km拡大後): {}'.format(bbox))
    print('{}/{} 件のPlacemarkを{}に出力しました'.format(kept, total, outfile))


if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
