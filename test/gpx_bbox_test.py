import os
import tempfile
import unittest

import gpx_bbox

GPX_SAMPLE = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="35.0" lon="139.0"><name>start</name></wpt>
  <trk>
    <trkseg>
      <trkpt lat="36.5" lon="140.5"></trkpt>
      <trkpt lat="34.0" lon="138.0"></trkpt>
    </trkseg>
  </trk>
  <rte>
    <rtept lat="35.5" lon="141.5"></rtept>
  </rte>
</gpx>
'''


class GpxBboxTestCase(unittest.TestCase):
    def _write_gpx(self, tmp):
        path = os.path.join(tmp, 'track.gpx')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(GPX_SAMPLE)
        return path

    def test_bbox_covers_all_point_kinds(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp)
            west, south, east, north = gpx_bbox.bbox(path)

        self.assertEqual((west, south, east, north), (138.0, 34.0, 141.5, 36.5))

    def test_bbox_with_margin(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp)
            west, south, east, north = gpx_bbox.bbox(path, margin=0.1)

        self.assertAlmostEqual(west, 137.9)
        self.assertAlmostEqual(south, 33.9)
        self.assertAlmostEqual(east, 141.6)
        self.assertAlmostEqual(north, 36.6)

    def test_bbox_without_points_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'empty.gpx')
            with open(path, 'w', encoding='utf-8') as f:
                f.write('<gpx xmlns="http://www.topografix.com/GPX/1/1"></gpx>')

            with self.assertRaises(ValueError):
                gpx_bbox.bbox(path)


if __name__ == '__main__':
    unittest.main()
