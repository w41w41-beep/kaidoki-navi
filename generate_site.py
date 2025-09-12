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
    <title>カイドキ-ナビ - 賢い買い時を見つけよう！</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f7f6; color: #333; }}
        .container {{ max-width: 960px; margin: auto; padding: 20px; }}
        header {{ background-color: #fff; border-bottom: 1px solid #ddd; padding: 20px; text-align: center; }}
        header h1 {{ margin: 0; color: #007bff; }}
        .search-bar {{ padding: 20px; text-align: center; background-color: #e9ecef; }}
        .search-bar input {{ width: 80%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }}
        .content {{ padding: 20px 0; }}
        .section-title {{ font-size: 24px; font-weight: bold; margin-bottom: 20px; text-align: center; }}
        
        /* 商品のレイアウトをFlexboxで修正 */
        .product-grid {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }}

        .product-card {{ 
            flex: 1 1 280px; /* カードが横に並ぶように設定 */
            background-color: #fff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: transform 0.2s; 
        }}
        .product-card:hover {{ transform: translateY(-5px); }}
        .product-card img {{ width: 100%; height: auto; display: block; }}
        .product-info {{ padding: 15px; }}
        .product-name {{ font-size: 18px; font-weight: bold; margin-bottom: 5px; }}
        .product-price {{ color: #dc3545; font-size: 20px; font-weight: bold; margin-bottom: 10px; }}
        .product-status {{ font-size: 14px; color: #28a745; font-weight: bold; }}
        
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

        footer {{ text-align: center; padding: 20px; border-top: 1px solid #ddd; background-color: #fff; margin-top: 20px; }}
        .footer-links {{ display: flex; justify-content: center; gap: 20px; margin-top: 10px; }}
        .footer-links a {{ color: #007bff; text-decoration: none; }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>カイドキ-ナビ</h1>
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

    <div class="container content">
        <h2 class="section-title">今日の注目買い時アイテム</h2>
        <div style="text-align: center; font-size: 18px; color: #666; margin-bottom: 20px;">
            更新日: {today.strftime('%Y年%m月%d日')}
        </div>
        <div class="product-grid">
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
        </div>
    </div>
    <footer>
        <p>&copy; 2025 カイドキ-ナビ. All Rights Reserved.</p>
        <div class="footer-links">
            <a href="privacy.html">プライバシーポリシー</a>
            <a href="disclaimer.html">免責事項</a>
            <a href="contact.html">お問い合わせ</a>
        </div>
    </footer>
</body>
</html>
"""

# index.htmlファイルを生成
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("index.htmlファイルが正常に生成されました。")
