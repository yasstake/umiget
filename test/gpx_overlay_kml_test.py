import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

import gpx_overlay_kml

GPX_SMALL = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <trkseg>
      <trkpt lat="43.000000" lon="141.000000"><time>2026-06-09T00:00:00Z</time></trkpt>
      <trkpt lat="43.100000" lon="141.100000"><time>2026-06-09T00:10:00Z</time></trkpt>
    </trkseg>
  </trk>
</gpx>
'''

KML_NS = {'kml': 'http://www.opengis.net/kml/2.2'}


def _kml_with_placemarks(style_id, style_color, placemarks_xml):
    style_block = ''
    style_url = ''
    if style_id:
        style_block = '''<Style id="{id}"><IconStyle><color>{color}</color></IconStyle></Style>'''.format(
            id=style_id, color=style_color)
        style_url = '<styleUrl>#{}</styleUrl>'.format(style_id)

    placemarks = ''.join(
        '<Placemark><name>{name}</name>{style_url}<Point><coordinates>{lon},{lat},0</coordinates></Point></Placemark>'.format(
            name=name, lon=lon, lat=lat, style_url=style_url)
        for name, lon, lat in placemarks_xml
    )

    return '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>source</name>
    {style_block}
    {placemarks}
  </Document>
</kml>
'''.format(style_block=style_block, placemarks=placemarks)


class MarginDegreesTestCase(unittest.TestCase):
    def test_longitude_margin_grows_away_from_equator(self):
        _, lat_margin_eq = gpx_overlay_kml._margin_degrees(10.0, center_lat=0.0)
        lon_margin_eq, _ = gpx_overlay_kml._margin_degrees(10.0, center_lat=0.0)
        lon_margin_high, _ = gpx_overlay_kml._margin_degrees(10.0, center_lat=60.0)

        # 経度1度あたりの距離は高緯度ほど短くなるため、同じ10kmでも度数での幅は大きくなる
        self.assertGreater(lon_margin_high, lon_margin_eq)
        self.assertAlmostEqual(lon_margin_eq, lat_margin_eq, places=6)


class ExpandedBboxTestCase(unittest.TestCase):
    def _write_gpx(self, tmp):
        path = os.path.join(tmp, 'track.gpx')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(GPX_SMALL)
        return path

    def test_expanded_bbox_is_larger_than_raw_bbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp)
            west, south, east, north = gpx_overlay_kml.expanded_bbox(path, margin_km=10.0)

        self.assertLess(west, 141.0)
        self.assertLess(south, 43.0)
        self.assertGreater(east, 141.1)
        self.assertGreater(north, 43.1)

    def test_zero_margin_matches_raw_bbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp)
            west, south, east, north = gpx_overlay_kml.expanded_bbox(path, margin_km=0.0)

        self.assertAlmostEqual(west, 141.0, places=6)
        self.assertAlmostEqual(south, 43.0, places=6)
        self.assertAlmostEqual(east, 141.1, places=6)
        self.assertAlmostEqual(north, 43.1, places=6)


class OverlaySourceFilesTestCase(unittest.TestCase):
    def test_only_json_backed_kml_files_are_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            # a: json+kmlが揃っている -> 対象
            open(os.path.join(tmp, 'a.json'), 'w').close()
            open(os.path.join(tmp, 'a.kml'), 'w').close()
            # b: jsonはあるがkml未生成 -> 対象外
            open(os.path.join(tmp, 'b.json'), 'w').close()
            # c: GPX由来など、jsonを伴わないkml -> 対象外
            open(os.path.join(tmp, 'c.kml'), 'w').close()

            files = gpx_overlay_kml.overlay_source_files(data_dir=tmp)

        self.assertEqual(files, [os.path.join(tmp, 'a.kml')])

    def test_excluded_datasets_are_skipped_even_when_json_and_kml_both_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('fisher', 'fisher_common_net', 'traffic_route_major',
                         'traffic_route_minor', 'light_house'):
                open(os.path.join(tmp, name + '.json'), 'w').close()
                open(os.path.join(tmp, name + '.kml'), 'w').close()

            files = gpx_overlay_kml.overlay_source_files(data_dir=tmp)

        self.assertEqual(files, [os.path.join(tmp, 'light_house.kml')])


class AddTrackOverlayTestCase(unittest.TestCase):
    def test_adds_bright_yellow_green_line_style_and_placemark(self):
        with tempfile.TemporaryDirectory() as tmp:
            gpx_path = os.path.join(tmp, 'track.gpx')
            with open(gpx_path, 'w', encoding='utf-8') as f:
                f.write(GPX_SMALL)

            document = ET.Element('Document')
            gpx_overlay_kml.add_track_overlay(document, gpx_path)

        style = document.find('Style')
        self.assertEqual(style.get('id'), 'trackLineStyle')
        self.assertEqual(style.find('LineStyle/color').text, gpx_overlay_kml.TRACK_LINE_COLOR)

        placemark = document.find('Placemark')
        self.assertEqual(placemark.find('styleUrl').text, '#trackLineStyle')
        coords = placemark.find('LineString/coordinates').text
        self.assertEqual(coords, '141.0,43.0,0.0 141.1,43.1,0.0')


class MergeClippedOverlaysTestCase(unittest.TestCase):
    def test_placemarks_outside_bbox_are_dropped_and_styles_are_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            src_a = os.path.join(tmp, 'a.kml')
            src_b = os.path.join(tmp, 'b.kml')

            with open(src_a, 'w', encoding='utf-8') as f:
                f.write(_kml_with_placemarks('styleA', 'ff00ff00', [
                    ('inside_a', 141.05, 43.05),
                    ('outside_a', 200.0, 80.0),
                ]))
            with open(src_b, 'w', encoding='utf-8') as f:
                f.write(_kml_with_placemarks('styleB', 'ff0000ff', [
                    ('inside_b', 141.02, 43.02),
                ]))

            bbox = (141.0, 43.0, 141.1, 43.1)
            kml, kept, total = gpx_overlay_kml.merge_clipped_overlays([src_a, src_b], bbox)

        self.assertEqual((kept, total), (2, 3))

        style_ids = {s.get('id') for s in kml.iter('Style')}
        self.assertEqual(style_ids, {'styleA', 'styleB'})

        names = {p.findtext('name') for p in kml.iter('Placemark')}
        self.assertEqual(names, {'inside_a', 'inside_b'})

        style_urls = {p.findtext('name'): p.findtext('styleUrl') for p in kml.iter('Placemark')}
        self.assertEqual(style_urls, {'inside_a': '#styleA', 'inside_b': '#styleB'})


class SaveMergedOverlayTestCase(unittest.TestCase):
    def test_end_to_end_without_regenerating_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            gpx_path = os.path.join(tmp, 'track.gpx')
            with open(gpx_path, 'w', encoding='utf-8') as f:
                f.write(GPX_SMALL)

            data_dir = os.path.join(tmp, 'data')
            os.makedirs(data_dir)
            open(os.path.join(data_dir, 'light_house.json'), 'w').close()
            with open(os.path.join(data_dir, 'light_house.kml'), 'w', encoding='utf-8') as f:
                f.write(_kml_with_placemarks('lightHouseStyle', 'ff00ffff', [
                    ('近くの灯台', 141.05, 43.05),
                    ('遠くの灯台', 0.0, 0.0),
                ]))

            outfile = os.path.join(tmp, 'overlay.kml')
            kept, total, bbox = gpx_overlay_kml.save_merged_overlay(
                gpx_path, outfile, margin_km=10.0, data_dir=data_dir, regenerate_sources=False)

            self.assertEqual((kept, total), (1, 2))

            tree = ET.parse(outfile)
            placemarks = tree.findall('.//kml:Placemark', KML_NS)
            # クリップ済みの灯台1件 + 航跡のLineString1件
            self.assertEqual(len(placemarks), 2)

            names = {p.findtext('kml:name', namespaces=KML_NS) for p in placemarks}
            self.assertEqual(names, {'近くの灯台', '航跡'})

            track_placemark = [p for p in placemarks
                                if p.findtext('kml:name', namespaces=KML_NS) == '航跡'][0]
            self.assertEqual(track_placemark.findtext('kml:styleUrl', namespaces=KML_NS), '#trackLineStyle')


if __name__ == '__main__':
    unittest.main()
