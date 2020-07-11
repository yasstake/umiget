import sys
import json

x1 = 125
y1 = 25
x2 = 150
y2 = 40

def load(file):
    with open(file, 'r') as f:
        j = json.load(f)

    return j

def process(file):
    j = load(file)

    for line in j['features']:
        coordinates = line['geometry']['coordinates']
        point = coordinates[0][0]
        x = point[0]
        y = point[1]

        if (x1 < x) and (x < x2) and (y1 < y) and (y < y2):
            nl = json.dumps(line, ensure_ascii=False) + '\n'
            print(nl, end='')

process('land.geojson')
