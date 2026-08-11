import csv
import json
import os
import tempfile
import unittest

import gpx_to_earth_studio

GPX_TWO_LEGS = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>sample track</name>
    <trkseg>
      <trkpt lat="43.000000" lon="141.000000">
        <ele>10</ele>
        <time>2026-06-09T00:00:00Z</time>
      </trkpt>
      <trkpt lat="43.001000" lon="141.000000">
        <ele>20</ele>
        <time>2026-06-09T00:00:10Z</time>
      </trkpt>
      <trkpt lat="43.001000" lon="141.001000">
        <ele>30</ele>
        <time>2026-06-09T00:01:40Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>
'''


# 進行方向が0度/360度の境界をまたぐ(約10度->約350度、実際の旋回は約20度)トラック。
# DAY01_bikuni.gpxで実際に発生した「最初の地点で360度近く回転する」不具合の再現用。
GPX_HEADING_WRAP = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <trkseg>
      <trkpt lat="43.000000" lon="141.000000">
        <ele>0</ele>
        <time>2026-06-09T00:00:00Z</time>
      </trkpt>
      <trkpt lat="43.002000" lon="141.000500">
        <ele>0</ele>
        <time>2026-06-09T00:00:10Z</time>
      </trkpt>
      <trkpt lat="43.004000" lon="141.000000">
        <ele>0</ele>
        <time>2026-06-09T00:00:20Z</time>
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


class HeadingTestCase(unittest.TestCase):
    def test_heading_north_and_east(self):
        coords = [(141.0, 43.0), (141.0, 43.001), (141.001, 43.001)]
        headings = gpx_to_earth_studio.headings_from_coords(coords)

        self.assertEqual(len(headings), 3)
        self.assertAlmostEqual(headings[0], 0.0, delta=1.0)  # 真北へ
        self.assertAlmostEqual(headings[1], 90.0, delta=1.0)  # 真東へ
        self.assertEqual(headings[2], headings[1])  # 最終点は直前と同じ向き

    def test_single_point_does_not_crash(self):
        headings = gpx_to_earth_studio.headings_from_coords([(141.0, 43.0)])
        self.assertEqual(headings, [0.0])


class UnwrapHeadingsTestCase(unittest.TestCase):
    def test_takes_the_short_way_across_the_0_360_boundary(self):
        # 実データ(DAY01_bikuni.gpx)で発生した、素の値では4.24->267.97と大回り(+263.7度)に
        # なってしまうケース。短い方(-96.3度)に補正されるはず。
        unwrapped = gpx_to_earth_studio._unwrap_headings([4.24, 267.97], start=4.24)

        self.assertAlmostEqual(unwrapped[0], 4.24)
        self.assertAlmostEqual(unwrapped[1], 4.24 - 96.27, places=1)
        self.assertLess(abs(unwrapped[1] - unwrapped[0]), 180)

    def test_leaves_small_changes_untouched(self):
        unwrapped = gpx_to_earth_studio._unwrap_headings([10.0, 15.0, 12.0], start=10.0)
        self.assertEqual(unwrapped, [10.0, 15.0, 12.0])


class LookAtGeometryTestCase(unittest.TestCase):
    def test_offset_backward_moves_opposite_heading(self):
        lon, lat = 141.0, 43.0
        olon, olat = gpx_to_earth_studio._offset_point_backward(lon, lat, heading_deg=0.0, distance_m=1000.0)

        # 進行方向が真北(0度)なら、後方オフセットは南(緯度が減る)方向のはず
        self.assertLess(olat, lat)
        self.assertAlmostEqual(olon, lon, places=6)

    def test_offset_backward_zero_distance_is_a_no_op(self):
        lon, lat = 141.0, 43.0
        olon, olat = gpx_to_earth_studio._offset_point_backward(lon, lat, heading_deg=45.0, distance_m=0.0)
        self.assertEqual((olon, olat), (lon, lat))

    def test_backward_distance_increases_with_height_and_steeper_tilt(self):
        d_low_tilt = gpx_to_earth_studio._backward_distance_for_view_angle(1000.0, tilt_deg=80.0)
        d_high_tilt = gpx_to_earth_studio._backward_distance_for_view_angle(1000.0, tilt_deg=45.0)

        # tilt(水平寄り)が大きいほど、同じ高さでも対象はより遠くから見込む必要がある
        self.assertGreater(d_low_tilt, d_high_tilt)

    def test_look_at_recovers_the_offset_and_tilt_used_to_place_the_camera(self):
        target = (141.0, 43.0)
        target_alt = 0.0
        heading = 30.0
        tilt = 65.0
        height = 1000.0

        distance = gpx_to_earth_studio._backward_distance_for_view_angle(height, tilt)
        cam_lon, cam_lat = gpx_to_earth_studio._offset_point_backward(target[0], target[1], heading, distance)

        out_heading, out_tilt = gpx_to_earth_studio._look_at_heading_and_tilt(
            (cam_lon, cam_lat), height, target, target_alt)

        # 平面近似(緯度による東西距離の換算)を使うため、往復させるとわずかな誤差が乗る
        self.assertAlmostEqual(out_heading, heading, delta=0.05)
        self.assertAlmostEqual(out_tilt, tilt, delta=0.05)


class SelectIndicesTestCase(unittest.TestCase):
    def test_includes_first_and_last(self):
        idx = gpx_to_earth_studio._select_indices(100, 5)
        self.assertEqual(idx[0], 0)
        self.assertEqual(idx[-1], 99)
        self.assertLessEqual(len(idx), 5)

    def test_k_greater_than_n_returns_all(self):
        idx = gpx_to_earth_studio._select_indices(3, 10)
        self.assertEqual(idx, [0, 1, 2])


class SmoothPointsTestCase(unittest.TestCase):
    def test_window_of_one_is_a_no_op(self):
        points = [(0.0, 0.0, 0.0, 't0'), (1.0, 1.0, 1.0, 't1')]
        self.assertEqual(gpx_to_earth_studio._smooth_points(points, 1), points)

    def test_preserves_point_count_and_timestamps(self):
        points = [(float(i), float(i), float(i), 't{}'.format(i)) for i in range(10)]
        smoothed = gpx_to_earth_studio._smooth_points(points, 5)

        self.assertEqual(len(smoothed), len(points))
        self.assertEqual([p[3] for p in smoothed], [p[3] for p in points])

    def test_averages_a_local_spike(self):
        # 中央の1点だけ大きく外れた「ノイズ」を、移動平均でならせるはず
        points = [(0.0, 0.0, 0.0, 't{}'.format(i)) for i in range(5)]
        points[2] = (100.0, 0.0, 0.0, 't2')

        smoothed = gpx_to_earth_studio._smooth_points(points, 5)

        self.assertLess(smoothed[2][0], 100.0)
        self.assertGreater(smoothed[2][0], 0.0)


class LoadPointsTestCase(unittest.TestCase):
    def _write_gpx(self, tmp, content):
        path = os.path.join(tmp, 'track.gpx')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_points_without_time_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_WITHOUT_TIME)
            with self.assertRaises(ValueError):
                gpx_to_earth_studio._load_points(path)

    def test_points_are_sorted_by_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            points = gpx_to_earth_studio._load_points(path)

        self.assertEqual(len(points), 3)
        times = [p[3] for p in points]
        self.assertEqual(times, sorted(times))


class EarthStudioProjectTestCase(unittest.TestCase):
    def _write_gpx(self, tmp, content):
        path = os.path.join(tmp, 'track.gpx')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_project_has_expected_top_level_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            project = gpx_to_earth_studio.gpx_to_earth_studio_project(
                path, duration_sec=60, fps=30, altitude_offset_m=200, tilt_deg=60)

        self.assertEqual(project['modelVersion'], 17)
        self.assertEqual(project['settings']['frameRate'], 30)
        self.assertEqual(project['settings']['duration'], 1800)
        self.assertEqual(project['playbackManager']['range'], {'start': 0, 'end': 1800})
        self.assertEqual(len(project['scenes']), 1)

    def test_position_and_rotation_attribute_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            project = gpx_to_earth_studio.gpx_to_earth_studio_project(path)

        camera_group = project['scenes'][0]['attributes'][0]
        self.assertEqual(camera_group['type'], 'cameraGroup')

        position_group = camera_group['attributes'][0]
        self.assertEqual(position_group['type'], 'cameraPositionGroup')
        position_types = [a['type'] for a in position_group['attributes']]
        self.assertEqual(position_types, ['longitude', 'latitude', 'altitude'])

        rotation_group = camera_group['attributes'][2]
        self.assertEqual(rotation_group['type'], 'cameraRotationGroup')
        rotation_types = [a['type'] for a in rotation_group['attributes']]
        self.assertEqual(rotation_types, ['rotationX', 'rotationY', 'rotationZ'])

    def test_target_tracking_enables_poi_and_disables_manual_rotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            project = gpx_to_earth_studio.gpx_to_earth_studio_project(
                path, altitude_m=1000, tilt_deg=65, target_tracking=True, smooth_window=1)

        camera_group = project['scenes'][0]['attributes'][0]
        target_effect = camera_group['attributes'][1]
        self.assertEqual(target_effect['type'], 'cameraTargetEffect')

        attrs_by_type = {a['type']: a for a in target_effect['attributes']}
        self.assertEqual(attrs_by_type['enabled']['value'], {'relative': 1})
        self.assertEqual(attrs_by_type['influence']['value'], {'relative': 1})

        poi_types = [a['type'] for a in attrs_by_type['poi']['attributes']]
        self.assertEqual(poi_types, ['longitudePOI', 'latitudePOI', 'altitudePOI'])
        self.assertEqual(len(attrs_by_type['poi']['attributes'][0]['keyframes']), 3)

        rotation_group = camera_group['attributes'][2]
        for block in rotation_group['attributes']:
            self.assertNotIn('keyframes', block)

    def test_target_tracking_offsets_camera_away_from_ground_track(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            tracked = gpx_to_earth_studio.gpx_to_earth_studio_project(
                path, altitude_m=1000, tilt_deg=65, target_tracking=True, smooth_window=1)
            untracked = gpx_to_earth_studio.gpx_to_earth_studio_project(
                path, altitude_m=1000, tilt_deg=65, target_tracking=False, smooth_window=1)

        def first_lon_lat(project):
            position_group = project['scenes'][0]['attributes'][0]['attributes'][0]
            lon_block, lat_block = position_group['attributes'][0], position_group['attributes'][1]
            return lon_block['keyframes'][0]['value'], lat_block['keyframes'][0]['value']

        self.assertNotEqual(first_lon_lat(tracked), first_lon_lat(untracked))

    def test_altitude_block_has_no_value_range_but_is_logarithmic_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            project = gpx_to_earth_studio.gpx_to_earth_studio_project(path)

        position_group = project['scenes'][0]['attributes'][0]['attributes'][0]
        altitude_block = position_group['attributes'][2]

        self.assertNotIn('minValueRange', altitude_block['value'])
        self.assertNotIn('maxValueRange', altitude_block['value'])
        self.assertEqual(altitude_block['value']['logarithmic'], False)
        self.assertEqual(len(altitude_block['keyframes']), 3)

    def test_absolute_altitude_is_constant_regardless_of_terrain(self):
        # GPX_TWO_LEGSは標高10/20/30mだが、絶対高度を指定した場合は地形に関わらず一定になるはず
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            project = gpx_to_earth_studio.gpx_to_earth_studio_project(path, altitude_m=1500)

        position_group = project['scenes'][0]['attributes'][0]['attributes'][0]
        altitude_block = position_group['attributes'][2]
        values = {round(kf['value'], 12) for kf in altitude_block['keyframes']}

        expected = round(1500 * gpx_to_earth_studio.ALTITUDE_VALUE_PER_METRE, 12)
        self.assertEqual(values, {expected})

    def test_rotation_z_is_static_and_unkeyframed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            project = gpx_to_earth_studio.gpx_to_earth_studio_project(path)

        rotation_group = project['scenes'][0]['attributes'][0]['attributes'][2]
        roll_block = rotation_group['attributes'][2]

        self.assertEqual(roll_block, {'type': 'rotationZ', 'value': {}})

    def test_keyframe_times_follow_real_elapsed_time_not_point_index(self):
        # GPX_TWO_LEGS: 区間1は10秒、区間2は90秒 -> 均等圧縮でも時間比は保たれるはず
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            project = gpx_to_earth_studio.gpx_to_earth_studio_project(path)

        position_group = project['scenes'][0]['attributes'][0]['attributes'][0]
        longitude_block = position_group['attributes'][0]
        times = [kf['time'] for kf in longitude_block['keyframes']]

        self.assertEqual(times[0], 0.0)
        self.assertEqual(times[-1], 1.0)
        # 3点のうち中間点は 10/100 = 0.1 の位置にあるはず(点のインデックスで等間隔の0.5ではない)
        self.assertAlmostEqual(times[1], 0.1, places=6)

    def test_save_earth_studio_esp_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            infile = self._write_gpx(tmp, GPX_TWO_LEGS)
            outfile = os.path.join(tmp, 'out.esp')

            gpx_to_earth_studio.save_earth_studio_esp(infile, outfile)

            with open(outfile, encoding='utf-8') as f:
                project = json.load(f)
            self.assertIn('scenes', project)


class CameraKeyframeCsvTestCase(unittest.TestCase):
    def _write_gpx(self, tmp, content):
        path = os.path.join(tmp, 'track.gpx')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_rows_include_first_and_last_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            rows = gpx_to_earth_studio.gpx_to_camera_keyframe_rows(
                path, duration_sec=60, fps=30, n_keyframes=15)

        frames = [row[0] for row in rows]
        self.assertEqual(frames[0], 0)
        self.assertEqual(frames[-1], 1800 - 1)
        self.assertEqual(frames, sorted(frames))

    def test_altitude_includes_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            rows = gpx_to_earth_studio.gpx_to_camera_keyframe_rows(
                path, altitude_offset_m=200, n_keyframes=15, smooth_window=1)

        first_altitude = rows[0][3]
        self.assertEqual(first_altitude, 10 + 200)

    def test_absolute_altitude_ignores_point_elevation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            rows = gpx_to_earth_studio.gpx_to_camera_keyframe_rows(
                path, altitude_m=1500, n_keyframes=15)

        altitudes = {row[3] for row in rows}
        self.assertEqual(altitudes, {1500.0})

    def test_target_tracking_moves_camera_and_computes_look_at_tilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            tracked = gpx_to_earth_studio.gpx_to_camera_keyframe_rows(
                path, altitude_m=1000, tilt_deg=65, n_keyframes=15, smooth_window=1, target_tracking=True)
            untracked = gpx_to_earth_studio.gpx_to_camera_keyframe_rows(
                path, altitude_m=1000, tilt_deg=65, n_keyframes=15, smooth_window=1, target_tracking=False)

        # カメラ位置(緯度・経度)は地点の真上から後方へずれているはず
        self.assertNotEqual((tracked[0][1], tracked[0][2]), (untracked[0][1], untracked[0][2]))
        # ずれた位置から幾何計算したTiltは、対象を正確に見込むため指定tiltへ戻ってくるはず
        self.assertAlmostEqual(tracked[0][5], 65.0, places=1)

    def test_save_camera_keyframe_csv_writes_expected_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            infile = self._write_gpx(tmp, GPX_TWO_LEGS)
            outfile = os.path.join(tmp, 'out.csv')

            gpx_to_earth_studio.save_camera_keyframe_csv(infile, outfile, n_keyframes=15)

            with open(outfile, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                rows = list(reader)

        self.assertEqual(header, gpx_to_earth_studio.CSV_HEADER)
        self.assertEqual(len(rows), 3)


class IntroTrackingOutroTestCase(unittest.TestCase):
    def _write_gpx(self, tmp, content):
        path = os.path.join(tmp, 'track.gpx')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_heading_does_not_spin_the_long_way_across_the_0_360_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_HEADING_WRAP)
            points = gpx_to_earth_studio._smooth_points(gpx_to_earth_studio._load_points(path), 1)

            _, _, _, _, headings, _ = gpx_to_earth_studio.intro_tracking_outro_keyframes(
                points, altitude_m=1500, altitude_offset_m=200, tilt_deg=80,
                max_keyframes=200, intro_sec=5.0, main_sec=60.0, outro_sec=5.0)

        for h0, h1 in zip(headings, headings[1:]):
            self.assertLess(abs(h1 - h0), 180)

    def test_intro_and_outro_keyframes_freeze_at_first_and_last_tracking_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            points = gpx_to_earth_studio._smooth_points(gpx_to_earth_studio._load_points(path), 1)

            times, lons, lats, alts, headings, tilts = gpx_to_earth_studio.intro_tracking_outro_keyframes(
                points, altitude_m=1500, altitude_offset_m=200, tilt_deg=80,
                max_keyframes=200, intro_sec=5.0, main_sec=60.0, outro_sec=5.0)

        self.assertEqual(times[0], 0.0)
        self.assertEqual(times[-1], 1.0)

        # イントロ(t=0)は最初の追跡キーフレーム(t=intro_frac)と全く同じ値 -> その間は静止
        self.assertEqual((lons[0], lats[0], alts[0], headings[0], tilts[0]),
                          (lons[1], lats[1], alts[1], headings[1], tilts[1]))
        # アウトロ(t=1.0)は最後の追跡キーフレームと全く同じ値 -> その間は静止
        self.assertEqual((lons[-1], lats[-1], alts[-1], headings[-1], tilts[-1]),
                          (lons[-2], lats[-2], alts[-2], headings[-2], tilts[-2]))

    def test_middle_keyframes_stay_within_intro_and_outro_time_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            points = gpx_to_earth_studio._smooth_points(gpx_to_earth_studio._load_points(path), 1)

            times, *_ = gpx_to_earth_studio.intro_tracking_outro_keyframes(
                points, altitude_m=1500, altitude_offset_m=200, tilt_deg=80,
                max_keyframes=200, intro_sec=5.0, main_sec=60.0, outro_sec=5.0)

        total = 5.0 + 60.0 + 5.0
        intro_frac = 5.0 / total
        outro_start_frac = 1.0 - 5.0 / total
        for t in times[1:-1]:
            self.assertGreater(t, intro_frac - 1e-9)
            self.assertLess(t, outro_start_frac + 1e-9)

    def test_all_tracking_keyframes_use_the_requested_altitude_and_tilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            points = gpx_to_earth_studio._smooth_points(gpx_to_earth_studio._load_points(path), 1)

            _, _, _, alts, _, tilts = gpx_to_earth_studio.intro_tracking_outro_keyframes(
                points, altitude_m=1500, altitude_offset_m=200, tilt_deg=80,
                max_keyframes=200, intro_sec=5.0, main_sec=60.0, outro_sec=5.0)

        # イントロ/アウトロも追跡区間の値をそのまま複製するため、全区間で同じ高度・角度になる
        for alt in alts:
            self.assertEqual(alt, 1500)
        for tilt in tilts:
            self.assertAlmostEqual(tilt, 80.0, places=3)

    def test_project_duration_includes_intro_and_outro(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            project = gpx_to_earth_studio.gpx_to_earth_studio_project(
                path, duration_sec=60.0, fps=30, altitude_m=1500, tilt_deg=80,
                intro_sec=5.0, outro_sec=5.0)

        self.assertEqual(project['settings']['duration'], round(70.0 * 30))

    def test_project_rotation_keyframes_are_frozen_during_intro_and_outro(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            project = gpx_to_earth_studio.gpx_to_earth_studio_project(
                path, duration_sec=60.0, fps=30, altitude_m=1500, tilt_deg=80,
                intro_sec=5.0, outro_sec=5.0)

        rotation_group = project['scenes'][0]['attributes'][0]['attributes'][2]
        tilt_block = rotation_group['attributes'][1]

        self.assertEqual(tilt_block['keyframes'][0]['time'], 0.0)
        self.assertEqual(tilt_block['keyframes'][0]['value'], tilt_block['keyframes'][1]['value'])
        self.assertEqual(tilt_block['keyframes'][-1]['time'], 1.0)
        self.assertEqual(tilt_block['keyframes'][-1]['value'], tilt_block['keyframes'][-2]['value'])

    def test_csv_rows_freeze_at_first_and_last_tracking_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_gpx(tmp, GPX_TWO_LEGS)
            rows = gpx_to_earth_studio.gpx_to_camera_keyframe_rows(
                path, duration_sec=60.0, fps=30, altitude_m=1500, tilt_deg=80,
                n_keyframes=15, intro_sec=5.0, outro_sec=5.0)

        self.assertEqual(rows[0][0], 0)
        self.assertEqual(rows[0][1:], rows[1][1:])
        self.assertEqual(rows[-1][0], round(70.0 * 30) - 1)
        self.assertEqual(rows[-1][1:], rows[-2][1:])


if __name__ == '__main__':
    unittest.main()
