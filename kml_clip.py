import argparse
import os
import sys
import xml.etree.ElementTree as ET

from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseMultipartGeometry

import convert

'''
KMLファイルをバウンディングボックス(west south east north)で切り取る。

Point は範囲内かどうかだけを判定し、LineStringは範囲の矩形で実際に線分を
切り詰める(Liang-Barsky線分クリッピング)。Polygonはshapely(GEOS)で
矩形との交差を計算する。範囲と交差しないPlacemarkは出力から除外される。

Polygonのクリッピングだけ自前のSutherland-Hodgman実装ではなくshapelyに
任せているのは、非凸なPolygonが範囲の境界を複数回出入りして複数の孤立した
破片に分割されるケースを、単純な矩形の逐次半平面クリッピングでは正しく
扱えないため。1つの輪郭にまとめようとすると境界に沿って本来つながって
いない破片同士を結ぶ辺が生じて自己交差ポリゴンになり、Google My Maps等
での表示時に本来含まれない領域まで塗りつぶされてしまう不具合があった。
'''

GEOMETRY_TAGS = ('Point', 'LineString', 'LinearRing', 'Polygon', 'MultiGeometry')


def _local(tag):
    return tag.rsplit('}', 1)[-1]


def _parse_coords(text):
    coords = []
    for token in text.split():
        parts = [p for p in token.split(',') if p != '']
        coords.append(tuple(float(p) for p in parts))
    return coords


def _parse_geometry(elem):
    tag = _local(elem.tag)

    if tag == 'Point':
        text = elem.findtext('{*}coordinates')
        coords = _parse_coords(text) if text else []
        return [('Point', coords[0])] if coords else []

    if tag in ('LineString', 'LinearRing'):
        text = elem.findtext('{*}coordinates')
        coords = _parse_coords(text) if text else []
        return [('LineString', coords)] if len(coords) > 1 else []

    if tag == 'Polygon':
        outer = elem.find('{*}outerBoundaryIs/{*}LinearRing/{*}coordinates')
        if outer is None or not outer.text:
            return []

        rings = [_parse_coords(outer.text)]
        for inner in elem.findall('{*}innerBoundaryIs/{*}LinearRing/{*}coordinates'):
            if inner.text:
                rings.append(_parse_coords(inner.text))

        return [('Polygon', rings)]

    if tag == 'MultiGeometry':
        geoms = []
        for child in elem:
            geoms.extend(_parse_geometry(child))
        return geoms

    return []


def _point_in_bbox(point, bbox):
    min_lon, min_lat, max_lon, max_lat = bbox
    x, y = point[0], point[1]
    return min_lon <= x <= max_lon and min_lat <= y <= max_lat


def _interpolate(a, b, t):
    n = min(len(a), len(b))
    return tuple(a[i] + t * (b[i] - a[i]) for i in range(n))


def _liang_barsky(p0, p1, bbox):
    min_lon, min_lat, max_lon, max_lat = bbox
    x0, y0 = p0[0], p0[1]
    dx, dy = p1[0] - x0, p1[1] - y0

    t0, t1 = 0.0, 1.0
    for p, q in (
        (-dx, x0 - min_lon),
        (dx, max_lon - x0),
        (-dy, y0 - min_lat),
        (dy, max_lat - y0),
    ):
        if p == 0:
            if q < 0:
                return None
            continue

        t = q / p
        if p < 0:
            if t > t1:
                return None
            if t > t0:
                t0 = t
        else:
            if t < t0:
                return None
            if t < t1:
                t1 = t

    if t0 > t1:
        return None

    return t0, t1


def _clip_line(coords, bbox):
    parts = []
    current = []

    for p0, p1 in zip(coords, coords[1:]):
        result = _liang_barsky(p0, p1, bbox)
        if result is None:
            if len(current) > 1:
                parts.append(current)
            current = []
            continue

        t0, t1 = result
        c0 = p0 if t0 == 0.0 else _interpolate(p0, p1, t0)
        c1 = p1 if t1 == 1.0 else _interpolate(p0, p1, t1)

        if current and current[-1] != c0:
            if len(current) > 1:
                parts.append(current)
            current = []

        if not current:
            current.append(c0)
        current.append(c1)

    if len(current) > 1:
        parts.append(current)

    return parts


def _clip_polygon(rings, bbox):
    '''Polygon(外輪+内輪の集合)を矩形bboxでクリップし、Polygonのリストを返す。

    外輪が範囲の境界を複数回出入りして複数の孤立した破片に分かれる場合は、
    その数だけPolygonを返す(呼び出し側でMultiGeometryにまとめられる)。
    GEOSの堅牢な交差演算を使うことで、自前のSutherland-Hodgman実装では
    正しく扱えなかった「複数破片への分割」や「穴の割り当て」を、自己交差
    のない妥当なポリゴンとして扱える。
    '''
    if not rings:
        return []

    try:
        polygon = Polygon(rings[0], rings[1:])
    except ValueError:
        return []

    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    if polygon.is_empty:
        return []

    clipped = polygon.intersection(box(*bbox))
    if clipped.is_empty:
        return []

    geoms = clipped.geoms if isinstance(clipped, BaseMultipartGeometry) else [clipped]

    result = []
    for geom in geoms:
        if geom.is_empty or geom.geom_type != 'Polygon':
            continue
        outer = [tuple(c) for c in geom.exterior.coords]
        holes = [[tuple(c) for c in interior.coords] for interior in geom.interiors]
        result.append([outer] + holes)

    return result


def _clip_simple_geometry(geom_type, coords, bbox):
    if geom_type == 'Point':
        return [('Point', coords)] if _point_in_bbox(coords, bbox) else []

    if geom_type == 'LineString':
        return [('LineString', part) for part in _clip_line(coords, bbox)]

    if geom_type == 'Polygon':
        return [('Polygon', polygon) for polygon in _clip_polygon(coords, bbox)]

    return []


def _parse_properties(placemark):
    properties = {}
    extended = placemark.find('{*}ExtendedData')
    if extended is not None:
        for data in extended.findall('{*}Data'):
            key = data.get('name')
            value_elem = data.find('{*}value')
            properties[key] = value_elem.text if value_elem is not None else None

    return properties


def clip_placemark(placemark, bbox):
    geom_elem = None
    for child in placemark:
        if _local(child.tag) in GEOMETRY_TAGS:
            geom_elem = child
            break

    if geom_elem is None:
        return None

    was_multi = _local(geom_elem.tag) == 'MultiGeometry'

    clipped = []
    for geom_type, coords in _parse_geometry(geom_elem):
        clipped.extend(_clip_simple_geometry(geom_type, coords, bbox))

    if not clipped:
        return None

    out = ET.Element('Placemark')

    name = placemark.findtext('{*}name')
    if name:
        ET.SubElement(out, 'name').text = name

    style_url = placemark.findtext('{*}styleUrl')
    if style_url:
        ET.SubElement(out, 'styleUrl').text = style_url

    properties = _parse_properties(placemark)
    if properties:
        extended_data = ET.SubElement(out, 'ExtendedData')
        for key, value in properties.items():
            data = ET.SubElement(extended_data, 'Data', {'name': key})
            ET.SubElement(data, 'value').text = '' if value is None else value

    if was_multi or len(clipped) > 1:
        multi = ET.SubElement(out, 'MultiGeometry')
        for geom_type, coords in clipped:
            convert.build_geometry(multi, {'type': geom_type, 'coordinates': coords})
    else:
        geom_type, coords = clipped[0]
        convert.build_geometry(out, {'type': geom_type, 'coordinates': coords})

    return out


def clip_kml(infile, outfile, bbox, document_name=None):
    tree = ET.parse(infile)
    root = tree.getroot()

    if document_name is None:
        src_document = root.find('{*}Document')
        src_name = src_document.findtext('{*}name') if src_document is not None else None
        document_name = src_name or os.path.splitext(os.path.basename(outfile))[0]

    kml = ET.Element('kml', {'xmlns': convert.KML_NAMESPACE})
    document = ET.SubElement(kml, 'Document')
    ET.SubElement(document, 'name').text = document_name

    total = 0
    kept = 0
    for placemark in root.iter():
        if _local(placemark.tag) != 'Placemark':
            continue

        total += 1
        clipped = clip_placemark(placemark, bbox)
        if clipped is not None:
            document.append(clipped)
            kept += 1

    out_tree = ET.ElementTree(kml)
    ET.indent(out_tree, space='  ')
    out_tree.write(outfile, encoding='utf-8', xml_declaration=True)

    return kept, total


def _parse_args(argv):
    parser = argparse.ArgumentParser(description='KMLファイルをバウンディングボックスで切り取る')
    parser.add_argument('input', help='入力KMLファイル')
    parser.add_argument('output', help='出力KMLファイル')
    parser.add_argument('west', type=float, help='範囲の西端(経度の最小値)')
    parser.add_argument('south', type=float, help='範囲の南端(緯度の最小値)')
    parser.add_argument('east', type=float, help='範囲の東端(経度の最大値)')
    parser.add_argument('north', type=float, help='範囲の北端(緯度の最大値)。'
                         'west/south/east/northは gpx_bbox.py の出力をそのまま渡せる '
                         '(例: python kml_clip.py in.kml out.kml $(python gpx_bbox.py track.gpx))')
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    bbox = (args.west, args.south, args.east, args.north)

    kept, total = clip_kml(args.input, args.output, bbox)
    print('{}/{} 件のPlacemarkを{}に出力しました'.format(kept, total, args.output))


if __name__ == '__main__':
    main()
