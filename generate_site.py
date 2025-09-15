import json

def generate_site():
    """products.jsonを読み込み、HTMLファイルを生成する関数"""

    with open('products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)

    # トップページのHTMLを生成
    index_html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>カイドキ-ナビ | お得な買い時を見つけよう！</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1><a href="index.html">カイドキ-ナビ</a></h1>
            <p>お得な買い時を見つけよう！</p>
        </div>
    </header>

    <div class="search-bar">
        <div class="search-container">
            <input type="text" placeholder="商品名、キーワードで検索...">
            <button class="search-button">🔍</button>
        </div>
    </div>

    <div class="genre-links-container">
        <div class="genre-links">
            <a href="#">パソコン</a>
            <span class="separator">|</span>
            <a href="#">家電</a>
        </div>
    </div>

    <main class="container">
        <div class="ai-recommendation-section">
            <h2 class="ai-section-title">今が買い時！お得な注目アイテム</h2>
            <div class="product-grid">
    """
    
    for product in products:
        index_html_content += f"""
                <a href="{product['page_url']}" class="product-card">
                    <img src="{product['image_url']}" alt="{product['name']}">
                    <div class="product-info">
                        <h3 class="product-name">{product['name']}</h3>
                        <p class="product-price">{product['price']}</p>
                        <p class="product-status">AI分析: {product['ai_analysis']}</p>
                    </div>
                </a>
        """

    index_html_content += """
            </div>
        </div>
    </main>

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
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(index_html_content)
    print("index.html が生成されました。")

    # 個別ページを商品ごとに生成
    for product in products:
        item_html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{product['name']}の買い時情報 | カイドキ-ナビ</title>
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
</head>
<body>

    <header>
        <div class="container">
            <h1><a href="index.html">カイドキ-ナビ</a></h1>
            <p>お得な買い時を見つけよう！</p>
        </div>
    </header>

    <div class="search-bar">
        <div class="search-container">
            <input type="text" placeholder="商品名、キーワードで検索...">
            <button class="search-button">🔍</button>
        </div>
    </div>

    <div class="genre-links-container">
        <div class="genre-links">
            <a href="#">パソコン</a>
            <span class="separator">|</span>
            <a href="#">家電</a>
        </div>
    </div>

    <main class="container">
        <div class="item-detail">
            <div class="item-image">
                <img src="{product['image_url']}" alt="{product['name']}">
            </div>

            <div class="item-info">
                <h1 class="item-name">{product['name']}</h1>
                <p class="item-category">カテゴリ：{product['category']}</p>
                <div class="price-section">
                    <p class="current-price">現在の価格：<span>{product['price']}</span></p>
                    <p class="price-status">AI分析：**{product['ai_analysis']}**</p>
                </div>

                <div class="affiliate-links">
                    <p class="links-title">最安値ショップをチェック！</p>
                    <a href="{product['amazon_url']}" class="shop-link" target="_blank">Amazonで見る</a>
                </div>

                <div class="item-description">
                    <h2>商品説明</h2>
                    <p>{product['description']}</p>
                </div>
            </div>
        </div>
    </main>

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
        with open(product['page_url'], 'w', encoding='utf-8') as f:
            f.write(item_html_content)
        print(f"{product['page_url']} が生成されました。")

if __name__ == "__main__":
    generate_site()
    print("サイトのファイル生成が完了しました！")
