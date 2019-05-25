/**
 * @fileoverview メイン画面表示機能
 */

/**
 * @class MapWindow
 * @classdesc メイン子画面
 * : メイン画面の表示・各クラスの生成
 */

/**
 * @function globalVariables
 * @summary グローバル変数クラス
 * @desc グローバル変数を保有するクラス
 * @returns なし
 */
var globalVariables = function () {
};
// マップ更新中フラグ(true:更新中 false:更新完了)
globalVariables.mapInstanceUpdatingFlg = false;
// マップ更新中のレイヤーID格納配列
globalVariables.mapInstanceUpdatingLayers = [];
globalVariables.progressEventCnt = 0;
globalVariables.layerWidgetList = [];
globalVariables.effectiveBaseToken = null;
globalVariables.effectiveOtherToken = null;
globalVariables.effectiveBaseTime = null;
globalVariables.effectiveOtherTime = null;
globalVariables.esriMap = null;
globalVariables.INIT_JS_PATH_480 = '/arcgis_js_api/library/4.8';
globalVariables.INIT_JS_PATH_325 = '/arcgis_js_api/library/3.25/3.25';
globalVariables.webScene3D = null;
globalVariables.view3D = null;
globalVariables.coordinate = null;
globalVariables.location = null;
globalVariables.objOfMenu = null;
globalVariables.searchObj = null;
globalVariables.urlParamList = [];
globalVariables.realTimeTsunamiFlg = true;
globalVariables.daySetPanelViewCnt = 0;

(function () {
    var urlParams = decodeURIComponent(parent.location.search.substring(1));
    if (urlParams) {
        var param = urlParams.split('&');

        for (i = 0; i < param.length; i++) {
            var paramItem = param[i].split('=');
            globalVariables.urlParamList[paramItem[0]] = paramItem[1];
        }
    }
}());

// polarId 表示モード 1：通常表示、2：極域2D、3：極域3D
globalVariables.polarId = 1;
if (globalVariables.urlParamList.polarId !== undefined && globalVariables.urlParamList.polarId !== null) {
    globalVariables.polarId = parseInt(globalVariables.urlParamList.polarId);
}

if (3 === globalVariables.polarId) {
    globalVariables.initJs = globalVariables.INIT_JS_PATH_480;
    globalVariables.layerMainJs = 'ShowWindowFunc/ShowGISWindowFunc/ShowLayerFunc/LayerMain3D';
    dojoConfig.baseUrl = loadUrlParams.arcDomainUrl + globalVariables.INIT_JS_PATH_480 + '/dojo';
} else {
    globalVariables.initJs = globalVariables.INIT_JS_PATH_325;
    globalVariables.layerMainJs = 'ShowWindowFunc/ShowGISWindowFunc/ShowLayerFunc/LayerMain';
    dojoConfig.baseUrl = loadUrlParams.arcDomainUrl + globalVariables.INIT_JS_PATH_325 + '/dojo';
}

// 2画面表示時選択中の画面設定
globalVariables.isCurrentMapWindow = null;
(function () {
    var active = globalVariables.urlParamList.active;
    var getIframeId = window.frameElement.id;
    if (active !== undefined && active !== null) {
        // 共有からの復元の場合
        if (getIframeId === 'left') {
            if ('1' === active) {
                // 2画面左画面アクティブ
                globalVariables.isCurrentMapWindow = true;
            } else {
                // 2画面左画面非アクティブ
                globalVariables.isCurrentMapWindow = false;
            }
        } else if (getIframeId === 'right') {
            if ('2' === active) {
                // 2画面右画面アクティブ
                globalVariables.isCurrentMapWindow = true;
            } else {
                // 2画面右画面非アクティブ
                globalVariables.isCurrentMapWindow = false;
            }
        }
    } else {
        // 通常表示の場合
        if (getIframeId === 'left') {
            // 2画面左画面アクティブ
            globalVariables.isCurrentMapWindow = true;
        } else if (getIframeId === 'right') {
            // 2画面右画面非アクティブ
            globalVariables.isCurrentMapWindow = false;
        }
    }
}());

/**
 * @function getMap
 * @summary マップオブジェクト取得
 * @desc マップオブジェクトを親画面に提供する
 * @returns {Object} マップオブジェクト
 */
var getMap = function () {
    return window.globalVariables.esriMap;
};

/**
 * @function getSymbolMain
 * @summary シンボル制御オブジェクト取得
 * @desc シンボル制御オブジェクトを返却する
 * @returns {Object} シンボル制御オブジェクト
 */
var getSymbolMain = function () {
    if (this._clsSymbolMain) {
        return this._clsSymbolMain;
    } else {
        return null;
    }
};

/**
 * @function getObjOfMenu
 * @summary ヘッダメニュー機能オブジェクト取得
 * @desc ヘッダメニュー機能オブジェクトを返却する
 * @returns {Object} ヘッダメニュー機能オブジェクト
 */
var getObjOfMenu = function () {
    return window.globalVariables.objOfMenu;
};

window.globalVariables.allServiceLayerList = {};

/**
 * @function getPresentLocation
 * @summary 現在地取得オブジェクト取得
 * @desc 現在地取得オブジェクトを返却する
 * @returns {Object} 現在地取得機能オブジェクト
 */
var getPresentLocation = function () {
    return window.globalVariables.location;
};

/**
 * @function getAllServiceLayerList
 * @summary レイヤーリストオブジェクト取得
 * @desc レイヤーリストオブジェクトを連携する
 * @returns {Object} レイヤー情報取得結果
 */
var getAllServiceLayerList = function () {
    return window.globalVariables.allServiceLayerList;
};

/**
 * @function getServiceLayer
 * @summary サービス登録レイヤー情報オブジェクト取得
 * @desc サービス登録レイヤー情報オブジェクトを連携する
 * @param {String} serviceUrl サービスURL
 * @returns {Object} レイヤー情報取得結果
 */
var getServiceLayer = function (serviceUrl) {
    if (serviceUrl in window.globalVariables.allServiceLayerList) {
        return window.globalVariables.allServiceLayerList[serviceUrl];
    } else {
        return null;
    }
};

/**
 * @function setServiceLayer
 * @summary レイヤーリストオブジェクト設定
 * @desc レイヤーリストオブジェクトに情報を設定する
 * @param {String} serviceUrl サービスURL
 * @param {String} response レスポンス
 * @returns {Object} レイヤー情報取得結果
 */
var setServiceLayer = function (serviceUrl, response) {
    window.globalVariables.allServiceLayerList[serviceUrl] = response;
};

/**
 * @function getArcLayerInfo
 * @summary ArcGIS側で登録されているレイヤ情報取得
 * @desc ArcGIS側で登録されているレイヤ情報を取得する
 * @param {String} serviceUrl サービスURL
 * @param {String} arcgisLayerId サービス単位のレイヤID
 * @returns {Object} レイヤ情報
 */
var getArcLayerInfo = function (serviceUrl, arcgisLayerId) {

    // FeatureServerの場合は、arcgis_layer_idを取り除く
    if (serviceUrl.lastIndexOf('/FeatureServer/') !== -1) {
        var splitUrl = serviceUrl.split('/FeatureServer/');
        serviceUrl = splitUrl[0] + '/FeatureServer/';
    }

    // NULLチェック
    if (window.getServiceLayer(serviceUrl) !== null
        && window.getServiceLayer(serviceUrl).layers !== undefined
        && (window.getServiceLayer(serviceUrl).layers !== null)) {
        var getServiceData = window.getServiceLayer(serviceUrl).layers;
        var getTargetLayerInfo = getServiceData[arcgisLayerId];
        return getTargetLayerInfo;
    } else {
        // データが無ければnullを返す
        return null;
    }
};

/**
 * @function getVisibleArcLayerId
 * @summary ArcGIS側で登録されているレイヤ情報取得
 * @desc ArcGIS側で登録されているレイヤ情報を取得する
 * @param {String} url サービスURL
 * @param {Number} layerId レイヤーId
 * @returns {Object} 表示中のArcGisLayerId一覧(グループレイヤーの場合は末端のid)
 */
var getVisibleArcLayerId = function (url, layerId) {
    var idList = [];
    var targetLayer = null;

    // esriバージョンによって処理を分ける
    if (window.globalVariables.INIT_JS_PATH_480 === window.globalVariables.initJs) {
        // esri4.8
        targetLayer = window.getMap().findLayerById(layerId);
    } else {
        // esri3.25
        targetLayer = window.getMap().getLayer(layerId);
    }

    if ((undefined !== targetLayer.visibleLayers) && (null !== targetLayer.visibleLayers)) {

        var setVisibleArcId = function (idList, url, visibleLayers) {
            var visibleLayerLength = visibleLayers.length;
            for (var i = 0; i < visibleLayerLength; i++) {
                var arcLayerInfo = window.getArcLayerInfo(url, visibleLayers[i].id);
                if (arcLayerInfo.type !== 'Group Layer') {
                    // ArcgisIDを設定する
                    idList.push(arcLayerInfo.id);
                } else {
                    // ArcgisIDを再帰的に取得する(末端のidを取得するため)
                    setVisibleArcId(idList, url, arcLayerInfo.subLayers);
                }
            }
        };

        var targetLength = targetLayer.visibleLayers.length;
        for (var i = 0; i < targetLength; i++) {
            var arcLayerInfo = window.getArcLayerInfo(url, targetLayer.visibleLayers[i]);
            if (arcLayerInfo.type !== 'Group Layer') {
                idList.push(arcLayerInfo.id);
            } else {
                // 子レイヤーを探索する
                setVisibleArcId(idList, url, arcLayerInfo.subLayers);
            }
        }
    }
    return idList;
};

/**
 * @function getLegendArcLayerId
 * @summary ArcGIS側で登録されているレイヤ情報取得
 * @desc ArcGIS側で登録されているレイヤ情報を取得する
 * @param {String} url サービスURL
 * @param {Number} arcgisLayerId レイヤーId
 * @param {Number} targetId 検索対象のレイヤーId
 * @returns {Object} 表示中のレイヤーに紐づく凡例用のLegendレイヤーのArcGisLayerId
 */
var getLegendArcLayerId = function (url, arcgisLayerId, targetId) {
    var result = {
        legendId: null,
        findFlg: false
    };

    var getChildLegendArcLayerId = function (result, url, layers, targetId) {
        var layerLength = layers.length;
        for (var i = 0; i < layerLength; i++) {
            var arcLayerInfo = window.getArcLayerInfo(url, layers[i].id);
            if (arcLayerInfo.type !== 'Group Layer') {
                if (arcLayerInfo.name === 'Legend') {
                    // Legendレイヤーのidを設定
                    result.legendId = arcLayerInfo.id;
                }
                if (arcLayerInfo.id === targetId) {
                    // 発見フラグを更新
                    result.findFlg = true;
                }
            } else {
                // ArcgisIDを再帰的に取得する(末端のidを取得するため)
                getChildLegendArcLayerId(result, url, arcLayerInfo.subLayers, targetId);
                if ((result.legendId !== null) && (result.findFlg === true)) {
                    break;
                }
            }
        }
    };

    var arcLayerInfo = window.getArcLayerInfo(url, arcgisLayerId);
    if (arcLayerInfo.type === 'Group Layer') {
        // グループレイヤーの場合のみ凡例用のレイヤーが存在する
        getChildLegendArcLayerId(result, url, arcLayerInfo.subLayers, targetId);
    }

    return result.legendId;
};

/**
 * @function addCallBackOfMapLocationLink
 * @summary 地図中心位置通知用コールバック設定
 * @desc 親画面に地図の中心位置を通知するためのコールバックを設定する
 * @param {Object} listener コールバックメソッド
 * @returns なし
 */
var addCallBackOfMapLocationLink = function (listener) {
    locationLinkOfPrent = listener;
};

// MapParent.jsにて定義(mapCenterLink)
var locationLinkOfPrent = null;

/**
 * @function showAtThisLocation
 * @summary 地図中心位置設定
 * @desc 親画面から地図の中心位置を設定するためのメソッド
 * @param {Object} ext Extent
 * @returns なし
 */
var showAtThisLocation = function (ext) {

};  // オーバーライド

/**
 * @function resetOverView
 * @summary 外観図設定処理
 * @desc 親画面から外観図を設定するためのメソッド
 * @returns なし
 */
var resetOverView = function () {
    // オーバービュー
    var overViewObj = null;
}; // オーバーライド

/**
* @function changeActiveWindowCtlr
* @summary 地図画面アクティブ変更処理
* @desc 親画面から地図のアクティブ/非アクティブが切り替わった際に実施する処理を実装するメソッド
* @param {Object} ext Extent
* @returns なし
*/
var changeActiveWindowCtlr = function () {

};  // オーバーライド

/**
 * @function showAtThisLocation
 * @summary マップの中心位置を設定する
 * @desc 親画面からコールされ指定された中心点にマップを移動する
 *       これはグローバルメソッドなので宣言の先頭にvarはつけないでください
 * @param {Object} ext Extent
 * @returns なし
 */
showAtThisLocation = function (ext) {
    window.getMap().setExtent(ext, false);
};

/**
 * @function getSelectLayerIds
 * @summary 選択中のレイヤーID一覧取得
 * @desc 選択中のレイヤーID一覧取得
 * @returns {Object} 選択中のレイヤーID一覧
 */
var getSelectLayerIds = function () {
    // 選択中のレイヤーバーに追加されているIDの一覧を取得
    var ids = [];
    var listLength = window.globalVariables.layerWidgetList.length;
    for (var i = 0; i < listLength; i++) {
        ids.push(window.globalVariables.layerWidgetList[i].layerId);
    }
    return ids;
};

var mapWindowJs = function () {
    /**
     * @function initDojo
     * @summary フレームワーク初期化
     * @desc dojoフレームワークのinit.jsを実行し、フレームワークを利用可能にする
     * @returns なし
     */
    var initDojo = function () {
        var isOnload = false;
        var loadFilePath = loadUrlParams.arcDomainUrl + globalVariables.initJs + '/init.js';
        var domScript = document.createElement('script');
        domScript.src = loadFilePath;
        document.head.appendChild(domScript);

        // init.jsのロード完了イベント
        domScript.onload = function () {

            // 外部CSSの読み込み
            loadCss();
            // マップインスタンス生成(マップ表示領域の確保は別途行う)
            mapInit();
        };
    };

    /**
     * @function loadCss
     * @summary 外部CSS読み込み
     * @desc arcGIS側のCSSを読み込む
     * @returns なし
     */
    var loadCss = function () {

        // CSS読み込み
        require(['dojo/dom-construct', 'dojo/query'], function (domConstruct, query) {
            (function () {
                var loadCssList = new Array();
                loadCssList.push('esri/css/esri.css');
                loadCssList.push('esri/dijit/css/Scalebar.css');
                loadCssList.push('dijit/themes/claro/claro.css');
                loadCssList.push('dojox/layout/resources/FloatingPane.css');
                loadCssList.push('dojox/layout/resources/ResizeHandle.css');
                loadCssList.push('dojox/grid/resources/claroGrid.css');

                var max = loadCssList.length;
                for (var i = 0; i < max; i++) {
                    var css = require.toUrl(loadCssList[i]);
                    var head = query('head')[0];
                    var link = domConstruct.create('link');
                    link.type = 'text/css';
                    link.rel = 'stylesheet';
                    link.href = css.toString();
                    head.appendChild(link);
                }
            }());
        });
    };

    var mapInit = function () {
        require([
            'dojo/parser',
            'dojo/dom',
            'Common/ShowMessage',
            'ShowWindowFunc/ShowGISWindowFunc/ShowMainWindowFunc/Map',
            'ShowWindowFunc/ShowGISWindowFunc/ShareInfoFunc/ShareInfoBookMark'
        ],
            function (
                parser,
                dom,
                ShowMessage,
                MapArea,
                ShareInfoBookMark
            ) {

                try {
                    // 親ウィンドウと非同期に処理する子ウィンドウでも解析する
                    var shareInfoBookMark = new ShareInfoBookMark();
                    window.globalVariables.urlParamObj = shareInfoBookMark.restorLink();
                    if (window.globalVariables.urlParamObj.Lang === null) {
                        window.globalVariables.urlParamObj.Lang = '0';
                    }

                    // polarId 表示モード 1：通常表示、2：極域2D、3：極域3D
                    globalVariables.polarId = 1;
                    if (window.globalVariables.urlParamObj.polarId !== null) {
                        globalVariables.polarId = parseInt(window.globalVariables.urlParamObj.polarId);
                    }

                    // map 初期化
                    loadingState = 'Loading';
                    errorState = 'Error';
                    var mapArea = new MapArea({}, 'mapPlace');
                    mapArea.startup();

                    // onloadでここに制御が来る
                    // 画面表示機能実行
                    main();
                } catch (error) {
                    ShowMessage.ExceptionMessage(error);
                }
            });
    };

    function main() {
        require([
            'dojo/dom',
            'dojo/on',
            'dojo/dom-style',
            'dojo/dom-construct',
            'esri/map',
            'esri/dijit/OverviewMap',
            'esri/geometry/Extent',
            'esri/geometry/Point',
            'dojo/text!Widgets/CommonConfig.json',
            'dojo/text!Widgets/MapConfig.json',
            'dojo/text!Widgets/MenuConfig.json',
            'ShowWindowFunc/ShowGISWindowFunc/ShowMainWindowFunc/Map',
            'ShowWindowFunc/ShowGISWindowFunc/GetPresentLocationFunc/PresentLocation',
            'ShowWindowFunc/ShowGISWindowFunc/ShowMainWindowFunc/MouseLocation',
            'ShowWindowFunc/ShowGISWindowFunc/ShowMainWindowFunc/MapScalebar',
            'ShowWindowFunc/ShowGISWindowFunc/ShowMainWindowFunc/MapController',
            'Common/CreateObjectsOfMenu',
            'Common/ValueCheck',
            'Common/ShowMessage',
            'Common/ProgressAnimation',
            'Common/Coordinate',
            'dojo/_base/lang',
            'dojo/text!Widgets/MainConfig.json',
            'ShowWindowFunc/ShowGISWindowFunc/ShowSymbolFunc/ShowSymbolMain',
            'ShowWindowFunc/ShowGISWindowFunc/ShowSymbolFunc/ShowMarkerSymbol',
            'ShowWindowFunc/ShowGISWindowFunc/ShowLayerFunc/LayerMain',
            'dojo/domReady!'
        ],
            function (
                dom,
                on,
                domStyle,
                domConstruct,
                Map,
                OverviewMap,
                Extent,
                Point,
                CommonConfigJSON,
                MapConfigJSON,
                MenuConfigJSON,
                MapArea,
                PresentLocation,
                MouseLocation,
                MapScalebar,
                MapController,
                CreateObjectsOfMenu,
                chk,
                ShowMessage,
                ProgressAnimation,
                Coordinate,
                lang,
                MainConfigJSON,
                ShowSymbolMain,
                ShowMarkerSymbol,
                LayerMain
            ) {
                // プログレスバーを表示する
                ProgressAnimation.showProgress();

                /**
                 * @function createObject
                 * @summary 各機能のコントローラー生成
                 * @desc メイン画面のヘッダメニューがDBアクセスのレスポンス返却の契機で
                         完了するためその契機で各機能のコントローラーを生成する
                 * @returns なし
                 */
                var createMenuObjectsSubWindow = function () {
                    // ヘッダメニューに表示してある機能を生成する
                    globalVariables.objOfMenu = new CreateObjectsOfMenu();
                };

                /**
                 * @function mapLoadAfter
                 * @summary マップ読込後処理
                 * @desc マップ読込後に画面の初期化を行う
                 * @returns なし
                 */
                var mapLoadAfter = function () {
                    var _extentData = _esriMap.extent;

                    // 各機能のコントローラーをnewする機能を呼び出す
                    createMenuObjectsSubWindow();

                    // polarId 表示モード 2：極域2Dの場合は地図上のコンポーネントを作成しない
                    if (2 !== globalVariables.polarId) {
                        // スケール表示
                        var scalebar = new MapScalebar();
                        scalebar.startup();

                        // 縮尺コントローラ表示
                        var mapController = new MapController({}, 'controller');
                        mapController.startup();


                        // 座標・表示(マウス位置座標)
                        var locationDisplay = new MouseLocation({}, 'viewLatLon');
                        locationDisplay.startup();

                        /*
                         * 日本全域表示
                         * MAPを日本全域表示の位置を中心にして全国が表示されるように縮小を調整する
                         */
                        var HomeButtonNode = dom.byId('HomeButton');
                        _createInputNode(HomeButtonNode, mainConfig.HOME_BUTTON_IMAGE);
                        _createSpanNode(HomeButtonNode, menuConfig.toolTipIconSubJp, mainConfig.HOME_BALHELP_JP);
                        _createSpanNode(HomeButtonNode, menuConfig.toolTipIconSubEn, mainConfig.HOME_BALHELP_EN);


                        var position = [defLon, defLat];
                        on(HomeButtonNode, 'click', function () {
                            try {
                                var location = globalVariables.location; // 現在位置取得オブジェクト
                                if (location !== null) {
                                    location.removeCenterMark();
                                }
                                var extent = new Extent(mapConfig.initialExtent);
                                _esriMap.setExtent(extent);

                            } catch (error) {
                                ShowMessage.ExceptionMessage(error);
                            }
                        });

                        var presentLocationIconNodeNode = dom.byId('Location');
                        _createInputNode(presentLocationIconNodeNode, mainConfig.LOCATION_BUTTON_IMAGE);
                        _createSpanNode(presentLocationIconNodeNode,
                            menuConfig.toolTipIconSubJp, mainConfig.LOCATION_BALHELP_JP);
                        _createSpanNode(presentLocationIconNodeNode,
                            menuConfig.toolTipIconSubEn, mainConfig.LOCATION_BALHELP_EN);

                        // 現在位置取得生成 イベントリスナーをコンストラクタで貼っている
                        presentLocationPlace = new PresentLocation(_esriMap);
                    }
                    // シンボル制御クラス
                    this._clsSymbolMain = new ShowSymbolMain(_esriMap);

                    // レイヤ制御クラス
                    this._clsLayerMain = new LayerMain(_esriMap, 0, this._clsSymbolMain);

                    window.globalVariables.layerMainObj = this._clsLayerMain;

                    // 「すべてのレイヤー」を開いた状態を初期表示とする
                    this._clsLayerMain._showAllLayerMenu();

                    // 初回実行：隠しスクリーンサイズ設定
                    screenSizeSetting();

                    var hideScreenMainNode = parent.document.getElementById('hideScreenMain');
                    var hideScreenNode = document.getElementById('hideScreenSub');

                    // 親画面隠しスクリーン非表示化
                    hideScreenMainNode.classList.add('hideScreenHidden');
                    hideScreenMainNode.classList.remove('hideScreen');

                    // 隠しスクリーン非表示化
                    hideScreenNode.classList.add('hideScreenHidden');
                    hideScreenNode.classList.remove('hideScreen');

                    window.addEventListener('resize', function (event) {
                        var newHei = 0;

                        // デバイス判定
                        if (parent.globalVariables.userAgent.match(/(iphone|ipad|ipod|android)/i)) {
                            var menuHei = parent.window.globalVariables.MenuHeight;
                            // PC以外
                            var ori = Math.abs(window.orientation);
                            if (90 === ori) {
                                // よこ
                                newHei = parent.window.globalVariables.deviceShortHeight - menuHei;
                            } else {
                                // たて
                                newHei = parent.window.globalVariables.deviceLargeHeight - menuHei;
                            }
                            var strHei = newHei + 'px';
                            domStyle.set(dojo.byId('mapArea'), 'height', strHei);
                            parent.window.globalVariables.htmlNodeCell1.style.height = strHei;
                            parent.window.globalVariables.htmlNodeCell2.style.height = strHei;
                        } else {
                            // PC
                            newHei = window.innerHeight;
                            domStyle.set(dojo.byId('mapArea'), 'height', newHei + 'px');
                        }
                        // 隠しスクリーンサイズ設定
                        screenSizeSetting();

                    });

                    // 共有URLの中心点とzoomの処理
                    showAtThisLocationForShareURL();

                    // 2画面連動処理MAPの変更イベントを受信して親画面へ通知する
                    on(_esriMap, 'pan-end', function (evt) {
                        try {
                            _extentData = _esriMap.extent;
                            if (true !== globalVariables.isCurrentMapWindow) {

                                // この画面が非アクティブなら何もしない
                                return;
                            }

                            if (null !== locationLinkOfPrent) {
                                locationLinkOfPrent(_esriMap.extent, globalVariables.isCurrentMapWindow);
                            }
                        } catch (error) {
                            ShowMessage.ExceptionMessage(error);
                        }
                    });

                    on(_esriMap, 'zoom-end', function () {
                        try {
                            _extentData = _esriMap.extent;
                            if (true !== globalVariables.isCurrentMapWindow) {
                                // この画面が非アクティブなら何もしない
                                return;
                            }

                            if (null !== locationLinkOfPrent) {
                                locationLinkOfPrent(_esriMap.extent, globalVariables.isCurrentMapWindow);
                            }
                        } catch (error) {
                            ShowMessage.ExceptionMessage(error);
                        }
                    });

                    on(_esriMap, 'resize', function () {
                        try {
                            // デバイス判定
                            if (parent.globalVariables.userAgent.match(/(iphone|ipad|ipod|android)/i)) {

                                var newHei = 0;
                                var menuHei = parent.window.globalVariables.MenuHeight;
                                var ori = Math.abs(window.orientation);
                                if (90 === ori) {
                                    // よこ
                                    newHei = parent.window.globalVariables.deviceShortHeight - menuHei;
                                } else {
                                    // たて
                                    newHei = parent.window.globalVariables.deviceLargeHeight - menuHei;
                                }
                                domStyle.set(dojo.byId('map'), 'height', newHei + 'px');

                            } else {
                                // mapのheightは、常に親であるmapAreaのheightに合わせる。
                                // mapAreaのheightは、ウィンドウのresizeイベントで設定する。
                                // ※上書きする理由は、このfunctionに届いた時点で、子ノードを含むesriMapのリサイズが
                                //   発生したからであり、esriMapContainer等子ノードが自動的にサイズ変更されることにより
                                //   mapノードに余白ができてしまったりするため。
                                domStyle.set(dojo.byId('map'), 'height', '100%');
                            }

                            if (true !== globalVariables.isCurrentMapWindow) {

                                // この画面が非アクティブなら何もしない
                                return;
                            }

                            // リサイズが完了してしばらくしないと中心点の設定ができない
                            setTimeout(function () {
                                _esriMap.centerAt(_extentData.getCenter()).then(function () {
                                    try {
                                        locationLinkOfPrent(_esriMap.extent, globalVariables.isCurrentMapWindow);
                                    } catch (error) {
                                        ShowMessage.ExceptionMessage(error);
                                    }

                                });
                            }, mainConfig.MAP_RESIZE_AT_EXTENT_WAIT_TIME);
                        } catch (error) {
                            ShowMessage.ExceptionMessage(error);
                        }
                    });

                    // メソッドを設定した印をつけておく このフラグは子画面が連動可能であることを示す
                    showAtThisLocation.isExist = true;

                    // 右画面マップ生成時用処理
                    parent.window.globalVariables.htmlNodeRightLoad();

                    /**
                     * @function changeActiveWindowCtlr
                     * @summary 地図画面アクティブ変更処理
                     * @desc 親画面から地図のアクティブ/非アクティブが切り替わった際に実施する処理を実装するメソッド
                             これはグローバルメソッドなので宣言の先頭にvarはつけないでください
                     * @param {Object} ext Extent
                     * @returns なし
                     */
                    window.changeActiveWindowCtlr = function () {
                        // アクティブ/非アクティブが変更されたのでイベントを張り替える
                        globalVariables.objOfMenu.changeCntrls(window.globalVariables.isCurrentMapWindow);
                    };

                    // インフォウィンドウの文言の多元語化対応
                    var actionZoomToNode = null;
                    actionZoomToNode = dom.byId('map_root');
                    if (false === chk.isNull(actionZoomToNode)) {
                        var actionZoomToDom = actionZoomToNode.getElementsByClassName('zoomTo');
                        if (false === chk.isNull(actionZoomToDom[0])) {
                            // タイトル属性削除
                            actionZoomToDom[0].removeAttribute('title');
                            // 本文を多言語化対応
                            actionZoomToDom[0].innerHTML =
                                '<span class=\'langJp\'>ズーム</span><span class=\'langEn\'>Zoom</span>';
                        }
                    }
                    // タブレット対応
                    var mapNode = dom.byId('map');
                    // デバイス判定
                    if (parent.window.globalVariables.userAgent.match(/(iphone|ipad|ipod|android)/i)) {
                        if (false === chk.isNull(actionZoomToNode) && false === chk.isNull(mapNode)) {
                            if (0 === parent.window.globalVariables.deviceHeight) {
                                domStyle.set(actionZoomToNode, 'height', window.innerHeight + 'px');
                                domStyle.set(mapNode, 'height', window.innerHeight + 'px');
                            } else {
                                domStyle.set(actionZoomToNode, 'height',
                                    parent.window.globalVariables.deviceHeight);
                                domStyle.set(mapNode, 'height',
                                    parent.window.globalVariables.deviceHeight);
                            }
                        }
                    }

                    // プログレスバーを非表示にする
                    ProgressAnimation.hideProgress();
                };

                /**
                 * @function screenSizeSetting
                 * @summary 隠しスクリーンサイズ設定
                 * @desc 初期表示時の隠しスクリーンのサイズを設定する
                 * @returns なし
                 */

                var screenSizeSetting = function () {

                    // 親画面側のサイズ
                    var newParentHei = 0;
                    var newParentWid = 0;

                    var newHei = 0;
                    var newWid = 0;
                    var tdHeightSize = 0 - parent.window.globalVariables.MenuHeight;
                    var tdWidthSize = parent.window.globalVariables.deviceBrowserFixedAreaHeight;

                    // デバイス判定
                    if (parent.window.globalVariables.userAgent.match(/(iphone|ipad|ipod|android)/i)) {
                        // PC以外
                        var ori = Math.abs(window.orientation);
                        if (90 === ori) {
                            // よこ
                            // 親画面
                            newParentHei = parent.window.globalVariables.deviceShortHeight;
                            newParentWid = parent.window.globalVariables.deviceLargeHeight + tdWidthSize;

                            // 子画面ヘッダメニューの厚さ分、MAPの領域を減らす
                            tdHeightSize += parent.window.globalVariables.deviceShortHeight;    // height - メニュー高
                            tdWidthSize += parent.window.globalVariables.deviceLargeHeight;     // width + ブラウザマージン
                            newHei = tdHeightSize;
                            newWid = tdWidthSize;

                        } else {
                            // たて
                            // 親画面
                            newParentHei = parent.window.globalVariables.deviceLargeHeight;
                            newParentWid = parent.window.globalVariables.deviceShortHeight + tdWidthSize;

                            // 子画面ヘッダメニューの厚さ分、MAPの領域を減らす
                            tdHeightSize += parent.window.globalVariables.deviceLargeHeight;    // height - メニュー高
                            tdWidthSize += parent.window.globalVariables.deviceShortHeight;     // width + ブラウザマージン
                            newHei = tdHeightSize;
                            newWid = tdWidthSize;

                        }

                    } else {
                        // PC
                        // 親画面
                        newParentHei = parent.window.innerHeight;
                        newParentWid = parent.window.innerWidth;

                        // 子画面、2画面
                        newHei = window.innerHeight;
                        newWid = window.innerWidth;
                    }

                    // 隠しスクリーンサイズ設定処理
                    // 親画面
                    var hideScreenMainNode = window.parent.document.getElementById('hideScreenMain');

                    hideScreenMainNode.style.top = 0 + 'px';
                    hideScreenMainNode.style.left = 0 + 'px';
                    hideScreenMainNode.style.height = newParentHei + 'px';
                    hideScreenMainNode.style.width = newParentWid + 'px';

                    // 子画面
                    var hideScreenNode = document.getElementById('hideScreenSub');

                    domStyle.set(hideScreenNode, 'top', '0px');
                    domStyle.set(hideScreenNode, 'left', '0px');
                    domStyle.set(hideScreenNode, 'height', newHei + 'px');
                    domStyle.set(hideScreenNode, 'width', newWid + 'px');

                    // 2画面
                    var hideScreenmapWinNode = window.parent.document.getElementById('mapWinHideScreen');

                    domStyle.set(hideScreenmapWinNode, 'height', newHei + 'px');

                };

                /**
                 * @function _createInputNode
                 * @summary inputノード作成
                 * @desc 地図操作アイコンのINPUTノードを作成する
                 * @param {Object} targetNode inputタグを設定する親ノード
                 * @param {String} imageUrl アイコンのimageのURL
                 * @returns なし
                 */
                var _createInputNode = function (targetNode, imageUrl) {
                    var workNode = domConstruct.create('input');
                    workNode.type = 'image';
                    workNode.src = imageUrl;
                    targetNode.appendChild(workNode);
                };

                /**
                 * @function _createSpanNode
                 * @summary spanノード作成
                 * @desc 地図操作アイコンのSpanノードを作成する
                 * @param {Object} targetNode   Spanタグを設定する親ノード
                 * @param {String} StrClassName Spanクラスの名前
                 * @param {String} StrText      SpanノードのText
                 * @returns なし
                 */
                _createSpanNode = function (targetNode, StrClassName, StrText) {
                    const EleNode = document.createElement('span');
                    const AtribNode = document.createAttribute('class');
                    const TextNode = document.createTextNode(StrText);

                    //プロパティ、値の設定
                    AtribNode.value = StrClassName;
                    EleNode.setAttributeNode(AtribNode);

                    //ノードの挿入
                    EleNode.appendChild(TextNode);
                    targetNode.appendChild(EleNode);
                };

                /**
                 * @function showAtThisLocationForShareURL
                 * @summary マップの中心位置を設定する共有URL用
                 * @desc 親画面から指定された中心点にマップを移動する
                 * @returns なし
                 */
                var showAtThisLocationForShareURL = function () {
                    try {
                        if (chk.isNull(window.globalVariables.urlParamObj.centerx)) {
                            // 共有URL指定ではないルート
                            if (true === globalVariables.isCurrentMapWindow &&
                                2 !== globalVariables.polarId &&
                                3 !== globalVariables.polarId) {

                                // アクティブ画面の場合で且つ通常地図表示の場合
                                // 現在位置取得
                                presentLocationPlace.getLocation(true);
                            } else {

                                // 非アクティブの場合
                                // 親から中心点とズームの通知が来るはずなので何もしない
                            }
                            return;
                        } else {

                            // 共有URL指定のルート
                            var lat = parseFloat(window.globalVariables.urlParamObj.centery);
                            var lon = parseFloat(window.globalVariables.urlParamObj.centerx);
                            var zoom = parseInt(window.globalVariables.urlParamObj.cacheLevel);

                            _esriMap.setLevel(zoom).then(function () {
                                // 2D表示かどうか判定する
                                if (window.globalVariables.polarId === 2) {
                                    // 2D表示の場合は座標を変換する
                                    var point = new Point({ latitude: lat, longitude: lon });
                                    var pt = Coordinate.projectForSync(point, _esriMap.spatialReference.wkid);

                                    //マップセンターを移動
                                    _esriMap.centerAt(new Point([pt.x, pt.y], _esriMap.spatialReference.wkid));
                                } else {
                                    // 通常地図の場合は入力パラメータの緯度経度をそのまま使う

                                    //マップセンターを移動
                                    _esriMap.centerAt(new Point([lon, lat]));
                                }
                            });
                            return;
                        }
                    } catch (error) {
                        ShowMessage.ExceptionMessage(error);
                    }
                };

                var _esriMap = window.getMap();

                // タイトル名
                var commonConfig = eval('(' + CommonConfigJSON + ')');

                // ウィンドウタイトルを設定
                var titleWindow = dojo.byId('windowTitle');
                titleWindow.innerHTML = commonConfig.windowTitle;

                // 共通の座標機能をグローバルに配置して親からの共有URL機能から利用できるようにする
                globalVariables.coordinate = Coordinate;

                // Configの取得
                var mainConfig = eval('(' + MainConfigJSON + ')');
                var mapConfig = eval('(' + MapConfigJSON + ')');
                var menuConfig = eval('(' + MenuConfigJSON + ')');

                // デフォルトの中心座標
                var defLat = mainConfig.DEF_LAT;
                var defLon = mainConfig.DEF_LON;
                var defZoom = mainConfig.DEF_ZOOM;
                var polarLat = mainConfig.POLAR_LAT;
                var polarLon = mainConfig.POLAR_LON;

                if (_esriMap.loaded === true) {
                    mapLoadAfter();
                } else {
                    _esriMap.on('load', lang.hitch(this, mapLoadAfter));
                }
            });     // requireの終わり
    }           // mapWindowの終わり
    // 処理開始
    initDojo();
};

// 処理開始
// polarId 表示モード 1：通常表示、2：極域2D、3：極域3D
if (3 === globalVariables.polarId) {
    // フレームワーク初期化とmain3Dメソッドの呼び出し
    mapWindow3DJs();
} else {
    // フレームワーク初期化とmainメソッドの呼び出し
    mapWindowJs();
}
