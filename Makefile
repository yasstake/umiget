
all:


umiget:
	python umiget.py


convert:
	python convert.py
	- rm seamap.mbtiles
	tippecanoe --force -o seamap.mbtiles -L marina:marina.out.json -L fisher_net:fisher_net.out.json -L float:float.out.json -L light_house:light_house.out.json -L light:light.out.json --maximum-zoom=15 --minimum-zoom=7


download:
	- rm -rf ./land
	- mkdir  ./land
	wget https://osmdata.openstreetmap.de/download/land-polygons-split-4326.zip

unzip:
	unzip -oj land-polygons-split-4326.zip -d ./land

geojson:
	ogr2ogr -lco "ENCODING=UTF-8" -f geoJSON land.geojson ./land/land_polygons.shp

landtiles:
	tippecanoe --force -o land.mbtiles land.geojson


install_pip:
	python -m pip install requests-html
	python -m pip install arcgis2geojson

install_mac:
	brew install gdal
	brew install tippercanoe



