import argparse
import os
import sys

import gpx_overlay_kml
import gpx_to_earth_studio
import gpx_to_track_kml

'''
GPXの航跡1本を渡すと、これまでの一連の作業で決めた仕様に沿って一括で
3種類の成果物を作る。

1. トラックのKML変換 (gpx_to_track_kml.py)
   軌跡を黄緑色のラインで表示し、始点/終点にSTART/GOALのPlacemarkを立てる。

2. Google Earth Studioのカメラトラックデータ (gpx_to_earth_studio.py)
   .esp(実験的なプロジェクトファイル)と、手入力用キーフレーム表CSV。
   本セッションでのやり取りで決まった既定値を踏襲する:
   追跡区間は標高1500m一定・カメラ角度(Tilt)80度・キーフレーム10個・
   GPSノイズを抑える移動平均あり。冒頭5秒は日本全土、末尾5秒はトラック全体を
   真上・北が上で見渡すカットを追加する(この場合、向きはEarth Studioの
   自動追尾ではなく手動キーフレームとして焼き込まれる。詳細はgpx_to_earth_studio.py参照)。

3. 海しる(MSIL)データのオーバーレイ (gpx_overlay_kml.py)
   GPXのバウンディングボックスを10km拡大した範囲でdata/*.jsonの全データセットを
   クリップし、1つのKMLファイルにまとめる。
'''

# gpx_to_earth_studio.py の既定値(このセッションでのやり取りで決まったもの)
EARTH_STUDIO_DEFAULTS = dict(
    altitude_m=1500.0,
    tilt_deg=80.0,
    max_keyframes=10,
    smooth_window=5,
    target_tracking=False,
    intro_sec=5.0,
    outro_sec=5.0,
)
CSV_KEYFRAMES_DEFAULT = 10

OVERLAY_MARGIN_KM_DEFAULT = 10.0


def run_pipeline(gpx_file, out_dir=None, data_dir='./data',
                  earth_studio_kwargs=None, csv_keyframes=CSV_KEYFRAMES_DEFAULT,
                  overlay_margin_km=OVERLAY_MARGIN_KM_DEFAULT, regenerate_overlay_sources=True):
    base_name = os.path.splitext(os.path.basename(gpx_file))[0]
    out_dir = out_dir or os.path.dirname(gpx_file) or '.'
    base = os.path.join(out_dir, base_name)

    es_kwargs = dict(EARTH_STUDIO_DEFAULTS)
    if earth_studio_kwargs:
        es_kwargs.update(earth_studio_kwargs)

    track_kml = base + '.kml'
    esp_file = base + '.esp'
    csv_file = base + '_camera_keyframes.csv'
    overlay_kml = base + '_overlay.kml'

    gpx_to_track_kml.save_track_kml(gpx_file, track_kml)

    gpx_to_earth_studio.save_earth_studio_esp(gpx_file, esp_file, **es_kwargs)
    gpx_to_earth_studio.save_camera_keyframe_csv(
        gpx_file, csv_file, n_keyframes=csv_keyframes,
        **{k: v for k, v in es_kwargs.items() if k != 'max_keyframes'})

    kept, total, bbox = gpx_overlay_kml.save_merged_overlay(
        gpx_file, overlay_kml, margin_km=overlay_margin_km, data_dir=data_dir,
        regenerate_sources=regenerate_overlay_sources)

    return {
        'track_kml': track_kml,
        'esp_file': esp_file,
        'csv_file': csv_file,
        'overlay_kml': overlay_kml,
        'overlay_kept': kept,
        'overlay_total': total,
        'overlay_bbox': bbox,
    }


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        description='GPXの航跡から、トラックKML・Earth Studioカメラデータ・海しるオーバーレイKMLを一括生成する')
    parser.add_argument('gpx', help='入力GPXファイル')
    parser.add_argument('--out-dir', help='出力先ディレクトリ(既定: GPXファイルと同じディレクトリ)')
    parser.add_argument('--data-dir', default='./data', help='海しるデータ(*.json/*.kml)のディレクトリ(既定./data)')
    parser.add_argument('--overlay-margin-km', type=float, default=OVERLAY_MARGIN_KM_DEFAULT,
                         help='オーバーレイのバウンディングボックス拡大距離(km、既定10)')
    parser.add_argument('--no-regenerate-overlay-sources', action='store_true',
                         help='data/*.jsonからのKML再生成を省略し、既存の*.kmlをそのまま使う')
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)

    result = run_pipeline(
        args.gpx, out_dir=args.out_dir, data_dir=args.data_dir,
        overlay_margin_km=args.overlay_margin_km,
        regenerate_overlay_sources=not args.no_regenerate_overlay_sources)

    print('トラックKML       -> {}'.format(result['track_kml']))
    print('Earth Studio(.esp) -> {}'.format(result['esp_file']))
    print('キーフレーム表CSV  -> {}'.format(result['csv_file']))
    print('オーバーレイKML    -> {} ({}/{} 件、bbox={})'.format(
        result['overlay_kml'], result['overlay_kept'], result['overlay_total'], result['overlay_bbox']))


if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
