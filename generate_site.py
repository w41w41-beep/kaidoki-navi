import os
import datetime

# 今日の日付を取得
today = datetime.date.today()

# HTMLファイルの内容を生成
html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>カイドキ-ナビ - お得な買い時を見つけよう！</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f7f6; color: #333; }}
        .container {{ max-width: 960px; margin: auto; padding: 20px; }}
        header {{ background-color: #fff; border-bottom: 1px solid #ddd; padding: 5px; text-align: center; }}
        /* タイトルとサブタイトルの上下マージンをなくし、タイトルを青色に戻す */
        header h1, header p {{ margin: 0; }}
        header h1 {{ color: #007bff; }}
        .search-bar {{ padding: 20px; text-align: center; background-color: #e9ecef; }}
        .search-bar input {{ width: 80%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }}
        .content {{ padding: 20px 0; }}
        .section-title {{ font-size: 24px; font-weight: bold; margin-bottom: 20px; text-align: center; }}
        
        /* 商品のレイアウトをFlexboxで修正 */
        .product-grid {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center; /* アイテムを中央に配置 */
            align-items: stretch; /* アイテムの高さを統一 */
            gap: 20px;
        }}

        .product-card {{ 
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s; 
            flex: 1 1 calc(33.333% - 20px); /* デスクトップで3列表示 */
            display: flex;
            flex-direction: column;
        }}
        .product-card:hover {{ transform: translateY(-5px); }}
        
        .product-card img {{ 
            width: 100%;
            height: 180px; /* 画像の高さを統一 */
            object-fit: contain; /* 画像をアスペクト比を維持して収める */
            display: block;
        }}

        .product-info {{ 
            padding: 15px;
            flex-grow: 1; /* 余ったスペースを埋める */
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 120px; /* コンテンツが少ない場合の最低限の高さ */
        }}

        .product-name {{ 
            font-size: 18px; 
            font-weight: bold; 
            margin-bottom: 5px;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2; /* 2行に制限 */
            -webkit-box-orient: vertical;
        }}
        .product-price {{ color: #dc3545; font-size: 20px; font-weight: bold; margin-bottom: 10px; }}
        .product-status {{ font-size: 14px; color: #28a745; font-weight: bold; }}
        
        /* スマートフォン向けレスポンシブデザイン（2列表示） */
        @media (max-width: 768px) {{
            .product-grid {{
                padding: 0 10px; /* 左右に余白を追加 */
            }}
            .product-card {{
                flex: 1 1 calc(50% - 15px); /* スマホで2列表示 */
            }}
            .product-name {{ 
                font-size: 16px;
            }}
            .product-price {{
                font-size: 18px;
            }}
            .product-status {{
                font-size: 12px;
            }}
        }}

        /* ジャンルリンクのコンテナスタイル */
        .genre-links-container {{
            max-width: 960px;
            margin: 20px auto;
            padding: 10px;
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        .genre-links a {{
            color: #007bff;
            text-decoration: none;
            font-weight: bold;
            margin: 0 15px;
            font-size: 16px;
        }}

        /* --- ジャンルリンクの自動仕切り線 --- */
        .genre-links a::after {{
            content: "|";
            color: #666;
            margin: 0 10px;
        }}
        /* 最後のリンクの後ろには仕切りを表示しない */
        .genre-links a:last-child::after {{
            content: "";
            margin: 0;
        }}
        /* ---------------------------------- */

        /* ページネーションのスタイル */
        .pagination-container {{
            text-align: center;
            margin-top: 20px;
        }}

        .pagination-link {{
            display: inline-block;
            margin: 0 5px;
            padding: 8px 12px;
            color: #007bff;
            text-decoration: none;
            border: 1px solid #007bff;
            border-radius: 5px;
            transition: background-color 0.3s;
        }}
        .pagination-link.disabled {{
            color: #ccc;
            border: 1px solid #ccc;
            cursor: not-allowed;
            pointer-events: none; /* クリックイベントを無効化 */
        }}

        .pagination-link:not(.disabled):hover {{
            background-color: #007bff;
            color: #fff;
        }}

        .pagination-link.active {{
            background-color: #007bff;
            color: #fff;
            font-weight: bold;
        }}

        .pagination-ellipsis {{
            display: inline-block;
            margin: 0 5px;
            padding: 8px 0;
        }}

        footer {{ text-align: center; padding: 20px; border-top: 1px solid #ddd; background-color: #fff; margin-top: 20px; }}
        .footer-links {{ display: flex; justify-content: center; gap: 20px; margin-top: 10px; }}
        .footer-links a {{ color: #007bff; text-decoration: none; }}
</style>
</head>
<body>
    <header>
        <div class="container">
            <h1>カイドキ-ナビ</h1>
            <p>お得な買い時を見つけよう！</p>
        </div>
    </header>

    <div class="search-bar">
        <input type="text" placeholder="商品名、キーワードで検索...">
    </div>

    <div class="genre-links-container">
        <div class="genre-links">
            <a href="#">パソコン</a>
            <a href="#">家電</a>
        </div>
    </div>

    <!-- AIとAPIが連携した際の「注目のおすすめ」セクション -->
    <div class="container content">
        <h2 class="section-title">AIが選んだ注目のおすすめ</h2>
        <div style="text-align: center; font-size: 16px; margin-bottom: 20px;">
            AIが価格データを解析し、<br>今最もお買い得な商品をここに自動でピックアップします！
        </div>
        <div class="product-grid">
            <div class="product-card">
                <a href="https://amzn.to/3I6rIdF" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61o7EzoRpBL._AC_SX679_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Apple AirPods Pro (第2世代)</div>
                        <div class="product-price">¥38,192</div>
                        <div class="product-status">🎁 今が最もお得です！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/4nvuSXs" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/51a00Not+LL._AC_SY679_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Amazon Fire TV Stick 4K Max</div>
                        <div class="product-price">¥12,980</div>
                        <div class="product-status">🔥 人気ランキング1位！</div>
                    </div>
                </a>
            </div>
        </div>
    </div>
    
    <!-- 全商品のセクション -->
    <div class="container content">
        <h2 class="section-title" id="todayItemsSection">今日の注目買い時アイテム</h2>
        <div style="text-align: center; font-size: 18px; color: #666; margin-bottom: 20px;">
            更新日: {today.strftime('%Y年%m月%d日')}
        </div>
        <div class="product-grid" id="productGrid">
            <!-- ページネーションで表示される商品 (全30個) -->
            <div class="product-card">
                <a href="https://amzn.to/3I6rIdF" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61o7EzoRpBL._AC_SX679_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Apple AirPods Pro (第2世代)</div>
                        <div class="product-price">¥38,192</div>
                        <div class="product-status">🎁 注目のおすすめ商品！</div>
                    </div>
                </a>
            </div>

            <div class="product-card">
                <a href="https://amzn.to/4nbSLTS" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/51Pn+NasrBL._AC_SY300_SX300_QL70_ML2_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Anker Soundcore Liberty 4</div>
                        <div class="product-price">¥12,980</div>
                        <div class="product-status">💡 賢い買い時を見つけよう！</div>
                    </div>
                </a>
            </div>
            
            <div class="product-card">
                <a href="https://amzn.to/4gopMtN" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/710GmYYsbTL._AC_SX522_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Echo Dot (エコードット) 第5世代</div>
                        <div class="product-price">¥7,480</div>
                        <div class="product-status">💰 お得な価格をチェック！</div>
                    </div>
                </a>
            </div>
            
            <div class="product-card">
                <a href="https://amzn.to/4610pdU" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61YEluxj3UL._AC_SX522_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">モバイルバッテリー 【2025新定番・軽量×大容量45800mAh】 モバイルバッテリー 大容量 軽量 小型 最大2.4A出力 ケーブル内蔵 6台同時充電可能 LCD残量表示 タイプc 低電流対応 携帯充電器 iPhone iPad//Android各種スマホ対応 持ち運び便利 PSE認証済み/安全回路保護 旅行/防災対策</div>
                        <div class="product-price">¥2,899</div>
                        <div class="product-status">🔥 割引目玉商品！</div>
                    </div>
                </a>
            </div>

            <div class="product-card">
                <a href="https://amzn.to/4nbSLTS" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/51Pn+NasrBL._AC_SY300_SX300_QL70_ML2_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Anker Soundcore Liberty 4</div>
                        <div class="product-price">¥12,980</div>
                        <div class="product-status">💡 賢い買い時を見つけよう！</div>
                    </div>
                </a>
            </div>
            
            <div class="product-card">
                <a href="https://amzn.to/4nvuSXs" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/51a00Not+LL._AC_SY679_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Amazon Fire TV Stick 4K Max(マックス) | Fire TV Stick史上最もパワフル | ストリーミングメディアプレイヤー</div>
                        <div class="product-price">¥12,980</div>
                        <div class="product-status">📺 手軽に大画面で！</div>
                    </div>
                </a>
            </div>
            
            <div class="product-card">
                <a href="https://amzn.to/46C1Oru" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61ejmoLFURL._AC_SX522_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">パナソニック 電動歯ブラシ ドルツ EW-DP58-P + 歯間フィットブラシ(2本入り) EW0830-X</div>
                        <div class="product-price">¥38,000</div>
                        <div class="product-status">🎁 注目のおすすめ商品！</div>
                    </div>
                </a>
            </div>

            <div class="product-card">
                <a href="https://amzn.to/4gsxmnc" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61SwWE+TevL._AC_SY355_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Amazon Kindle Paperwhite - 目に優しい、かさばらない、大きな画面で読みやすい、防水、色調調節ライト、12週間持続バッテリー、7インチディスプレイ、ブラック、16GB、広告なし</div>
                        <div class="product-price">¥27,980</div>
                        <div class="product-status">💡 賢い買い時を見つけよう！</div>
                    </div>
                </a>
            </div>
            
            <div class="product-card">
                <a href="https://amzn.to/3Imkoui" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61uDYXfqtxL._AC_SX569_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">【Amazon.co.jp限定】 ロジクール MX MASTER3s アドバンスド ワイヤレス マウス 静音 MX2300GRd Logi Bolt Bluetooth Unifying非対応 8000dpi 高速スクロールホイール USB-C 充電式 無線 MX2300 グラファイト 国内正規品 ※Amazon限定の壁紙ダウンロードと特典ロゴステッカー付き</div>
                        <div class="product-price">¥15,210 </div>
                        <div class="product-status">💰 お得な価格をチェック！</div>
                    </div>
                </a>
            </div>

            <div class="product-card">
                <a href="https://amzn.to/46kUSOk" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/71s7HbyqzEL._AC_SY695_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">[Amazonベーシック] キャリーケース スーツケース ハードタイプ ダブルキャスター付き</div>
                        <div class="product-price">¥3,821</div>
                        <div class="product-status">🎁 注目のおすすめ商品！</div>
                    </div>
                </a>
            </div>

            <div class="product-card">
                <a href="https://amzn.to/4mbdSEz" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/71nSaPyH6iL._AC_SY355_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">ソニー(SONY) ULT FIELD 5 Bluetoothスピーカー 迫力の重低音 クリアなサウンド ロングバッテリー25時間 ショルダーストラップ ライティング搭載 防水 防塵 SRS-ULT50 WZ オフホワイト</div>
                        <div class="product-price">¥24,800</div>
                        <div class="product-status">🎁 注目のおすすめ商品！</div>
                    </div>
                </a>
            </div>
            
            <div class="product-card">
                <a href="https://amzn.to/4nP1iwj" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/91ghhfky4LL._AC_SY355_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">MagSafe充電器 ワイヤレス 最大15W</div>
                        <div class="product-price">¥5,192</div>
                        <div class="product-status">💰 お得な価格をチェック！</div>
                    </div>
                </a>
            </div>
            
            <div class="product-card">
                <a href="https://amzn.to/42vw6tr" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/71EGPpNyslL._AC_SX522_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Lifeinnotech アンチグレア MacBook Air 13.6インチ 2025 M4 /M3/M2チップ 用 フィルム ブルーライトカット 保護フィルム マックブックエアー 13インチ 2024 2022 反射低減 指紋防止 抗菌 (2点セット)</div>
                        <div class="product-price">¥1,683</div>
                        <div class="product-status">🔥 注目アイテム！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/4gxpEYP" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/71G3KUCqAoL._AC_SX569_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Dell ノートパソコン Inspiron 14 5440 14インチ Core 5 120U メモリ 16GB SSD 512GB Microsoft Office Home & Business 2024 Windows 11 アイスブルー 2025春モデル</div>
                        <div class="product-price">¥183,303</div>
                        <div class="product-status">💡 賢い買い時を見つけよう！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/47IB4GO" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61mDR99eeUL._AC_SY355_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">ASUS ノートパソコン Vivobook 17 X1704VA 17.3型 インテル Core i5 1334U メモリ16GB SSD 512GB WPS Office搭載 Windows 11 バッテリー駆動 7.9時間 重量 2.1kg Wi-Fi 6E クワイエットブルー X1704VA-I5165W</div>
                        <div class="product-price">¥89,800</div>
                        <div class="product-status">💰 お得な価格をチェック！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/4nzjZ74" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/71argqnNnIL._AC_SX569_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">DOSS SoundBox Pro+ Bluetoothスピーカー 24W 重低音 ワイヤレス ポータブル 小型 ブルートゥース スピーカー【15時間再生/ワイヤレスステレオ対応/ライティング機能/IPX6 防水/マイク内蔵/Aux-in/TFカード対応/お風呂 アオトドア適用】(ブラック)</div>
                        <div class="product-price">¥9,599</div>
                        <div class="product-status">🎁 今が最もお得です！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/3Ib1aYI" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61uDYXfqtxL._AC_SX569_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">【Amazon.co.jp限定】 ロジクール MX MASTER3s アドバンスド ワイヤレス マウス 静音 MX2300GRd Logi Bolt Bluetooth Unifying非対応 8000dpi 高速スクロールホイール USB-C 充電式 無線 MX2300 グラファイト 国内正規品 ※Amazon限定の壁紙ダウンロードと特典ロゴステッカー付き</div>
                        <div class="product-price">¥15,210</div>
                        <div class="product-status">💡 賢い買い時を見つけよう！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/46zVCAd" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61OK3dX6Z2L._AC_SY355_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">AVISTA ゲーミングモニター 27インチ 液晶 QHD Fast IPS 180Hz 1ms ゲームモード(FPS/RTS/MOBA) ブラック DGQ270SCB ドウシシャ</div>
                        <div class="product-price">¥24,980</div>
                        <div class="product-status">💰 お得な価格をチェック！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/3K2vNQD" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/71h9OhYdCdL._AC_SX569_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">イヤホン bluetooth 耳掛け ワイヤレスイヤホン 最大75時間再生 Hi-Fi音質 Bluetooth5.4 瞬時接続 AAC対応【2025年新モデル、完全ワイヤレス、ENCノイズキャンセリングマイク搭載】 ヘッドホン IP7防水 LEDディスプレイ Type-C 急速充電 適用 iPhone/Android ビジネス/WEB会議/通勤/通学/スポーツ</div>
                        <div class="product-price">¥3,149</div>
                        <div class="product-status">🔥 注目アイテム！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/4mjStcC" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/71qQlVaxLqL._AC_SX569_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">【整備済み品】Microsoft サーフェス Surface laptop3 1872 / 第10世代CPU:Core i7 1065G7 / Win11 / MS Office 2019 / 15インチ ノートパソコン/メモリ:32GB / SSD:1000GB / 解像度:2256x1504 / Webカメラ、タッチパネル、顔認証、TypeC/ブラック</div>
                        <div class="product-price">¥98,000</div>
                        <div class="product-status">💡 賢い買い時を見つけよう！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/3KmxYOU" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61kvB-M7S9L._AC_SX569_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">ASUS Chromebook クロームブック CM14 14インチ 日本語キーボード 8GBメモリ 重量1.45kg ゼロタッチ登録対応 カードリーダー搭載 グラヴィティグレー CM1402CM2A-NK0107</div>
                        <div class="product-price">¥45,455</div>
                        <div class="product-status">💰 お得な価格をチェック！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/4me59By" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/71LBrMaYuwL._AC_SX569_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">【Amazon.co.jp限定】Lenovo ノートパソコン パソコン IdeaPad Slim 3 15.6インチ インテル® プロセッサー N100搭載 メモリ8GB SSD512GB MS Office 2024搭載 Windows11 バッテリー駆動12.8時間 重量1.55kg アークティックグレー 82XB00EKJP ノートPC</div>
                        <div class="product-price">¥79,800</div>
                        <div class="product-status">🎁 今が最もお得です！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/463esQ5" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/71-Z6UZ1UzL._AC_SY355_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">HP ノートパソコン Pavilion Aero 13-bg 13.3インチ 軽量990g AMD Ryzen7 8840U 16GBメモリ 1TB SSD Windows 11 Home スカイブルー Copilotキー搭載 AIPC (型番：A17XCPA-AAAA)ン</div>
                        <div class="product-price">¥121,600</div>
                        <div class="product-status">💡 賢い買い時を見つけよう！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/3JYCVxv" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/51t35+ah6yL._AC_SY355_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">ソニー(SONY) ワイヤレスノイズキャンセリングヘッドホン WH-CH720N: ノイズキャンセリング搭載/Bluetooth対応/軽量設計/マイク搭載/外音取り込み搭載/360Reality Audio対応/ブラック WH-CH720N B</div>
                        <div class="product-price">¥17,482</div>
                        <div class="product-status">💰 お得な価格をチェック！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/46i6yRJ" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61XCzP79dAL._AC_SX522_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">NISSYO【日本正規品・ドライヤー 静音】ヘアドライヤー 大風量 2億マイナスイオン 8モード 温冷リズム 冷風調節 42℃ チャイルドモード 軽量 ヘアードライヤー 静電気防止 ドライヤー強風 ヘアケア 美髪 1200W ノズル付き コンパクト ギフト プレゼント グレー</div>
                        <div class="product-price">¥8,980</div>
                        <div class="product-status">🔥 注目アイテム！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/3VAmqdD" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/41IDQPBtDeL._AC_SX385_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">【整備済み品】 任天堂 Nintendo Switch(有機ELモデル) ホワイト HEG-S-KAAAA ニンテンドー スイッチ 180日保証</div>
                        <div class="product-price">¥32,000</div>
                        <div class="product-status">💡 賢い買い時を見つけよう！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/48gdiCd" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61D+DW2eR-L._AC_SY500_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Anker Zolo Power Bank (10000mAh, 35W, Built-In Dual USB-Cケーブル) (モバイルバッテリー 10000mAh 最大35W出力 ケーブル一体型 ディスプレイ搭載) 【PD/PowerIQ搭載/PSE技術基準適合】iPhone 16 / 15 Android iPad その他各種機器 (ブラック)</div>
                        <div class="product-price">¥5,990</div>
                        <div class="product-status">💰 お得な価格をチェック！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/3VcAgTd" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/71M1sL0sUeL._AC_SY355_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">Pixio PX278 WAVE Beige ゲーミングモニター 27インチ 180Hz WQHD ベージュ 2年保証 かわいい</div>
                        <div class="product-price">¥39,980</div>
                        <div class="product-status">🎁 今が最もお得です！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/4n1zdl8" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/81Dfa+BTqQL._AC_SX522_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">SwitchBot スマートロック Ultra 顔認証パッド 指紋認証 - スイッチボット 暗証番号 鍵 スマートキー ドアロック オートロック スマホで操作 交通系ICカード Suica PASMO Alexa/Google Home/Siri対応 遠隔対応 工事不要 取付カンタン 防犯対策 後付け</div>
                        <div class="product-price">¥34,980</div>
                        <div class="product-status">💡 賢い買い時を見つけよう！</div>
                    </div>
                </a>
            </div>
            <div class="product-card">
                <a href="https://amzn.to/4pmmiMj" target="_blank">
                    <img src="https://m.media-amazon.com/images/I/61BrggC5D4L._AC_SX522_.jpg" alt="商品画像">
                    <div class="product-info">
                        <div class="product-name">dreame (ドリーミー)L40s Pro Ultraロボット掃除機 自動ゴミ収集 モップセルフクリーニング 自動洗浄・乾燥機能付き 水拭き両用 強力吸引19,000Pa 100% 絡まり防止デュオブラシ 伸長可能なモップとサイドブラシで隅々まで清掃 AI障害物回避180種以上対応 音声コントロールによる指示 ロボット掃除機</div>
                        <div class="product-price">¥199,800</div>
                        <div class="product-status">💰 お得な価格をチェック！</div>
                    </div>
                </a>
            </div>
        </div>
    </div>
    <div class="pagination-container" id="pagination-container"></div>
    <footer>
        <p>&copy; 2025 カイドキ-ナビ. All Rights Reserved.</p>
        <div class="footer-links">
            <a href="privacy.html">プライバシーポリシー</a>
            <a href="disclaimer.html">免責事項</a>
            <a href="contact.html">お問い合わせ</a>
        </div>
    </footer>
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const productGrid = document.getElementById('productGrid');
            const productCards = Array.from(document.querySelectorAll('#productGrid .product-card'));
            const paginationContainer = document.getElementById('pagination-container');
            const todayItemsSection = document.getElementById('todayItemsSection');

            const productsPerPage = 24;
            let currentPage = 1;
            
            const displayPage = (pageNumber) => {{
                const startIndex = (pageNumber - 1) * productsPerPage;
                const endIndex = startIndex + productsPerPage;

                productCards.forEach((card, index) => {{
                    if (index >= startIndex && index < endIndex) {{
                        card.style.display = 'flex';
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});
            }};

            const setupPagination = () => {{
                const pageCount = Math.ceil(productCards.length / productsPerPage);
                paginationContainer.innerHTML = '';
                
                const maxPageLinks = 7;
                const ellipsis = '<span class="pagination-ellipsis">...</span>';

                if (pageCount <= 1) {{
                    return;
                }}

                // 前へボタン
                const prevLink = document.createElement('a');
                prevLink.href = '#';
                prevLink.innerHTML = '&laquo; 前へ';
                prevLink.classList.add('pagination-link');
                if (currentPage === 1) {{
                    prevLink.classList.add('disabled');
                }} else {{
                    prevLink.addEventListener('click', (e) => {{
                        e.preventDefault();
                        currentPage--;
                        displayPage(currentPage);
                        updatePaginationLinks();
                    }});
                }}
                paginationContainer.appendChild(prevLink);

                // ページリンクの表示ロジック
                let startPage = Math.max(1, currentPage - Math.floor(maxPageLinks / 2));
                let endPage = Math.min(pageCount, startPage + maxPageLinks - 1);
                
                if (endPage - startPage < maxPageLinks - 1) {{
                    startPage = Math.max(1, endPage - maxPageLinks + 1);
                }}

                if (startPage > 1) {{
                    const firstPageLink = document.createElement('a');
                    firstPageLink.href = '#';
                    firstPageLink.textContent = '1';
                    firstPageLink.classList.add('pagination-link');
                    firstPageLink.addEventListener('click', (e) => {{
                        e.preventDefault();
                        currentPage = 1;
                        displayPage(currentPage);
                        updatePaginationLinks();
                    }});
                    paginationContainer.appendChild(firstPageLink);
                    if (startPage > 2) {{
                        paginationContainer.innerHTML += ellipsis;
                    }}
                }}

                for (let i = startPage; i <= endPage; i++) {{
                    const pageLink = document.createElement('a');
                    pageLink.href = '#';
                    pageLink.textContent = i;
                    pageLink.classList.add('pagination-link');
                    if (i === currentPage) {{
                        pageLink.classList.add('active');
                    }}
                    pageLink.addEventListener('click', (e) => {{
                        e.preventDefault();
                        currentPage = i;
                        displayPage(currentPage);
                        updatePaginationLinks();
                        if (todayItemsSection) {{
                            todayItemsSection.scrollIntoView();
                        }}
                    }});
                    paginationContainer.appendChild(pageLink);
                }}
                
                if (endPage < pageCount) {{
                    if (endPage < pageCount - 1) {{
                        paginationContainer.innerHTML += ellipsis;
                    }}
                    const lastPageLink = document.createElement('a');
                    lastPageLink.href = '#';
                    lastPageLink.textContent = pageCount;
                    lastPageLink.classList.add('pagination-link');
                    lastPageLink.addEventListener('click', (e) => {{
                        e.preventDefault();
                        currentPage = pageCount;
                        displayPage(currentPage);
                        updatePaginationLinks();
                    }});
                    paginationContainer.appendChild(lastPageLink);
                }}

                // 次へボタン
                const nextLink = document.createElement('a');
                nextLink.href = '#';
                nextLink.innerHTML = '次へ &raquo;';
                nextLink.classList.add('pagination-link');
                if (currentPage === pageCount) {{
                    nextLink.classList.add('disabled');
                }} else {{
                    nextLink.addEventListener('click', (e) => {{
                        e.preventDefault();
                        currentPage++;
                        displayPage(currentPage);
                        updatePaginationLinks();
                    }});
                }}
                paginationContainer.appendChild(nextLink);

                const updatePaginationLinks = () => {{
                    const currentLinks = document.querySelectorAll('.pagination-link');
                    currentLinks.forEach(link => link.classList.remove('active'));
                    const newLinks = paginationContainer.querySelectorAll('.pagination-link');
                    newLinks.forEach(link => {{
                        if (parseInt(link.textContent) === currentPage) {{
                            link.classList.add('active');
                        }}
                    }});
                    setupPagination();
                    if (todayItemsSection) {{
                        todayItemsSection.scrollIntoView();
                    }}
                }};
            }};
            
            // ページロード時に初期化
            displayPage(currentPage);
            setupPagination();
        }});
    </script>
</body>
</html>
"""

# index.htmlファイルを生成
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("index.htmlファイルが正常に生成されました。")
