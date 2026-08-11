import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

import kml_clip

KML_NS = {'kml': 'http://www.opengis.net/kml/2.2'}

BBOX = (139.0, 34.0, 141.0, 36.0)

SAMPLE_KML = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>sample</name>
<Placemark>
  <name>inside</name>
  <styleUrl>#someStyle</styleUrl>
  <ExtendedData><Data name="foo"><value>bar</value></Data></ExtendedData>
  <Point><coordinates>140,35,0</coordinates></Point>
</Placemark>
<Placemark>
  <name>outside</name>
  <Point><coordinates>150,35,0</coordinates></Point>
</Placemark>
<Placemark>
  <name>polyline</name>
  <LineString><coordinates>138,35 140,35 142,35 140,35.5 138,35.5</coordinates></LineString>
</Placemark>
<Placemark>
  <name>poly</name>
  <Polygon>
    <outerBoundaryIs><LinearRing><coordinates>138,33 142,33 142,37 138,37 138,33</coordinates></LinearRing></outerBoundaryIs>
    <innerBoundaryIs><LinearRing><coordinates>140,34.5 140.5,34.5 140.5,35 140,35 140,34.5</coordinates></LinearRing></innerBoundaryIs>
  </Polygon>
</Placemark>
</Document>
</kml>
'''


class ClipMathTestCase(unittest.TestCase):
    """幾何演算そのもの(_clip_line/_clip_polygon)を、KMLの読み書きを介さずに検証する。"""

    def test_clip_line_splits_into_multiple_parts(self):
        coords = [(138, 35), (140, 35), (142, 35), (140, 35.5), (138, 35.5)]
        parts = kml_clip._clip_line(coords, BBOX)

        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0], [(139.0, 35.0), (140, 35), (141.0, 35.0)])
        self.assertEqual(parts[1], [(141.0, 35.25), (140, 35.5), (139.0, 35.5)])

    def test_clip_line_fully_outside_returns_no_parts(self):
        coords = [(150, 35), (160, 35)]
        self.assertEqual(kml_clip._clip_line(coords, BBOX), [])

    def test_clip_polygon_keeps_hole_inside_bbox(self):
        outer = [(138, 33), (142, 33), (142, 37), (138, 37), (138, 33)]
        hole = [(140, 34.5), (140.5, 34.5), (140.5, 35), (140, 35), (140, 34.5)]

        polygons = kml_clip._clip_polygon([outer, hole], BBOX)

        self.assertEqual(len(polygons), 1)
        rings = polygons[0]
        self.assertEqual(set(rings[0]), {(139.0, 36.0), (139.0, 34.0), (141.0, 34.0), (141.0, 36.0)})
        self.assertEqual(set(rings[1]), set(hole))

    def test_clip_polygon_fully_outside_returns_empty_list(self):
        outer = [(150, 33), (152, 33), (152, 35), (150, 35), (150, 33)]
        self.assertEqual(kml_clip._clip_polygon([outer], BBOX), [])

    def test_clip_polygon_splits_non_convex_polygon_into_multiple_pieces(self):
        """非凸なPolygonが範囲の境界を複数回出入りして2つの孤立した破片に
        分かれる場合、自己交差した1つの輪郭ではなく、別々の妥当な(shapelyで
        validな)Polygonとして分割されなければならない。これはbbox切り取り
        後にGoogle My Mapsで範囲全体が塗りつぶされてしまう不具合の再現。"""
        # 2つの正方形をy=[0.9, 1.1]の細い橋でつないだダンベル型のPolygon。
        dumbbell = [
            (0, 0), (2, 0), (2, 0.9), (8, 0.9), (8, 0), (10, 0),
            (10, 2), (8, 2), (8, 1.1), (2, 1.1), (2, 2), (0, 2), (0, 0),
        ]
        # 橋をすべて除外し、2つの正方形だけを残すbbox。
        bbox = (-1, 0, 11, 0.85)

        polygons = kml_clip._clip_polygon([dumbbell], bbox)

        self.assertEqual(len(polygons), 2)
        bounds = sorted(
            (min(x for x, y in rings[0]), max(x for x, y in rings[0]))
            for rings in polygons
        )
        self.assertEqual(bounds, [(0.0, 2.0), (8.0, 10.0)])


class ClipKmlFileTestCase(unittest.TestCase):
    """clip_kml()を通じたKML読み込み->切り取り->書き出しの一連の流れを検証する。"""

    def _clip_sample(self, bbox=BBOX):
        with tempfile.TemporaryDirectory() as tmp:
            infile = os.path.join(tmp, 'in.kml')
            outfile = os.path.join(tmp, 'out.kml')

            with open(infile, 'w', encoding='utf-8') as f:
                f.write(SAMPLE_KML)

            kept, total = kml_clip.clip_kml(infile, outfile, bbox)
            tree = ET.parse(outfile)

        return kept, total, tree

    def test_placemark_outside_bbox_is_dropped(self):
        kept, total, tree = self._clip_sample()

        self.assertEqual((kept, total), (3, 4))
        names = {p.findtext('kml:name', namespaces=KML_NS) for p in tree.findall('.//kml:Placemark', KML_NS)}
        self.assertEqual(names, {'inside', 'polyline', 'poly'})

    def test_point_placemark_keeps_extended_data(self):
        _, _, tree = self._clip_sample()

        placemark = tree.findall('.//kml:Placemark', KML_NS)[0]
        self.assertEqual(placemark.findtext('kml:name', namespaces=KML_NS), 'inside')

        data = placemark.find('kml:ExtendedData/kml:Data', KML_NS)
        self.assertEqual(data.get('name'), 'foo')
        self.assertEqual(data.findtext('kml:value', namespaces=KML_NS), 'bar')

    def test_point_placemark_keeps_style_url(self):
        _, _, tree = self._clip_sample()

        placemark = tree.findall('.//kml:Placemark', KML_NS)[0]
        self.assertEqual(placemark.findtext('kml:name', namespaces=KML_NS), 'inside')
        self.assertEqual(placemark.findtext('kml:styleUrl', namespaces=KML_NS), '#someStyle')

    def test_split_line_becomes_multigeometry(self):
        _, _, tree = self._clip_sample()

        placemarks = {p.findtext('kml:name', namespaces=KML_NS): p
                      for p in tree.findall('.//kml:Placemark', KML_NS)}

        line_strings = placemarks['polyline'].findall('.//kml:LineString', KML_NS)
        self.assertEqual(len(line_strings), 2)

    def test_polygon_hole_is_preserved(self):
        _, _, tree = self._clip_sample()

        placemarks = {p.findtext('kml:name', namespaces=KML_NS): p
                      for p in tree.findall('.//kml:Placemark', KML_NS)}

        polygon = placemarks['poly'].find('kml:Polygon', KML_NS)
        self.assertIsNotNone(polygon.find('kml:outerBoundaryIs', KML_NS))
        self.assertIsNotNone(polygon.find('kml:innerBoundaryIs', KML_NS))

    def test_bbox_that_excludes_everything_yields_no_placemarks(self):
        kept, total, tree = self._clip_sample(bbox=(0.0, 0.0, 1.0, 1.0))

        self.assertEqual((kept, total), (0, 4))
        self.assertEqual(tree.findall('.//kml:Placemark', KML_NS), [])


if __name__ == '__main__':
    unittest.main()
