# umiget

[海しる(海洋状況表示システム/MSIL)](https://www.msil.go.jp/map/ja/) が公開している
公式API (`api.msil.go.jp`) から、灯台・漁港・航路・漁業権などの海事関連データを取得し、
GeoJSON・OSM seamarkタグ付きGeoJSON・Google Earth用KMLに変換するツールです。

## 必要環境

- Python 3.9 以上
- [requests](https://pypi.org/project/requests/)
- [shapely](https://pypi.org/project/shapely/)(`kml_clip.py` のPolygonクリッピングで使用)

```
pip install requests shapely
```

(または `make install_pip`)

## APIキーについて

データ取得には海しるAPIのサブスクリプションキーが必要です。

- `umiget.py` には [https://portal.msil.go.jp/howtouse](https://portal.msil.go.jp/howtouse)
  に掲載されている**試用キー**が既定値として組み込まれています。試用キーは
  「利用者への事前の通知なく停止または変更されることがある」ため、継続的に
  利用する場合は下記から本登録キーを申請し、環境変数で指定してください。

  ```
  export MSIL_API_KEY="取得した本登録キー"
  ```

- 本登録キーの申請は [https://portal.msil.go.jp](https://portal.msil.go.jp) の
  問い合わせフォームから行います(氏名・所属・メールアドレス・利用目的などが必要)。

## データ取得: umiget.py

```
python umiget.py
```

`data/` ディレクトリ以下に、各データセットのGeoJSONファイル(`<データ名>.json`)が
保存されます。既定では以下のデータセットを取得します。

| データ名 | 内容 |
|---|---|
| `light_house` | 灯台 |
| `float_lights` | 灯浮標 |
| `pillar_lights` | 灯標 |
| `other_lights` | 灯(その他) |
| `fisher` | 漁港 |
| `fisher_fix_net` | 定置漁業権 |
| `fisher_common_net` | 共同漁業権 |
| `fisher_demarcated_net` | 区画漁業権 |
| `traffic_route_major` | 海交法航路 |
| `traffic_route_minor` | 港則法航路 |

以下は `__main__` 内でコメントアウトされていますが、`Umi.save_info(...)` で
個別に呼び出せば取得できます。

| データ名 | 内容 |
|---|---|
| `obstacle` / `obstacle_area` | 海底障害物(点/面) |
| `wrected_ship_point` / `wrected_ship_area` | 沈船(点/面) |
| `notices_to_mariners` / `notices_to_mariners_en` | 水路通報(和文/英文) |
| `navigational_warnings` / `navigational_warnings_en` | 航行警報(和文/英文) |

Pythonから個別のデータセットだけ取得したい場合:

```python
from umiget import Umi

umi = Umi()
geojson = umi.get_light_house()
umi.logout()
```

### 制限事項

- **マリーナ・海水浴場・潮汐観測所**は、海しるAPIの公開カタログ
  ([https://portal.msil.go.jp/msil-api-list](https://portal.msil.go.jp/msil-api-list))
  に現時点で掲載されていないため取得できません。
- APIの応答は1回最大1000レコードで、超過分は `resultOffset` によるページネーションで
  自動的に追加取得されます。
- サーバーへの過度なアクセスを避けるため、リクエスト間隔は約1秒に制限しています
  (`Umi.REQUEST_WAIT`)。データセットが多い・レコード数が多いほど取得に時間が
  かかります。

## データの変換: convert.py

取得したGeoJSON (`data/*.json`) を変換します。用途に応じて2つのモードがあります。

### 1. OSM seamarkタグ付きGeoJSONへの変換(既定動作)

```
python convert.py
```

[OpenStreetMap Seamarks](https://wiki.openstreetmap.org/wiki/Seamarks/Seamark_Objects)
のタグ体系(`seamark:type` 等)を付与した改行区切りGeoJSON(`*.out.json`)を
カレントディレクトリに出力します。`Makefile` の `convert` ターゲットでは、
これをさらに [tippecanoe](https://github.com/mapbox/tippecanoe) でベクトルタイル
(`seamap.mbtiles`)にまとめます。

### 2. Google Earth用KMLへの変換

```
python convert.py --kml
```

`data/` 以下の全ての `*.json` を、同名の `.kml` ファイルに変換します
(`make kml` でも同じことができます)。

- Point / MultiPoint / LineString / MultiLineString / Polygon(穴あき対応) /
  MultiPolygon に対応しています。
- 各地物の全プロパティは `ExtendedData` として埋め込まれるため、Google Earthで
  ピンをクリックすると元の属性がそのまま確認できます。
- 地物の名前(Placemark名)は `名称`・`漁港名`・`マリーナの名称`・`航路名`・
  `ラベル追加文字`・`港名`・`読み` の優先順で自動的に選ばれます。該当する
  フィールドが無いデータセットでは、名前なし(属性のみ)のPlacemarkになります。

生成された `.kml` ファイルは、Google Earthの「ファイル > 開く」からそのまま
読み込めます。

## 範囲を指定した加工: gpx_bbox.py / kml_clip.py

GPXファイルの範囲を調べたり、KMLファイルをその範囲で切り取ったりするための
単体スクリプトです。`gpx_bbox.py` は `convert.py` 同様、標準ライブラリのみで
動作します。`kml_clip.py` はPolygonのクリッピングに `shapely` を使用します。

### 1. GPXファイルのバウンディングボックス表示: gpx_bbox.py

```
python gpx_bbox.py track.gpx
```

`track.gpx` 内の `wpt`/`trkpt`/`rtept` すべての座標から範囲を求め、
`west south east north`(経度最小 緯度最小 経度最大 緯度最大)の順で
1行出力します。

- `--margin DEG`: 範囲の四辺に度単位の余白を追加します(既定 `0`)。
- `--json`: `{"west": ..., "south": ..., "east": ..., "north": ...}` 形式で出力します。

### 2. KMLファイルをバウンディングボックスで切り取る: kml_clip.py

```
python kml_clip.py input.kml output.kml west south east north
```

`west south east north` は `gpx_bbox.py` の出力をそのまま渡せるので、
「GPXの範囲でKMLを切り取る」という使い方がそのまま1行で書けます。

```
python kml_clip.py data/light_house.kml tokyo_bay.kml $(python gpx_bbox.py track.gpx --margin 0.1)
```

- Point は範囲内かどうかのみで採用/除外を判定します。
- LineString は範囲の矩形で実際に線分を切り詰めます(Liang-Barsky法)。
- Polygon は `shapely`(GEOS)で範囲の矩形との交差を計算します。非凸な
  Polygonが範囲の境界を複数回出入りして複数の孤立した破片に分割される場合は、
  それぞれ別のPolygonとして出力されます(KML上はMultiGeometryになります)。
  Polygonの穴(innerBoundaryIs)も交差計算に含まれます。
- 範囲と全く交差しないPlacemarkは出力から除外されます。

## 陸地データとの合成(Makefile)

`Makefile` には、[OpenStreetMap land polygons](https://osmdata.openstreetmap.de/)
をダウンロードして陸地データを用意し、`convert` で作成したデータと合成する
一連のターゲットも用意されています(`download` → `unzip` → `geojson` →
`land.tokyo.json` → `convert`)。tippecanoe・gdal が別途必要です
(`make install_mac` でmacOSにインストール可能)。

## テスト

ネットワークに接続しない高速なユニットテストが既定で実行されます。

```
python3 -m unittest umiget_test.UmiUnitTestCase
PYTHONPATH=. python3 -m unittest test.convert_test test.gpx_bbox_test test.kml_clip_test
```

実際に海しるAPIへ接続する結合テストは、既定ではスキップされます。動作確認したい
場合は環境変数を立てて実行してください(サーバーへの負荷を考慮し、必要な時だけ
実行することを推奨します)。

```
UMIGET_RUN_INTEGRATION=1 python3 -m unittest umiget_test
```

## 参考リンク

- [海しる(海洋状況表示システム)](https://www.msil.go.jp/map/ja/)
- [海しるAPI利用方法](https://portal.msil.go.jp/howtouse)
- [海しるAPI一覧](https://portal.msil.go.jp/msil-api-list)
