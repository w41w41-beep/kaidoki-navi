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
        .product-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }}
        .product-card {{ background-color: #fff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: transform 0.2s; }}
        .product-card:hover {{ transform: translateY(-5px); }}
        .product-card img {{ width: 100%; height: auto; display: block; }}
        .product-info {{ padding: 15px; }}
        .product-name {{ font-size: 18px; font-weight: bold; margin-bottom: 5px; }}
        .product-price {{ color: #dc3545; font-size: 20px; font-weight: bold; margin-bottom: 10px; }}
        .product-status {{ font-size: 14px; color: #28a745; font-weight: bold; }}
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

    <div class="container content">
        <h2 class="section-title">今日の注目買い時アイテム</h2>
        <div style="text-align: center; font-size: 18px; color: #666; margin-bottom: 20px;">
            更新日: {today.strftime('%Y年%m月%d日')}
        </div>
        <div class="product-grid">
            <div class="product-card">
                <img src="https://via.placeholder.com/300x200" alt="商品画像">
                <div class="product-info">
                    <div class="product-name">ダミー商品A</div>
                    <div class="product-price">¥42,800</div>
                    <div class="product-status">🔥過去30日で最安値！</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# index.htmlファイルを生成
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("index.htmlファイルが正常に生成されました。")
