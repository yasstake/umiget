import unittest
import json
from umiget import Umi

INVENTRY_JSON='''
{"currentVersion":10.6,"id":15,"name":"灯台","type":"Feature Layer","description":"","geometryType":"esriGeometryPoint","sourceSpatialReference":{"wkid":4326,"latestWkid":4326},"copyrightText":"","parentLayer":{"id":14,"name":"灯"},"subLayers":[],"minScale":0,"maxScale":0,"drawingInfo":{"renderer":{"type":"simple","symbol":{"type":"esriPMS","url":"74d8b54da02b5dd4e5d7d86cb0bd2f53","imageData":"iVBORw0KGgoAAAANSUhEUgAAACMAAAAYCAYAAABwZEQ3AAAAAXNSR0IB2cksfwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAlNJREFUSInNlr1u4kAURk+kSFOw1aTBfoNIEUoEeYOkM5tUG/pI8AqRKOIg3EWiDkpDRwtOl0cIVn4eIFUUuqlobpUt7IDX2IAR2nBdWJ7xeM7cud833mWLYjfvAK112RgTbAOMbYwZAQ2g+9MwTnSvswUw9ehe3jQI5IOxExAbz04eGCfx/HMwSilbROJNG9+qJMxd1osiUk1p9pVSgYhYyQ6tdTevBcRhbKAKzH14QTgiktw+gMAYYwNrw3xGQHfMVLNOBFrrxjrGmFYzjSjFPoks1Wo1Wq0WvV4Pz/PmBiqlbkTENcbk5ciEIVqVDfjEVNTv9+l0OpRKpeSQMdAQEX8tikUwsagCI2LKsay5khoTZnAIPACf6xTvKjBJo0sLi/CscgGnSRPPePUIMgB8rXWwCtwymDSlZMV0W8eM+eDDeufdeePN8YwHML7n3r/Ul90ds5MKthAmxeggdN2k2tyovXqrbl1PvOsnnvgTXVdcMWFiFSnWMdS/+OKFl+CIo9+EKl4Ok/CQALghTHtSbdb3f46IuEBwzPHwkUdOOOFXdMXjkMPygMHojDN7FZgqs3p5IKyLT/hHbVNPMsaUmZmcr7WunJpTv0nTatNOnWCffYvYGZcJo5Qqi8jUOzJei3uSS+zg/Ab28Pxzzp0KlQXrDiMTplAo+CISLPOOWJbSzi6A6kAN3IpUrpMdzzwTKW0xTDRJHq/IhG5L261RC/bYGxYpMmHCK6/jCy4CzGyO3D/k68YBB77WumKMKSul7EKh4MdB/isMzLItIqRYBn8Bqf8BXNE3AI8AAAAASUVORK5CYII=","contentType":"image/png","width":26,"height":18,"angle":0,"xoffset":56,"yoffset":0},"label":"","description":""},"transparency":0,"labelingInfo":[{"labelPlacement":"esriServerPointLabelPlacementAboveRight","where":null,"labelExpression":"[名称]","useCodedValues":true,"symbol":{"type":"esriTS","color":[0,0,0,255],"backgroundColor":null,"borderLineColor":null,"borderLineSize":null,"verticalAlignment":"bottom","horizontalAlignment":"center","rightToLeft":false,"angle":0,"xoffset":0,"yoffset":0,"kerning":true,"haloColor":[255,255,255,255],"haloSize":1,"font":{"family":"MS UI Gothic","size":8,"style":"normal","weight":"normal","decoration":"none"}},"minScale":250000,"maxScale":0}]},"defaultVisibility":false,"extent":{"xmin":122.93441666700005,"ymin":20.40138888900003,"xmax":147.9173333330001,"ymax":45.52161111100003,"spatialReference":{"wkid":4326,"latestWkid":4326}},"hasAttachments":false,"htmlPopupType":"esriServerHTMLPopupTypeAsHTMLText","displayField":"名称","typeIdField":null,"subtypeFieldName":null,"fields":[{"name":"OBJECTID","type":"esriFieldTypeOID","alias":"OBJECTID","domain":null},{"name":"Shape","type":"esriFieldTypeGeometry","alias":"Shape","domain":null},{"name":"航路標識番号","type":"esriFieldTypeDouble","alias":"航路標識番号","domain":null},{"name":"灯フラグ","type":"esriFieldTypeDouble","alias":"灯フラグ","domain":null},{"name":"名称","type":"esriFieldTypeString","alias":"名称","length":255,"domain":null},{"name":"読み","type":"esriFieldTypeString","alias":"読み","length":255,"domain":null},{"name":"データ年度","type":"esriFieldTypeString","alias":"データ年度","length":255,"domain":null},{"name":"調査年度","type":"esriFieldTypeString","alias":"調査年度","length":255,"domain":null},{"name":"作成機関","type":"esriFieldTypeString","alias":"作成機関","length":255,"domain":null},{"name":"出典","type":"esriFieldTypeString","alias":"出典","length":255,"domain":null},{"name":"F9","type":"esriFieldTypeString","alias":"F9","length":255,"domain":null},{"name":"緯度","type":"esriFieldTypeDouble","alias":"緯度","domain":null},{"name":"F11","type":"esriFieldTypeString","alias":"F11","length":255,"domain":null},{"name":"経度","type":"esriFieldTypeDouble","alias":"経度","domain":null},{"name":"標識種別","type":"esriFieldTypeString","alias":"標識種別","length":255,"domain":null}],"indexes":[{"name":"FDO_OBJECTID","fields":"OBJECTID","isAscending":true,"isUnique":true,"description":""},{"name":"FDO_Shape","fields":"Shape","isAscending":true,"isUnique":false,"description":""}],"subtypes":[],"relationships":[],"canModifyLayer":true,"canScaleSymbols":false,"hasLabels":true,"capabilities":"Map,Query,Data","maxRecordCount":1000,"supportsStatistics":true,"supportsAdvancedQueries":true,"supportedQueryFormats":"JSON, AMF, geoJSON","ownershipBasedAccessControlForFeatures":{"allowOthersToQuery":true},"useStandardizedQueries":true,"advancedQueryCapabilities":{"useStandardizedQueries":true,"supportsStatistics":true,"supportsOrderBy":true,"supportsDistinct":true,"supportsPagination":true,"supportsTrueCurve":true,"supportsReturningQueryExtent":true,"supportsQueryWithDistance":true,"supportsSqlExpression":true},"supportsDatumTransformation":true}
'''

class MyTestCase(unittest.TestCase):
    def test_umi_login(self):
        umi = Umi()
        umi.login()

        print(umi.session)
        print(umi.token)

    def test_url_encoding(self):
        umi = Umi()
        umi = Umi()
        umi.login()

        print(umi.make_params({'a': 'b', 'c':'d'}))

    def test_parse_invetry(self):
        umi = Umi()
        print(umi.parse_inventory(INVENTRY_JSON))





    def test_get_lights(self):
        umi = Umi()
        umi = Umi()
        umi.login()

        print(umi.get_light_house())






if __name__ == '__main__':
    unittest.main()
