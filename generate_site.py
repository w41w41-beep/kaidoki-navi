import json
import math

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 24

def generate_site():
    """products.jsonを読み込み、HTMLファイルを生成する関数"""

    with open('products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)

    # カテゴリー情報を収集
    categories = {}
    for product in products:
        main_cat = product['category']['main']
        if main_cat not in categories:
            categories[main_cat] = []
        
        if 'sub' in product['category'] and product['category']['sub'] not in categories[main_cat]:
            categories[main_cat].append(product['category']['sub'])

    # トップページのHTMLを生成
    # ----------------------------------------------------
    total_products = len(products)
    total_pages = math.ceil(total_products / PRODUCTS_PER_PAGE)
    
    # ページネーションのHTMLを生成
    pagination_html = ""
    if total_pages > 1:
        pagination_html += '<div class="pagination-container">\n'
        for i in range(1, total_pages + 1):
            is_active = " active" if i == 1 else ""
            pagination_html += f'    <a href="page-{i}.html" class="pagination-link{is_active}">{i}</a>\n'
        pagination_html += '</div>\n'

    # カテゴリーリンクのHTMLを生成
    category_links_html = ""
    for main_cat, sub_cats in categories.items():
        category_links_html += f'<a href="#">{main_cat}</a>'
        if sub_cats:
            category_links_html += '<span class="separator">|</span>'
        # ここはまだサブカテゴリーのリンクがありませんが、将来的には追加できます

    index_html_content = f"""
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
            {category_links_html}
        </div>
    </div>

    <main class="container">
        <div class="ai-recommendation-section">
            <h2 class="ai-section-title">今が買い時！お得な注目アイテム</h2>
            <div class="product-grid">
    """
    
    # トップページに表示する最初の24件の商品を抽出
    top_page_products = products[:PRODUCTS_PER_PAGE]
    
    for product in top_page_products:
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

    index_html_content += f"""
            </div>
        </div>
        {pagination_html}
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
    # ----------------------------------------------------
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
            {category_links_html}
        </div>
    </div>

    <main class="container">
        <div class="item-detail">
            <div class="item-image">
                <img src="{product['image_url']}" alt="{product['name']}">
            </div>

            <div class="item-info">
                <h1 class="item-name">{product['name']}</h1>
                <p class="item-category">カテゴリ：{product['category']['main']} &gt; {product['category']['sub']}</p>
                <div class="price-section">
                    <p class="current-price">現在の価格：<span>{product['price']}</span></p>
                    <p class="price-status">AI分析：**{product['ai_analysis']}**</p>
                </div>

                <div class="affiliate-links">
                    <p class="links-title">最安値ショップをチェック！</p>
                    <a href="{product.get('amazon_url', '#')}" class="shop-link" target="_blank">Amazonで見る</a>
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

    print("サイトのファイル生成が完了しました！")

if __name__ == "__main__":
    generate_site()
