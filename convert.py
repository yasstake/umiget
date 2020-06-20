import json

'''
https://wiki.openstreetmap.org/wiki/Seamarks/Seamark_Objects
'''

'''
https://wiki.openstreetmap.org/wiki/Tag:seamark:type%3Dharbour
マリーナ
seamark:type=harbour
seamark:category=marina
name:en  英語名
name     ローカル名

漁港
seamark:category=fishing


'''


SEAMARK_NS = 'seamark:'
PROPERTIES = 'properties'

SEAMARK_MARINA = ''


def load(file):
    with open(file, 'r') as f:
        j = json.load(f)

    return j

def process(file, filter, outfile):
    j = load(file)

    with open(outfile, 'a') as f:
        for line in j['features']:
            p = filter(line)
            f.write(json.dumps(p, ensure_ascii=False))
            f.write('\n')


def basic_property(line, p=None):
    if not p:
        p = {}

    p['type'] = line['type']
    p['geometry'] = line['geometry']
    p[PROPERTIES] = {}

    return p


def marina_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'harbour'
    p[PROPERTIES][SEAMARK_NS + 'category'] = 'marina'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['マリーナの名称']

    return p


def fisher_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'harbour'
    p[PROPERTIES][SEAMARK_NS + 'category'] = 'fishing'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['漁港名']

    return p


def fisher_fixnet_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'marine_farm'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['ラベル追加文字']

    return p

def float_lights_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'buoy'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['名称']
    p[PROPERTIES]['light_id'] = line_p['航路標識番号']

    return p


def light_house_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'light_minor'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['名称']
    p[PROPERTIES]['light_id'] = line_p['航路標識番号']

    return p

def pillar_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'light_minor'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['名称']
    p[PROPERTIES]['light_id'] = line_p['航路標識番号']

    return p

def other_lights_property(line, p=None):
    p = basic_property(line, p)

    line_p = line[PROPERTIES]

    p[PROPERTIES][SEAMARK_NS + 'type'] = 'light'
    p[PROPERTIES][SEAMARK_NS + 'name'] = line_p['名称']
    p[PROPERTIES]['light_id'] = line_p['航路標識番号']

    return p


if __name__ == '__main__':
    process('./data/marina.json', marina_property, 'out.json')
    process('./data/fisher_fix_net.json', fisher_fixnet_property, 'out.json')
    process('./data/float_lights.json', float_lights_property, 'out.json')
    process('./data/light_house.json', light_house_property, 'out.json')
    process('./data/other_lights.json', other_lights_property, 'out.json')



