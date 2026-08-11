

umiget:
	python3 umiget.py

umiget-refresh:
	python3 umiget.py --refresh


convert: land.tokyo.json
	python3 convert.py
	- rm seamap.mbtiles
	tippecanoe -rg --force -o seamap.mbtiles \
	           -L fisher_net:fisher_net.out.json \
	           -L float:float.out.json -L light_house:light_house.out.json \
	           -L light:light.out.json -L land:land.tokyo.json \
	           --maximum-zoom=14 --minimum-zoom=7

kml:
	python3 convert.py --kml

download:
	- rm -rf ./land
	- mkdir  ./land
	wget https://osmdata.openstreetmap.de/download/land-polygons-split-4326.zip


download-japan:
	wget http://download.geofabrik.de/asia/japan-latest.osm.pbf


unzip:
	unzip -oj land-polygons-split-4326.zip -d ./land

geojson:
	ogr2ogr -lco "ENCODING=UTF-8" -f geoJSON land.geojson ./land/land_polygons.shp


land.tokyo.json:
	python3 util/bbox.py > land.tokyo.json

landtiles:
	tippecanoe -rg -z11 -z7 -C './filter/limit-tiles-to-bbox 138 35 141 32 $*' --force -o land.mbtiles land.geojson


install_pip:
	python3 -m pip install requests

install_mac:
	brew install gdal
	brew install tippercanoe


