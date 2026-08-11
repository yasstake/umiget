import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

import gpx_to_interval_kml

GPX_ONE_HOUR = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>sample track</name>
    <trkseg>
      <trkpt lat="43.000000" lon="141.000000">
        <ele>10</ele>
        <time>2026-06-09T00:07:00Z</time>
      </trkpt>
      <trkpt lat="43.001000" lon="141.001000">
        <ele>20</ele>
        <time>2026-06-09T00:16:00Z</time>
      </trkpt>
      <trkpt lat="43.002000" lon="141.002000">
        <ele>30</ele>
        <time>2026-06-09T00:29:00Z</time>
      </trkpt>
      <trkpt lat="43.003000" lon="141.003000">
        <ele>40</ele>
        <time>2026-06-09T00:44:00Z</time>
      </trkpt>
      <trkpt lat="43.004000" lon="141.004000">
        <ele>50</ele>
        <time>2026-06-09T00:52:00Z</time>
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

KML_NS = {'kml': gpx_to_interval_kml.KML_NAMESPACE}


class CeilToClockMarkTestCase(unittest.TestCase):
    def test_rounds_up_to_next_quarter_hour(self):
        step = gpx_to_interval_kml.datetime.timedelta(minutes=15)
        dt = gpx_to_interval_kml._parse_time('2026-06-09T00:07:00Z')

        marked = gpx_to_interval_kml._ceil_to_clock_mark(dt, step)

        self.assertEqual(marked.strftime('%H:%M'), '00:15')

    def test_time_already_on_a_mark_is_unchanged(self):
        step = gpx_to_interval_kml.datetime.timedelta(minutes=15)
        dt = gpx_to_interval_kml._parse_time('2026-06-09T00:30:00Z')

        marked = gpx_to_interval_kml._ceil_to_clock_mark(dt, step)

        self.assertEqual(marked, dt)


class SamplePointsByIntervalTestCase(unittest.TestCase):
    def test_start_and_end_are_kept_as_is_and_middle_marks_are_clock_aligned(self):
        points = [
            (141.000, 43.000, 10, '2026-06-09T00:07:00Z'),  # 開始点(:15等に丸めない)
            (141.001, 43.001, 20, '2026-06-09T00:16:00Z'),
            (141.002, 43.002, 30, '2026-06-09T00:29:00Z'),
            (141.003, 43.003, 40, '2026-06-09T00:44:00Z'),
            (141.004, 43.004, 50, '2026-06-09T00:52:00Z'),  # 終了点(:45等に丸めない)
        ]

        sampled = gpx_to_interval_kml.sample_points_by_interval(points, 15)
        times = [p[3].strftime('%H:%M') for p in sampled]

        # 開始(00:07)・終了(00:52)はそのまま。中間は時計の00:15,00:30,00:45を
        # 目標に一番近い実測点(00:16, 00:29, 00:44)が選ばれる(開始時刻からのオフセットではない)。
        self.assertEqual(times, ['00:07', '00:16', '00:29', '00:44', '00:52'])

    def test_start_that_already_lands_on_a_mark_is_not_duplicated(self):
        points = [
            (141.0, 43.0, 0, '2026-06-09T00:00:00Z'),
            (141.0, 43.0, 0, '2026-06-09T00:20:00Z'),
        ]

        sampled = gpx_to_interval_kml.sample_points_by_interval(points, 15)
        times = [p[3].strftime('%H:%M') for p in sampled]

        # 開始(00:00)がちょうど目標時刻と重なっても、開始点として1回だけ出力する
        self.assertEqual(times, ['00:00', '00:20'])

    def test_empty_points_returns_empty(self):
        self.assertEqual(gpx_to_interval_kml.sample_points_by_interval([], 15), [])

    def test_single_point_returns_that_point(self):
        points = [(141.0, 43.0, 0, '2026-06-09T00:00:00Z')]
        sampled = gpx_to_interval_kml.sample_points_by_interval(points, 15)
        self.assertEqual(len(sampled), 1)


class GpxToIntervalKmlTestCase(unittest.TestCase):
    def _write_gpx(self, tmp, content):
        path = os.path.join(tmp, 'track.gpx')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_points_without_time_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_WITHOUT_TIME)
            with self.assertRaises(ValueError):
                gpx_to_interval_kml.gpx_to_interval_kml(path)

    def test_placemark_count_matches_sampling(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_ONE_HOUR)
            kml = gpx_to_interval_kml.gpx_to_interval_kml(path, interval_minutes=15)

        placemarks = kml.findall('.//Placemark')
        self.assertEqual(len(placemarks), 5)

    def test_placemark_name_is_jst_formatted_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_ONE_HOUR)
            kml = gpx_to_interval_kml.gpx_to_interval_kml(path, interval_minutes=15)

        first = kml.find('.//Placemark')
        # 00:07 UTC -> 09:07 JST
        self.assertEqual(first.find('name').text, '06/09 09:07')

    def test_placemark_coordinates_use_the_selected_points_ele(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_ONE_HOUR)
            kml = gpx_to_interval_kml.gpx_to_interval_kml(path, interval_minutes=15)

        first = kml.find('.//Placemark')
        self.assertEqual(first.find('Point/coordinates').text, '141.0,43.0,10.0')

    def test_save_interval_kml_writes_valid_xml_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            infile = self._write_gpx(tmp, GPX_ONE_HOUR)
            outfile = os.path.join(tmp, 'out.kml')

            gpx_to_interval_kml.save_interval_kml(infile, outfile, interval_minutes=15)

            tree = ET.parse(outfile)
            placemarks = tree.findall('.//kml:Placemark', KML_NS)
            self.assertEqual(len(placemarks), 5)


if __name__ == '__main__':
    unittest.main()
