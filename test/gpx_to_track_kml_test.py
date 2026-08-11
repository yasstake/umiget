import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

import gpx_to_track_kml

GPX_WITH_TIME = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>sample track</name>
    <trkseg>
      <trkpt lat="43.208836" lon="141.047059">
        <time>2026-06-09T22:49:55Z</time>
      </trkpt>
      <trkpt lat="43.209150" lon="141.047243">
        <time>2026-06-09T22:50:07Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>
'''

GPX_WITHOUT_TIME = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <trkseg>
      <trkpt lat="43.0" lon="141.0"></trkpt>
    </trkseg>
  </trk>
</gpx>
'''

KML_NS = {'kml': gpx_to_track_kml.KML_NAMESPACE, 'gx': gpx_to_track_kml.GX_NAMESPACE}


class GpxToTrackKmlTestCase(unittest.TestCase):
    def _write_gpx(self, tmp, content, name='track.gpx'):
        path = os.path.join(tmp, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_gpx_to_track_kml_pairs_when_and_coord_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_WITH_TIME)
            kml = gpx_to_track_kml.gpx_to_track_kml(path)

        track = kml.find('.//Placemark')
        whens = [e.text for e in track.iter('when')]
        coords = [e.text for e in track.iter('gx:coord')]

        self.assertEqual(whens, ['2026-06-09T22:49:55Z', '2026-06-09T22:50:07Z'])
        self.assertEqual(coords, ['141.047059 43.208836 0.0', '141.047243 43.20915 0.0'])
        self.assertEqual(track.find('name').text, 'sample track')

    def test_points_without_time_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_WITHOUT_TIME)

            with self.assertRaises(ValueError):
                gpx_to_track_kml.gpx_to_track_kml(path)

    def test_start_and_goal_placemarks_use_first_and_last_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_WITH_TIME)
            kml = gpx_to_track_kml.gpx_to_track_kml(path)

        placemarks = kml.findall('.//Placemark')
        start, goal = placemarks[1], placemarks[2]

        self.assertEqual(start.find('name').text, 'START')
        self.assertEqual(start.find('styleUrl').text, '#startStyle')
        self.assertEqual(start.find('Point/coordinates').text, '141.047059,43.208836,0.0')

        self.assertEqual(goal.find('name').text, 'GOAL')
        self.assertEqual(goal.find('styleUrl').text, '#goalStyle')
        self.assertEqual(goal.find('Point/coordinates').text, '141.047243,43.20915,0.0')

    def test_start_and_goal_styles_have_distinct_icons_and_colors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_WITH_TIME)
            kml = gpx_to_track_kml.gpx_to_track_kml(path)

        styles = {s.get('id'): s for s in kml.findall('.//Style')}

        start_icon = styles['startStyle'].find('IconStyle/Icon/href').text
        goal_icon = styles['goalStyle'].find('IconStyle/Icon/href').text
        self.assertNotEqual(start_icon, goal_icon)

        start_color = styles['startStyle'].find('IconStyle/color').text
        goal_color = styles['goalStyle'].find('IconStyle/color').text
        self.assertNotEqual(start_color, goal_color)

    def test_save_track_kml_writes_valid_gx_track(self):
        with tempfile.TemporaryDirectory() as tmp:
            infile = self._write_gpx(tmp, GPX_WITH_TIME)
            outfile = os.path.join(tmp, 'out.kml')

            gpx_to_track_kml.save_track_kml(infile, outfile)

            tree = ET.parse(outfile)
            tracks = tree.findall('.//kml:Placemark/gx:Track', KML_NS)
            self.assertEqual(len(tracks), 1)


if __name__ == '__main__':
    unittest.main()
