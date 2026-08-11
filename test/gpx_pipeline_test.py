import json
import os
import tempfile
import unittest

import gpx_pipeline

GPX_SMALL = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>sample track</name>
    <trkseg>
      <trkpt lat="43.000000" lon="141.000000">
        <ele>10</ele>
        <time>2026-06-09T00:00:00Z</time>
      </trkpt>
      <trkpt lat="43.010000" lon="141.010000">
        <ele>20</ele>
        <time>2026-06-09T00:10:00Z</time>
      </trkpt>
      <trkpt lat="43.020000" lon="141.020000">
        <ele>30</ele>
        <time>2026-06-09T00:20:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>
'''


class RunPipelineTestCase(unittest.TestCase):
    def test_produces_all_four_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            gpx_path = os.path.join(tmp, 'track.gpx')
            with open(gpx_path, 'w', encoding='utf-8') as f:
                f.write(GPX_SMALL)

            data_dir = os.path.join(tmp, 'data')
            os.makedirs(data_dir)
            with open(os.path.join(data_dir, 'light_house.json'), 'w', encoding='utf-8') as f:
                json.dump({'type': 'FeatureCollection', 'features': [
                    {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [141.01, 43.01]},
                     'properties': {'名称': '近くの灯台', '航路標識番号': 1}},
                    {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [0.0, 0.0]},
                     'properties': {'名称': '遠くの灯台', '航路標識番号': 2}},
                ]}, f, ensure_ascii=False)

            result = gpx_pipeline.run_pipeline(gpx_path, data_dir=data_dir)

            self.assertTrue(os.path.exists(result['track_kml']))
            self.assertTrue(os.path.exists(result['esp_file']))
            self.assertTrue(os.path.exists(result['csv_file']))
            self.assertTrue(os.path.exists(result['overlay_kml']))
            self.assertEqual(result['overlay_kept'], 1)
            self.assertEqual(result['overlay_total'], 2)

    def test_earth_studio_defaults_match_session_settings(self):
        self.assertEqual(gpx_pipeline.EARTH_STUDIO_DEFAULTS['altitude_m'], 1500.0)
        self.assertEqual(gpx_pipeline.EARTH_STUDIO_DEFAULTS['tilt_deg'], 80.0)
        self.assertEqual(gpx_pipeline.EARTH_STUDIO_DEFAULTS['max_keyframes'], 10)
        self.assertEqual(gpx_pipeline.EARTH_STUDIO_DEFAULTS['intro_sec'], 5.0)
        self.assertEqual(gpx_pipeline.EARTH_STUDIO_DEFAULTS['outro_sec'], 5.0)


if __name__ == '__main__':
    unittest.main()
