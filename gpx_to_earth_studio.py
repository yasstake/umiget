import argparse
import csv
import datetime
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

import gpx_to_track_kml

'''
GPXのトラックから、Google Earth Studioでカメラをアニメーションさせるためのデータを
2種類生成する。

Earth Studio自体にはGPX/KML/CSVからカメラのキーフレームを自動生成する公式機能が
ないため(2026年8月時点でドキュメントを確認済み。KMLインポートは静止オーバーレイの
表示にしか使えない)、代わりに以下の2通りを用意する。

1. .esp プロジェクトファイル(--esp)
   Earth Studioのプロジェクト保存形式(.esp)はJSONだが、Googleは仕様を公開していない。
   本スクリプトの変換式は https://github.com/mkatzef/google-studio-utils
   (kml_to_esp.py, MITライセンス表記なし・READMEに使用例あり)が経験的に導き出した
   ものを踏襲している。バージョンによって形式が変わり、開けなくなる可能性がある
   実験的機能である点に注意。

2. 手入力用キーフレーム表(--csv)
   .espが万一開けない場合の保険として、Earth Studioの数値欄にそのまま手入力できる
   実数値(緯度・経度・高度[m]・方位[度]・傾き[度]・傾斜[度])の表を少数点で出力する。

GPXの実時間(数時間)は、アニメーションの尺(既定60秒)に等縮尺で圧縮する
(区間ごとの実時間の比率を保ったまま尺を短くする。GPSの点の密度ではなく、
実際の経過時間に応じてキーフレームの時刻を配置する)。

カメラの向き(Heading)は進行方向(次の点への方位)を自動で向くようにし、
傾き(Tilt)と傾斜(Roll)は指定した角度で一定にする(斜め俯瞰の追従カメラ)。

イントロ/アウトロ(--intro-sec/--outro-sec)を指定すると、前後に「カメラが動かない
静止区間」を追加できる。イントロは追跡開始位置、アウトロは追跡終了位置のカメラ位置・
向きのまま止まった状態を保持するだけで、その間の演出(俯瞰カット等)は追加しない
(利用者側でEarth Studio上に手動でキーフレームを追加する前提の、単なる余白時間)。
この場合、追跡区間の向きもEarth Studioの自動追尾(POI)には頼らず、区間全体を
Heading/Tiltの手動キーフレームとして焼き込む(前後の静止区間と地続きにするため)。
'''

EARTH_CIRC_M = 2 * math.pi * 6.371e6

# .espの高度キーフレーム値は「メートル * この係数」で表す。
# https://github.com/mkatzef/google-studio-utils の kml_to_esp.py で
# 経験的に特定された値をそのまま使用している。
ALTITUDE_VALUE_PER_METRE = 1.5356706349899208e-08


def _parse_time(text):
    return datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ')


def _angle180_180(a):
    return (a + 180) % 360 - 180


def _dx_dy(c1, c2):
    lon1, lat1 = c1
    lon2, lat2 = c2
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    lat_rad = math.radians(lat1)
    dy = EARTH_CIRC_M * dlat / 360
    dx = EARTH_CIRC_M * (dlon / 360) * math.cos(lat_rad)
    return dx, dy


def _bearing(c1, c2):
    dx, dy = _dx_dy(c1, c2)
    return (90 - math.degrees(math.atan2(dy, dx))) % 360


def _offset_point_backward(lon, lat, heading_deg, distance_m):
    """(lon, lat)から、headingの逆方向(進行方向の後方)へ地表面に沿ってdistance_mだけ
    移動した地点の(lon, lat)を返す。"""
    if distance_m <= 0:
        return lon, lat

    back_bearing_rad = math.radians((heading_deg + 180) % 360)
    dx = distance_m * math.sin(back_bearing_rad)
    dy = distance_m * math.cos(back_bearing_rad)
    dlat = dy / EARTH_CIRC_M * 360
    dlon = dx / (EARTH_CIRC_M * math.cos(math.radians(lat))) * 360
    return lon + dlon, lat + dlat


def _backward_distance_for_view_angle(height_above_target_m, tilt_deg):
    """高さheight_above_target_mから、狙う俯瞰角度tilt_deg(0=真下,90=水平)で対象を
    見込むために必要な、対象からの水平方向のバックオフセット距離(m)を返す。"""
    elevation_below_horizontal = 90 - tilt_deg
    if elevation_below_horizontal <= 0 or height_above_target_m <= 0:
        return 0.0
    return height_above_target_m / math.tan(math.radians(elevation_below_horizontal))


def _look_at_heading_and_tilt(camera_coord, camera_alt, target_coord, target_alt):
    """カメラから対象を正確に見込むための(Heading, Tilt)を度で返す(対象が常に画面中心に来る向き)。"""
    dx, dy = _dx_dy(camera_coord, target_coord)
    horizontal_distance = math.hypot(dx, dy)
    heading = _bearing(camera_coord, target_coord) if horizontal_distance > 1e-6 else 0.0

    height_diff = camera_alt - target_alt
    elevation_below_horizontal = math.degrees(math.atan2(height_diff, horizontal_distance))
    tilt = max(0.0, min(90.0, 90 - elevation_below_horizontal))
    return heading, tilt


def _unwrap_headings(headings, start=0.0):
    """連続するHeadingの並びを、隣接値との差が最小になるよう±360度ずつずらして
    連続的な値に補正する(0度と360度の境界をまたぐ際に、カメラが短い方ではなく
    遠回りに回転してしまうのを防ぐ)。
    """
    unwrapped = []
    prev = start
    for h in headings:
        if abs(h - 360 - prev) < abs(h - prev):
            h -= 360
        elif abs(h + 360 - prev) < abs(h - prev):
            h += 360
        prev = h
        unwrapped.append(h)
    return unwrapped


def headings_from_coords(coords):
    """各座標について、次の点へ向く方位(度)を返す(最後の点は直前と同じ向き)。

    隣接する方位との差が最小になるよう±360する(0度と360度の間で
    カメラが不自然に回転するのを防ぐ)。
    """
    n = len(coords)
    if n == 0:
        return []
    if n == 1:
        return [0.0]

    raw = [_bearing(coords[i], coords[i + 1]) for i in range(n - 1)]
    headings = _unwrap_headings(raw)
    headings.append(headings[-1])
    return headings


def _select_indices(n, k):
    """n個から、最初と最後を含めなるべく均等な間隔でk個選んだインデックス列を返す。"""
    if k >= n:
        return list(range(n))
    if k <= 1:
        return [0]
    return sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})


def _load_points(gpx_file):
    """GPX中の全<trk>のtrkptを時刻順にまとめて (lon, lat, ele, datetime) で返す。"""
    tree = ET.parse(gpx_file)
    root = tree.getroot()

    points = []
    for _name, track_points in gpx_to_track_kml.iter_tracks(root):
        for lon, lat, ele, time in track_points:
            points.append((lon, lat, ele, _parse_time(time)))

    if not points:
        raise ValueError(
            'GPXファイルに時刻付きのトラックポイント(<trkpt><time>)が見つかりません: {}'.format(gpx_file))

    points.sort(key=lambda p: p[3])
    return points


def _smooth_points(points, window):
    """経度・緯度・標高に移動平均をかけ、GPSノイズによるカメラの向き(Heading)の
    ぶれや急な切り返しを抑える。点数と各点の時刻は変えない(中心つき移動平均、
    端は範囲を切り詰めて平均する)。
    """
    if window <= 1:
        return points

    n = len(points)
    half = window // 2
    smoothed = []
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        chunk = points[lo:hi]
        lon = sum(p[0] for p in chunk) / len(chunk)
        lat = sum(p[1] for p in chunk) / len(chunk)
        ele = sum(p[2] for p in chunk) / len(chunk)
        smoothed.append((lon, lat, ele, points[i][3]))
    return smoothed


def _time_fractions(points):
    """points(時刻順)の各点について、区間全体に対する経過時間の割合(0.0-1.0)を返す。"""
    t0 = points[0][3]
    t1 = points[-1][3]
    total_seconds = (t1 - t0).total_seconds()

    if total_seconds <= 0:
        n = len(points)
        return [i / (n - 1) if n > 1 else 0.0 for i in range(n)]

    return [(p[3] - t0).total_seconds() / total_seconds for p in points]


# ---------------------------------------------------------------------------
# .esp プロジェクトファイル生成
# ---------------------------------------------------------------------------

def _keyframe_block(attr_type, times, values, min_val=None, max_val=None, extra=None):
    value = {'relative': 0}
    if min_val is not None:
        value['minValueRange'] = min_val
    if max_val is not None:
        value['maxValueRange'] = max_val
    if extra:
        value.update(extra)

    return {
        'type': attr_type,
        'value': value,
        'keyframes': [{'time': t, 'value': v} for t, v in zip(times, values)],
        'intimeline': True,
    }


def _resolve_altitudes(sel, altitude_m, altitude_offset_m):
    """カメラ高度のリストを返す。

    altitude_mが指定されていれば、地形に関わらず常にその絶対高度(標高)で一定にする。
    未指定の場合は、各地点の標高にaltitude_offset_mを足した高度で地形に追従する。
    """
    if altitude_m is not None:
        return [altitude_m] * len(sel)
    return [p[2] + altitude_offset_m for p in sel]


def intro_tracking_outro_keyframes(points, altitude_m, altitude_offset_m, tilt_deg,
                                    max_keyframes, intro_sec, main_sec, outro_sec):
    """静止イントロ→追跡区間→静止アウトロの一連のキーフレームを、
    (time, lon, lat, alt, heading, tilt)の並列リストとして返す。

    イントロ/アウトロはそれぞれ、追跡区間の最初/最後のキーフレームと全く同じ値を
    時刻0.0/1.0にも置くだけで、カメラは止まったまま動かない(利用者が後で
    Earth Studio上に演出を手動で追加する前提の、単なる余白時間)。
    timeは全体の尺(intro_sec+main_sec+outro_sec)に対する割合(0.0-1.0)。

    .esp向けの正規化・rotationXYZブロック化と、CSV向けの行フォーマットの両方から
    共通で使う。
    """
    total_sec = intro_sec + main_sec + outro_sec

    idx = _select_indices(len(points), min(max_keyframes, len(points)))
    sel = [points[i] for i in idx]
    track_times_raw = _time_fractions(sel)

    ground_lons = [p[0] for p in sel]
    ground_lats = [p[1] for p in sel]
    ground_eles = [p[2] for p in sel]
    cam_alts = _resolve_altitudes(sel, altitude_m, altitude_offset_m)
    travel_headings = headings_from_coords(list(zip(ground_lons, ground_lats)))

    track_lons, track_lats, track_headings, track_tilts = [], [], [], []
    for lon, lat, ele, alt, heading in zip(ground_lons, ground_lats, ground_eles, cam_alts, travel_headings):
        distance = _backward_distance_for_view_angle(alt - ele, tilt_deg)
        cam_lon, cam_lat = _offset_point_backward(lon, lat, heading, distance)
        look_heading, look_tilt = _look_at_heading_and_tilt((cam_lon, cam_lat), alt, (lon, lat), ele)
        track_lons.append(cam_lon)
        track_lats.append(cam_lat)
        track_headings.append(look_heading)
        track_tilts.append(look_tilt)

    # _look_at_heading_and_tiltは各点ごとに独立して[0,360)へ丸めるため、隣接するキーフレーム間で
    # 0度と360度をまたぐと遠回りに回転してしまう。連続的な値になるよう補正する。
    track_headings = _unwrap_headings(track_headings, start=track_headings[0])

    intro_frac = intro_sec / total_sec
    outro_start_frac = 1.0 - outro_sec / total_sec
    main_span = outro_start_frac - intro_frac
    track_times = [intro_frac + tr * main_span for tr in track_times_raw]

    times = [0.0] + track_times + [1.0]
    lons = [track_lons[0]] + track_lons + [track_lons[-1]]
    lats = [track_lats[0]] + track_lats + [track_lats[-1]]
    alts = [cam_alts[0]] + cam_alts + [cam_alts[-1]]
    headings = [track_headings[0]] + track_headings + [track_headings[-1]]
    tilts = [track_tilts[0]] + track_tilts + [track_tilts[-1]]

    return times, lons, lats, alts, headings, tilts


def _normalized_lon_lat_blocks(prefix, lons, lats):
    """lon/lat属性ブロックのペアを返す(正規化式はkml_to_esp.pyのものを踏襲)。"""
    lon_min = min(lons)
    lat_min = min(lats)
    s_lon = 180 - _angle180_180(lon_min)
    s_lat = 90 - _angle180_180(lat_min)
    lon_vals = [(v - lon_min) / s_lon for v in lons]
    lat_vals = [(v - lat_min) / s_lat for v in lats]
    return lon_vals, lat_vals, lon_min, lat_min


def _build_position_and_rotation_attrs(points, altitude_m, altitude_offset_m, tilt_deg, max_keyframes,
                                        target_tracking=False):
    idx = _select_indices(len(points), min(max_keyframes, len(points)))
    sel = [points[i] for i in idx]
    times = _time_fractions(sel)

    ground_lons = [p[0] for p in sel]
    ground_lats = [p[1] for p in sel]
    ground_eles = [p[2] for p in sel]
    cam_alts = _resolve_altitudes(sel, altitude_m, altitude_offset_m)
    headings = headings_from_coords(list(zip(ground_lons, ground_lats)))

    if target_tracking:
        # カメラを進行方向の後方へオフセットし、地点(=対象)の真上から外す。
        # 実際に対象を狙う向きはEarth Studioの「ターゲット自動追尾」に計算させる。
        cam_lons, cam_lats = [], []
        for lon, lat, ele, cam_alt, heading in zip(ground_lons, ground_lats, ground_eles, cam_alts, headings):
            distance = _backward_distance_for_view_angle(cam_alt - ele, tilt_deg)
            olon, olat = _offset_point_backward(lon, lat, heading, distance)
            cam_lons.append(olon)
            cam_lats.append(olat)
    else:
        cam_lons, cam_lats = ground_lons, ground_lats

    lon_vals, lat_vals, lon_min, lat_min = _normalized_lon_lat_blocks('camera', cam_lons, cam_lats)
    alt_vals = [a * ALTITUDE_VALUE_PER_METRE for a in cam_alts]

    position_attrs = [
        _keyframe_block('longitude', times, lon_vals, min_val=lon_min),
        _keyframe_block('latitude', times, lat_vals, min_val=lat_min),
        _keyframe_block('altitude', times, alt_vals, extra={'logarithmic': False}),
    ]

    if target_tracking:
        # 手動のHeading/Tiltは無効のままにし、Earth Studio側の自動追尾に向きを任せる。
        rotation_attrs = [
            {'type': 'rotationX', 'value': {}},
            {'type': 'rotationY', 'value': {}},
            {'type': 'rotationZ', 'value': {}},
        ]

        poi_lon_vals, poi_lat_vals, poi_lon_min, poi_lat_min = _normalized_lon_lat_blocks(
            'poi', ground_lons, ground_lats)
        poi_alt_vals = [e * ALTITUDE_VALUE_PER_METRE for e in ground_eles]
        target_effect_attrs = [
            {'type': 'enabled', 'value': {'relative': 1}},
            {
                'type': 'poi',
                'attributes': [
                    _keyframe_block('longitudePOI', times, poi_lon_vals, min_val=poi_lon_min),
                    _keyframe_block('latitudePOI', times, poi_lat_vals, min_val=poi_lat_min),
                    _keyframe_block('altitudePOI', times, poi_alt_vals, extra={'logarithmic': False}),
                ],
            },
            {'type': 'influence', 'value': {'relative': 1}},
        ]
    else:
        rotation_attrs = [
            _heading_keyframe_block(times, headings),
            _keyframe_block('rotationY', [0.0, 1.0], [tilt_deg / 180, tilt_deg / 180]),
            {'type': 'rotationZ', 'value': {}},
        ]
        target_effect_attrs = None

    return position_attrs, rotation_attrs, target_effect_attrs


def _heading_keyframe_block(times, headings):
    heading_min = min(headings)
    heading_max = max(headings)
    heading_range = heading_max - heading_min
    if heading_range < 1e-9:
        # 方位が終始変化しない場合、0除算を避けるためのフォールバック。
        heading_vals = [0.5] * len(headings)
        heading_min -= 0.5
        heading_max += 0.5
    else:
        heading_vals = [(h - heading_min) / heading_range for h in headings]

    return _keyframe_block('rotationX', times, heading_vals, min_val=heading_min, max_val=heading_max)


def _build_intro_tracking_outro_attrs(points, altitude_m, altitude_offset_m, tilt_deg,
                                       max_keyframes, intro_sec, main_sec, outro_sec):
    """静止イントロ→追跡区間→静止アウトロのposition/rotation属性を返す。

    前後の静止区間と地続きにするため、追跡区間もEarth Studioの自動追尾(POI)には
    頼らず、区間全体のHeading/Tiltを幾何計算で求めて手動キーフレームとして焼き込む。
    """
    times, lons, lats, alts, headings, tilts = intro_tracking_outro_keyframes(
        points, altitude_m, altitude_offset_m, tilt_deg, max_keyframes,
        intro_sec, main_sec, outro_sec)

    lon_vals, lat_vals, lon_min, lat_min = _normalized_lon_lat_blocks('camera', lons, lats)
    alt_vals = [a * ALTITUDE_VALUE_PER_METRE for a in alts]

    position_attrs = [
        _keyframe_block('longitude', times, lon_vals, min_val=lon_min),
        _keyframe_block('latitude', times, lat_vals, min_val=lat_min),
        _keyframe_block('altitude', times, alt_vals, extra={'logarithmic': False}),
    ]

    tilt_vals = [t / 180 for t in tilts]
    rotation_attrs = [
        _heading_keyframe_block(times, headings),
        _keyframe_block('rotationY', times, tilt_vals),
        {'type': 'rotationZ', 'value': {}},
    ]

    return position_attrs, rotation_attrs


def _scene(duration_frames, position_attrs, rotation_attrs, target_effect_attrs=None):
    return {
        'world': {'kmls': []},
        'animationModel': {
            'roving': False,
            'logarithmic': False,
            'groupedPosition': True,
        },
        'duration': duration_frames,
        'attributes': [
            {
                'type': 'cameraGroup',
                'inTimeline': True,
                'attributes': [
                    {
                        'type': 'cameraPositionGroup',
                        'inTimeline': True,
                        'attributes': position_attrs,
                    },
                    {
                        'type': 'cameraTargetEffect',
                        'attributes': target_effect_attrs if target_effect_attrs is not None else [
                            {'type': 'enabled', 'value': {}},
                            {
                                'type': 'poi',
                                'attributes': [
                                    {'type': 'longitudePOI', 'value': {}},
                                    {'type': 'latitudePOI', 'value': {}},
                                    {'type': 'altitudePOI', 'value': {'logarithmic': False}},
                                ],
                            },
                            {'type': 'influence', 'value': {}},
                        ],
                    },
                    {
                        'type': 'cameraRotationGroup',
                        'inTimeline': True,
                        'attributes': rotation_attrs,
                    },
                    {
                        'type': 'cameraLensGroup',
                        'attributes': [
                            {'type': 'fov', 'value': {}},
                            {'type': 'exposure', 'value': {}},
                            {'type': 'aperture', 'value': {}},
                            {'type': 'minFocusLength', 'value': {}},
                        ],
                    },
                ],
            },
            {
                'type': 'environmentGroup',
                'attributes': [
                    {
                        'type': 'sunGroup',
                        'attributes': [
                            {'type': 'sunVisibility', 'value': {}},
                            {'type': 'worldTime', 'value': {'relative': 0.5}},
                        ],
                    },
                    {
                        'type': 'cloudGroup',
                        'attributes': [
                            {'type': 'cloudVisibility', 'value': {}},
                            {'type': 'cloudopacity', 'value': {}},
                            {'type': 'cloudheight', 'value': {}},
                            {'type': 'clouddate', 'value': {'relative': 0.9545454545454546}},
                        ],
                    },
                    {
                        'type': 'starsPlanetsGroup',
                        'attributes': [{'type': 'starsEnabled', 'value': {}}],
                    },
                    {
                        'type': 'seawaterGroup',
                        'attributes': [
                            {'type': 'seawater', 'value': {}},
                            {'type': 'influence', 'value': {'relative': 1}},
                        ],
                    },
                    {'type': 'buildingsEnabled', 'value': {}},
                ],
            },
        ],
        'cameraExport': {'logarithmic': False, 'modelVersion': 2},
    }


def gpx_to_earth_studio_project(gpx_file, duration_sec=60.0, fps=30, altitude_m=None, altitude_offset_m=200.0,
                                 tilt_deg=60.0, max_keyframes=200, smooth_window=5, target_tracking=False,
                                 intro_sec=0.0, outro_sec=0.0, width=1920, height=1080):
    points = _smooth_points(_load_points(gpx_file), smooth_window)

    if intro_sec > 0 or outro_sec > 0:
        duration_frames = round((intro_sec + duration_sec + outro_sec) * fps)
        position_attrs, rotation_attrs = _build_intro_tracking_outro_attrs(
            points, altitude_m, altitude_offset_m, tilt_deg, max_keyframes,
            intro_sec, duration_sec, outro_sec)
        target_effect_attrs = None
    else:
        duration_frames = round(duration_sec * fps)
        position_attrs, rotation_attrs, target_effect_attrs = _build_position_and_rotation_attrs(
            points, altitude_m, altitude_offset_m, tilt_deg, max_keyframes, target_tracking=target_tracking)

    name = os.path.splitext(os.path.basename(gpx_file))[0]

    return {
        'modelVersion': 17,
        'settings': {
            'name': name,
            'frameRate': fps,
            'dimensions': {'width': width, 'height': height},
            'duration': duration_frames,
            'timeFormat': 'frames',
        },
        'scenes': [_scene(duration_frames, position_attrs, rotation_attrs, target_effect_attrs)],
        'playbackManager': {'range': {'start': 0, 'end': duration_frames}},
    }


def save_earth_studio_esp(gpx_file, outfile, **kwargs):
    project = gpx_to_earth_studio_project(gpx_file, **kwargs)
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(project, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 手入力用キーフレーム表(CSV)生成
# ---------------------------------------------------------------------------

CSV_HEADER = ['Frame', 'Latitude', 'Longitude', 'Altitude(m)', 'Heading(deg)', 'Tilt(deg)', 'Roll(deg)']


def gpx_to_camera_keyframe_rows(gpx_file, duration_sec=60.0, fps=30, altitude_m=None, altitude_offset_m=200.0,
                                 tilt_deg=60.0, n_keyframes=15, smooth_window=5, target_tracking=False,
                                 intro_sec=0.0, outro_sec=0.0):
    points = _smooth_points(_load_points(gpx_file), smooth_window)

    if intro_sec > 0 or outro_sec > 0:
        duration_frames = round((intro_sec + duration_sec + outro_sec) * fps)
        times, lons, lats, alts, headings, tilts = intro_tracking_outro_keyframes(
            points, altitude_m, altitude_offset_m, tilt_deg, n_keyframes,
            intro_sec, duration_sec, outro_sec)

        rows = []
        for frac, lon, lat, alt, heading, tilt in zip(times, lons, lats, alts, headings, tilts):
            frame = round(frac * (duration_frames - 1))
            # Headingは0/360度をまたぐ回り込みを避けるため連続値のまま出力する(%360で丸めない)。
            # Earth Studioへ手入力する際は表示された値をそのまま入力すること。
            rows.append([frame, round(lat, 6), round(lon, 6), round(alt, 1),
                         round(heading, 1), round(tilt, 1), 0])
        return rows

    duration_frames = round(duration_sec * fps)

    idx = _select_indices(len(points), min(n_keyframes, len(points)))
    sel = [points[i] for i in idx]
    times = _time_fractions(sel)
    ground_coords = [(p[0], p[1]) for p in sel]
    headings = headings_from_coords(ground_coords)
    alts = _resolve_altitudes(sel, altitude_m, altitude_offset_m)

    if target_tracking:
        # Earth Studio上の自動追尾が使えない手入力向けに、対象(地点)を正確に
        # 画面中心へ捉える向きを幾何計算で求める(カメラは進行方向の後方へオフセット)。
        cam_coords = []
        out_headings = []
        out_tilts = []
        for (lon, lat, ele, _dt), heading, alt in zip(sel, headings, alts):
            distance = _backward_distance_for_view_angle(alt - ele, tilt_deg)
            cam_lon, cam_lat = _offset_point_backward(lon, lat, heading, distance)
            look_heading, look_tilt = _look_at_heading_and_tilt((cam_lon, cam_lat), alt, (lon, lat), ele)
            cam_coords.append((cam_lon, cam_lat))
            out_headings.append(look_heading)
            out_tilts.append(look_tilt)
        # _look_at_heading_and_tiltは点ごとに独立して[0,360)へ丸めるため、隣接するキーフレーム間で
        # 0度と360度をまたぐと遠回りに回転してしまう。連続的な値になるよう補正する。
        out_headings = _unwrap_headings(out_headings, start=out_headings[0]) if out_headings else []
    else:
        cam_coords = [(lon, lat) for lon, lat, _ele, _dt in sel]
        out_headings = headings
        out_tilts = [tilt_deg] * len(sel)

    rows = []
    for (cam_lon, cam_lat), frac, alt, out_heading, out_tilt in zip(
            cam_coords, times, alts, out_headings, out_tilts):
        frame = round(frac * (duration_frames - 1))
        # Headingは0/360度をまたぐ回り込みを避けるため連続値のまま出力する(%360で丸めない)。
        rows.append([frame, round(cam_lat, 6), round(cam_lon, 6), round(alt, 1),
                     round(out_heading, 1), round(out_tilt, 1), 0])

    return rows


def save_camera_keyframe_csv(gpx_file, outfile, **kwargs):
    rows = gpx_to_camera_keyframe_rows(gpx_file, **kwargs)
    with open(outfile, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv):
    parser = argparse.ArgumentParser(
        description='GPXのトラックからGoogle Earth Studio用のカメラトラックデータ(.esp / キーフレーム表CSV)を生成する')
    parser.add_argument('gpx', help='入力GPXファイル')
    parser.add_argument('--esp', help='出力.espファイル(既定: 入力と同名の.esp)')
    parser.add_argument('--csv', help='出力キーフレーム表CSVファイル(既定: 入力と同名の_camera_keyframes.csv)')
    parser.add_argument('--no-esp', action='store_true', help='.espファイルを生成しない')
    parser.add_argument('--no-csv', action='store_true', help='キーフレーム表CSVを生成しない')
    parser.add_argument('--duration', type=float, default=60.0, help='アニメーションの尺(秒、既定60)')
    parser.add_argument('--fps', type=int, default=30, help='フレームレート(既定30)')
    altitude_group = parser.add_mutually_exclusive_group()
    altitude_group.add_argument('--altitude', type=float, default=None,
                                 help='カメラの絶対高度(標高m)。地形に関わらずこの高度で一定にする')
    altitude_group.add_argument('--altitude-offset', type=float, default=200.0,
                                 help='トラック地点の標高に加えるカメラの高度オフセット(m、既定200)。地形に追従する')
    parser.add_argument('--tilt', type=float, default=60.0,
                         help='カメラの傾き(度、0=真下, 90=水平、既定60)。'
                              '--target-tracking指定時はオフセット距離の計算にのみ使う目安角度')
    parser.add_argument('--target-tracking', action='store_true',
                         help='カメラを地点の真上から進行方向後方へオフセットし、'
                              'Earth Studioの「ターゲット自動追尾」で常にその地点を狙わせる'
                              '(対象が画面中心に来る。中心からずらすにはEarth Studio上で手動調整が必要)')
    parser.add_argument('--max-keyframes', type=int, default=200,
                         help='.espに含める最大キーフレーム数(既定200)')
    parser.add_argument('--csv-keyframes', type=int, default=15,
                         help='CSVに出力するキーフレーム数(既定15、手入力しやすい少数に間引く)')
    parser.add_argument('--smooth-window', type=int, default=5,
                         help='GPSノイズによるカメラの向きのぶれを抑える移動平均の点数(既定5、1で無効)')
    parser.add_argument('--intro-sec', type=float, default=0.0,
                         help='冒頭に追加する、カメラが動かない静止区間の秒数(既定0=追加しない。'
                              '演出は手動でEarth Studio上に追加する前提の余白)')
    parser.add_argument('--outro-sec', type=float, default=0.0,
                         help='末尾に追加する、カメラが動かない静止区間の秒数(既定0=追加しない。'
                              '演出は手動でEarth Studio上に追加する前提の余白)')
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    base = os.path.splitext(args.gpx)[0]

    kwargs = dict(duration_sec=args.duration, fps=args.fps, altitude_m=args.altitude,
                  altitude_offset_m=args.altitude_offset, tilt_deg=args.tilt, smooth_window=args.smooth_window,
                  target_tracking=args.target_tracking, intro_sec=args.intro_sec, outro_sec=args.outro_sec)

    if not args.no_esp:
        esp_out = args.esp or base + '.esp'
        save_earth_studio_esp(args.gpx, esp_out, max_keyframes=args.max_keyframes, **kwargs)
        print('{} -> {}'.format(args.gpx, esp_out))

    if not args.no_csv:
        csv_out = args.csv or base + '_camera_keyframes.csv'
        save_camera_keyframe_csv(args.gpx, csv_out, n_keyframes=args.csv_keyframes, **kwargs)
        print('{} -> {}'.format(args.gpx, csv_out))


if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
