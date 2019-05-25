/**
 * @class RequestServer
 * @classdesc サーバへリクエストする
 */
define([
    'dojo/request/xhr',
    'dojo/_base/lang',
    'dojo/json',
    'Common/ValueCheck',
    'dojo/Deferred'
],
    function (
        xhr,
        DojoLang,
        DojoJson,
        chk,
        Deferred
    ) {
        return {
            TIME_OUT: 10000, // ミリ秒単位
            RETRY_COUNT: 0,
            INTERVAL: 1000, // ミリ秒単位

            /**
             * @function doPost
             * @summary GISサーバのApiへリクエスト
             * @desc GISサーバのApiへリクエストする
             * @param {String} apiPath api以降のURLを指定する
             * @param {Object} params 検索条件
             * @param {Object} recieveAfterCallBack データを受信した後に実行するコールバック
             * @param {Object} errCallback エラー発生時に実行するコールバック(省略可)
             * @returns {Object} deferred
             */
            doPost: function (apiPath, params, recieveAfterCallBack, errCallback) {
                return this.doPostGisAPIBaseURL(loadUrlParams.gisApiDomainUrl, apiPath,
                    params, recieveAfterCallBack, errCallback);
            },

            /**
             * @function doPost
             * @summary GISサーバのApiへリクエスト(リアルタイム津波防災情報図専用)
             * @desc GISサーバのApiへリクエストする
             * @param {String} apiPath api以降のURLを指定する
             * @param {Object} params 検索条件
             * @returns {Object} deferred
             */
            doPostSis: function (apiPath, params) {
                var deferred = new Deferred();

                if (chk.isNull(apiPath)) {
                    return deferred.promise;
                }
                var requestUrl = loadUrlParams.gisApiDomainUrl + apiPath;

                xhr(requestUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    data: params,
                    handleAs: 'json',
                    sync: true
                }).then(function (data) {
                    return deferred.resolve(data);
                },
                    function (err) {
                        return deferred.resolve('');
                    });

                return deferred.promise;

            },
            /** @function doPostArcGisRestApi
              * @summary arcGISサーバリクエスト
              * @desc arcGISのRestサービスにリクエストを発行する
              * @param {String} apiurl RestApiURL
              * @param {Object} params URLパラメータを指定するサーバーのサービスサイトルート以降を設定する
              * @param {Object} recieveAfterCallBack データを受信した後に実行するコールバック
              * @param {Object} errCallback エラー発生時に実行するコールバック(省略可)
              * @param {Number} timeout タイムアウト値(ミリ秒単位)(デフォルト10秒)(省略可)
              * @param {Number} counter リトライカウンタ(コール元からは指定禁止)
              * @returns {Object} response
              */
            doPostArcGisRestApi: function (apiurl, params, recieveAfterCallBack, errCallback, timeout, counter) {
                return this.doPostArcGisRestApiBaseURL(loadUrlParams.baseLayerUrl, apiurl,
                    params, recieveAfterCallBack, errCallback, timeout, counter);
            },
            /** @function doPostRestOpenCloud
              * @summary arcGISサーバリクエスト
              * @desc arcGISのRestサービスにリクエストを発行する
              * @param {String} apiurl RestApiURL
              * @param {Object} params URLパラメータを指定するサーバーのサービスサイトルート以降を設定する
              * @param {Object} recieveAfterCallBack データを受信した後に実行するコールバック
              * @param {Object} errCallback エラー発生時に実行するコールバック(省略可)
              * @param {Number} timeout タイムアウト値(ミリ秒単位)(デフォルト10秒)(省略可)
              * @param {Number} counter リトライカウンタ(コール元からは指定禁止)
              * @returns {Object} response
              */
            doPostArcGisRestApiOpenCloud: function (apiurl, params, recieveAfterCallBack,
                errCallback, timeout, counter) {
                return this.doPostArcGisRestApiBaseURL(this.getOpenCloudPortalURL(), apiurl,
                    params, recieveAfterCallBack, errCallback, timeout, counter);
            },
            /** @function doPostArcGisRestApiBaseURL
              * @summary arcGISサーバリクエスト
              * @desc arcGISのRestサービスにリクエストを発行する
              * @param {String} baseurl baseURL
              * @param {String} apiurl RestApiURL
              * @param {Object} params URLパラメータを指定するサーバーのサービスサイトルート以降を設定する
              * @param {Object} recieveAfterCallBack データを受信した後に実行するコールバック
              * @param {Object} errCallback エラー発生時に実行するコールバック(省略可)
              * @param {Number} timeout タイムアウト値(ミリ秒単位)(デフォルト10秒)(省略可)
              * @param {Number} counter リトライカウンタ(コール元からは指定禁止)
              * @returns なし
              */
            doPostArcGisRestApiBaseURL: function (baseurl, apiurl, params,
                recieveAfterCallBack, errCallback, timeout, counter) {
                // Restにアクセスする際はdojo/request/xhrだとエラーになるのでdojo.xhrPostを使用している
                // また、プロパティにPOSTパラメータを指定する際、postDataではエラーになるのでcontentを使用して設定している
                var that = this;

                var requestUrl = baseurl + '/arcgis/rest/services' + apiurl;
                dojo.xhrPost({
                    url: requestUrl,
                    //postData: postdata,
                    content: params,
                    timeout: this.TIME_OUT,
                    load: function (response) {
                        var responseInstance = DojoJson.parse(response);
                        // 正常時のコールバック
                        recieveAfterCallBack(responseInstance);
                    },
                    error: function (err) {
                        if (chk.isNull(counter)) {
                            // エラーの初回はcounter値に0設定
                            counter = 0;
                        } else {
                            // エラー2回目以降はcounterインクリメント
                            counter++;
                        }

                        if (that.RETRY_COUNT > counter) {
                            // リトライルート
                            setTimeout(DojoLang.hitch(that, that.doPostArcGisRestApiBaseURL(baseurl, apiurl, params,
                                recieveAfterCallBack, errCallback, timeout, counter)), that.INTERVAL);
                            return;
                        }
                        // リトライアウト
                        if (!chk.isNull(errCallback)) {
                            // エラーコールバックコール
                            errCallback(err);
                        }
                    }
                });
            },

            /**
             * @function doPostLogger
             * @summary Webサーバのログ出力Apiへリクエスト
             * @desc Webサーバのログ出力Apiへリクエストする
             * @param {String} apiPath apiパス
             * @param {Object} params ログ出力パラメータ
             * @param {Object} recieveAfterCallBack データを受信した後に実行するコールバック
             * @param {Object} errCallback エラー発生時に実行するコールバック(省略可)
             * @returns なし
             */
            doPostLogger: function (apiPath, params, recieveAfterCallBack, errCallback) {

                var requestUrl = loadUrlParams.webApiDomainUrl + '/msilweblog' + apiPath;

                xhr(requestUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    data: dojo.toJson(params),
                    handleAs: 'json',
                    sync: true
                }).then(function (data) {
                    var resultData = data;
                    recieveAfterCallBack(resultData);
                },
                    function (err) {
                        if (!chk.isNull(errCallback)) {
                            errCallback(err);
                        }
                    });
            },

            /**
             * @function doPostToken
             * @summary WebサーバのTokenApiへリクエスト
             * @desc WebサーバのTokenApiへリクエストする
             * @param {Object} requestUrl トークン発行先URL
             * @param {Object} recieveAfterCallBack データを受信した後に実行するコールバック
             * @param {Object} errCallback エラー発生時に実行するコールバック(省略可)
             * @returns なし
             */
            doPostToken: function (requestUrl, recieveAfterCallBack, errCallback) {

                var exeServer = 'usualy';
                // 環境判定
                if (loadUrlParams.otherDomainUrl !== '') {
                    exeServer = 'confidential';
                }
                // 要求先判定
                var requestObj = this.getPortalUrlAutoSelect(requestUrl);
                var effectiveToken = null;
                var effectiveTime = null;
                if (exeServer === 'confidential' && requestObj.requestServer === 'other') {
                    effectiveToken = window.globalVariables.effectiveOtherToken;
                    effectiveTime = window.globalVariables.effectiveOtherTime;
                } else {
                    effectiveToken = window.globalVariables.effectiveBaseToken;
                    effectiveTime = window.globalVariables.effectiveBaseTime;
                }
                // 取得済みのトークンが存在している、かつ有効時刻を過ぎていなければ
                // コールバックを即時実行する
                var nowDate = new Date();
                var dateDifference = nowDate - effectiveTime;
                if (!chk.isNull(effectiveToken) && dateDifference < effectiveMinutes * 60 * 1000) {
                    var resultData = {};
                    resultData.token = effectiveToken;
                    recieveAfterCallBack(resultData);
                } else {
                    requestObj.requestUrl += '/msilwebtoken/api/token/new';

                    xhr(requestObj.requestUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        data: null,
                        handleAs: 'json',
                        sync: true
                    }).then(function (data) {
                        var resultData = data;
                        recieveAfterCallBack(resultData);
                        // 取得したトークンと現在時刻をグローバル変数に格納する
                        if (requestObj.requestServer === 'other') {
                            window.globalVariables.effectiveOtherToken = resultData.token;
                            window.globalVariables.effectiveOtherTime = new Date();
                        } else {
                            window.globalVariables.effectiveBaseToken = resultData.token;
                            window.globalVariables.effectiveBaseTime = new Date();
                        }
                    },
                        function (err) {
                            if (!chk.isNull(errCallback)) {
                                errCallback(err);
                            }
                        });
                }
            },

            /**
             * @function doPostTokenForSync
             * @summary WebサーバのTokenApiへリクエスト(同期処理用)
             * @desc 接続先先URLに対応するWebサーバのTokenApiへリクエストする(同期処理用)
             * @param {Object} targetUrl 接続先先URL
             * @returns {Object} Deferred
            */
            doPostTokenForSync: function (targetUrl) {

                var exeServer = 'usualy';
                // 環境判定
                if (loadUrlParams.otherDomainUrl !== '') {
                    exeServer = 'confidential';
                }
                // 要求先判定
                var requestObj = this.getPortalUrlAutoSelect(targetUrl);
                var effectiveToken = null;
                var effectiveTime = null;
                if (exeServer === 'confidential' && requestObj.requestServer === 'other') {
                    effectiveToken = window.globalVariables.effectiveOtherToken;
                    effectiveTime = window.globalVariables.effectiveOtherTime;
                } else {
                    effectiveToken = window.globalVariables.effectiveBaseToken;
                    effectiveTime = window.globalVariables.effectiveBaseTime;
                }

                var deferred = new Deferred();
                // 取得済みのトークンが存在している、かつ有効時刻を過ぎていなければ
                // トークンを即時返却する
                var nowDate = new Date();
                var dateDifference = nowDate - effectiveTime;
                if (!chk.isNull(effectiveToken) && dateDifference < effectiveMinutes * 60 * 1000) {
                    var data = {};
                    data.token = effectiveToken;
                    return deferred.resolve(data.token);
                } else {
                    requestObj.requestUrl += '/msilwebtoken/api/token/new';
                    xhr(requestObj.requestUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        data: null,
                        handleAs: 'json',
                        sync: true
                    }).then(function (data) {
                        // 取得したトークンと現在時刻をグローバル変数に格納する
                        if (requestObj.requestServer === 'other') {
                            window.globalVariables.effectiveOtherToken = data.token;
                            window.globalVariables.effectiveOtherTime = new Date();
                        } else {
                            window.globalVariables.effectiveBaseToken = data.token;
                            window.globalVariables.effectiveBaseTime = new Date();
                        }
                        return deferred.resolve(data.token);
                    },
                        function (err) {
                            return deferred.resolve('');
                        });

                    return deferred.promise;

                }


            },

            /**
             * @function doPostTokenForSyncOld
             * @summary WebサーバのTokenApiへリクエスト(同期処理用)(旧Rest APIバージョン)
             * @desc 接続先先URLに対応するWebサーバのTokenApiへリクエストする(同期処理用)
             * @param {Object} targetUrl 接続先先URL
             * @returns {Object} Deferred
            */
            doPostTokenForSyncOld: function (targetUrl) {

                var deferred = new Deferred();

                var requestObj = this.getPortalUrlAutoSelect(targetUrl);

                requestObj.requestUrl += '/msilwebtoken/api/token/old';
                xhr(requestObj.requestUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    data: null,
                    handleAs: 'json',
                    sync: true
                }).then(function (data) {
                    return deferred.resolve(data.token);
                },
                    function (err) {
                        return deferred.resolve('');
                    });

                return deferred.promise;

            },

            /**
             * @function doPostOther
             * @summary GISサーバのApiへリクエスト
             * @desc GISサーバのApiへリクエストする
             * @param {String} apiPath api以降のURLを指定する
             * @param {Object} params 検索条件
             * @param {Object} recieveAfterCallBack データを受信した後に実行するコールバック
             * @param {Object} errCallback エラー発生時に実行するコールバック(省略可)
             * @returns {Object} response
             */
            doPostOther: function (apiPath, params, recieveAfterCallBack, errCallback) {
                return this.doPostGisAPIBaseURL(loadUrlParams.otherDomainUrl, apiPath,
                    params, recieveAfterCallBack, errCallback);
            },

            /**
             * @function doPostGisAPIBaseURL
             * @summary GISサーバのApiへリクエスト
             * @desc GISサーバのApiへリクエストする
             * @param {String} baseurl baseURLを指定する
             * @param {String} apiPath api以降のURLを指定する
             * @param {Object} params 検索条件
             * @param {Object} recieveAfterCallBack データを受信した後に実行するコールバック
             * @param {Object} errCallback エラー発生時に実行するコールバック(省略可)
             * @returns {Object} response
             */
            doPostGisAPIBaseURL: function (baseurl, apiPath, params, recieveAfterCallBack, errCallback) {
                return this.doPostBaseURL(baseurl + '/msilgisapi', apiPath,
                    params, recieveAfterCallBack, errCallback);
            },

            /**
             * @function doPostBaseURL
             * @summary POSTリクエスト
             * @desc POSTリクエストする
             * @param {String} baseurl baseURLを指定する
             * @param {String} apiPath api以降のURLを指定する
             * @param {Object} params 検索条件
             * @param {Object} recieveAfterCallBack データを受信した後に実行するコールバック
             * @param {Object} errCallback エラー発生時に実行するコールバック(省略可)
             * @returns なし
             */
            doPostBaseURL: function (baseurl, apiPath, params, recieveAfterCallBack, errCallback) {

                if (chk.isNull(baseurl) || chk.isNull(apiPath)) {
                    return;
                }
                var requestUrl = baseurl + apiPath;

                xhr(requestUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    data: dojo.toJson(params),
                    handleAs: 'json',
                    sync: true
                }).then(function (data) {
                    var resultData = data;
                    recieveAfterCallBack(resultData);
                },
                    function (err) {
                        if (!chk.isNull(errCallback)) {
                            errCallback(err);
                        }
                    });
            },

            /**
             * @function getPortalUrlAutoSelect
             * @summary アクセス対象のURLをもとにPortalへリクエストURLを返却する
             * @desc アクセス対象のURLをもとにPortalへリクエストURLを返却する
             * @param {String} targetUrl アクセス対象のURLを指定する
             * @returns {Object} requestObj リクエスト先情報
            */
            getPortalUrlAutoSelect: function (targetUrl) {
                var requestObj = {};
                // デフォルトは自身のポータル
                requestObj.requestUrl = loadUrlParams.webApiDomainUrl;
                requestObj.requestServer = 'base';

                if (!chk.isNull(targetUrl)) {
                    if ((!chk.isNull(loadUrlParams.otherDomainUrl))
                        && (loadUrlParams.otherDomainUrl !== '')
                        && (-1 !== targetUrl.indexOf(loadUrlParams.otherDomainUrl))) {
                        // その他サーバを利用
                        // ※otherDomainUrlではなく、ポータル(otherPortalDomainUrl)にアクセスします。
                        requestObj.requestUrl = loadUrlParams.otherPortalDomainUrl;
                        requestObj.requestServer = 'other';
                    } else if ((!chk.isNull(loadUrlParams.otherPortalDomainUrl))
                        && (loadUrlParams.otherPortalDomainUrl !== '')
                        && (-1 !== targetUrl.indexOf(loadUrlParams.otherPortalDomainUrl))) {
                        // 外部ポータルが直接指定されている場合は外部ポータルURLを取得する
                        requestObj.requestUrl = loadUrlParams.otherPortalDomainUrl;
                        requestObj.requestServer = 'other';
                    }
                }
                return requestObj;

            },

            /**
             * @function getOpenCloudURL
             * @summary WebサーバのへリクエストURLを返却する
             * @desc WebサーバのへリクエストURLを返却する
             * @returns {String} WebサーバのへリクエストURL
            */
            getOpenCloudPortalURL: function () {
                // デフォルトは自身のポータル
                var requestUrl = loadUrlParams.webApiDomainUrl;

                if ((!chk.isNull(loadUrlParams.otherDomainUrl))
                    && (loadUrlParams.otherDomainUrl !== '')) {
                    // その他サーバを利用
                    // ※otherDomainUrlではなく、ポータル(otherPortalDomainUrl)にアクセスします。
                    requestUrl = loadUrlParams.otherPortalDomainUrl;
                } else if ((!chk.isNull(loadUrlParams.otherPortalDomainUrl))
                    && (loadUrlParams.otherPortalDomainUrl !== '')) {
                    // 外部ポータルが直接指定されている場合は外部ポータルURLを取得する
                    requestUrl = loadUrlParams.otherPortalDomainUrl;
                }

                return requestUrl;
            },

            /**
             * @function doPostNowTime
             * @summary Webサーバの現在時刻取得Apiへリクエスト
             * @desc Webサーバの現在時刻取得Apiへリクエストする
             * @param {Object} recieveAfterCallBack データを受信した後に実行するコールバック
             * @param {Object} errCallback エラー発生時に実行するコールバック(省略可)
             * @returns なし
             */
            doPostNowTime: function (recieveAfterCallBack, errCallback) {

                var requestUrl = loadUrlParams.webApiDomainUrl + '/msilgisapi/api/nowtime/jst';

                xhr(requestUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    handleAs: 'json',
                    sync: true
                }).then(function (data) {
                    var resultData = data;
                    if (resultData.result === false) {
                        errCallback('response error:' + requestUrl);
                    }
                    var nowtime = new Date(resultData.year,
                        resultData.month - 1,
                        resultData.day,
                        resultData.hour,
                        resultData.minute,
                        resultData.second);

                    recieveAfterCallBack(nowtime);
                },
                    function (err) {
                        if (!chk.isNull(errCallback)) {
                            errCallback(err);
                        }
                    });
            },

            /**
             * @function doPostNowTimeSync
             * @summary Webサーバの現在時刻取得Apiへリクエスト(同期)
             * @desc Webサーバの現在時刻取得Apiへリクエストする(同期)
             * @returns {Object} Deferred
             */
            doPostNowTimeSync: function () {

                var requestUrl = loadUrlParams.webApiDomainUrl + '/msilgisapi/api/nowtime/jst';
                var deferred = new Deferred();

                xhr(requestUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    handleAs: 'json',
                    sync: true
                }).then(function (data) {
                    var resultData = data;
                    if (resultData.result === false) {
                        errCallback('response error:' + requestUrl);
                    }
                    var nowtime = new Date(resultData.year,
                        resultData.month - 1,
                        resultData.day,
                        resultData.hour,
                        resultData.minute,
                        resultData.second);

                    deferred.resolve(nowtime);
                },
                    function (err) {
                        deferred.reject(err);
                    });
                return deferred.promise;
            },

            /**
             * @function getJsonFile
             * @summary 外部サーバリクエストでJsonファイルを取得
             * @desc 外部サーバリクエストでJsonファイルを取得し、引数のコールバック関数に返却
             * @param {String} jsonFileUrl アクセス対象のURLを指定する
             * @param {Function} callbackFunction Jsonファイル取得完了後に実行する関数
             * @param {Function} errorFunction Jsonファイル取得失敗時に実行する関数
             * @returns なし
            */
            getJsonFile: function (jsonFileUrl, callbackFunction, errorFunction) {
                $.ajax({
                    type: 'GET',
                    url: jsonFileUrl,
                    dataType: 'json',
                    timeout: this.TIME_OUT,
                    success: callbackFunction,
                    error: errorFunction
                });
            }
        };
    });

