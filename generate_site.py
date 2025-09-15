import json
import math
import os
import shutil

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 24

def generate_site():
    """products.jsonを読み込み、HTMLファイルを生成する関数"""

    # 既存のHTMLファイルを削除
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.html') and not file in ['privacy.html', 'disclaimer.html', 'contact.html']:
                os.remove(os.path.join(root, file))
    
    # カテゴリフォルダを削除
    if os.path.exists('category'):
        shutil.rmtree('category')

    with open('products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)

    # カテゴリー情報を収集
    categories = {}
    for product in products:
        main_cat = product['category']['main']
        sub_cat = product['category']['sub']

        if main_cat not in categories:
            categories[main_cat] = []
        if sub_cat not in categories[main_cat]:
            categories[main_cat].append(sub_cat)
    
    # メインカテゴリーを五十音順にソート
    sorted_main_cats = sorted(categories.keys())

    # ヘッダーとフッターを生成する関数
    def generate_header_footer(current_path, sub_cat_links=None):
        base_path = os.path.relpath('.', start=os.path.dirname(current_path))
        
        main_links_html = ""
        for mc_link in sorted_main_cats:
            main_links_html += f'<a href="{base_path}/category/{mc_link}/index.html">{mc_link}</a><span class="separator">|</span>'
        
        header_html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>カイドキ-ナビ | お得な買い時を見つけよう！</title>
    <link rel="stylesheet" href="{base_path}/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
</head>
<body>
    <header>
        <div class="container">
            <h1><a href="{base_path}/index.html">カイドキ-ナビ</a></h1>
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
            {main_links_html}
        </div>
    </div>
"""
        
        # サブカテゴリーリンクのセクション
        sub_cat_links_html = ""
        if sub_cat_links:
            sub_cat_links_html += '<div class="genre-links sub-genre-links">'
            for sub_cat_link in sorted(sub_cat_links):
                sub_cat_links_html += f'<a href="{sub_cat_link.replace(" ", "")}.html">{sub_cat_link}</a><span class="separator">|</span>'
            sub_cat_links_html += '</div>'
            
        header_html += f"""
    <main class="container">
        <div class="ai-recommendation-section">
            <h2 class="ai-section-title">今が買い時！お得な注目アイテム</h2>
            {sub_cat_links_html}
            <div class="product-grid">
            """

        footer_html = f"""
            </div>
        </div>
    </main>
    <footer>
        <p>&copy; 2025 カイドキ-ナビ. All Rights Reserved.</p>
        <div class="footer-links">
            <a href="{base_path}/privacy.html">プライバシーポリシー</a>
            <a href="{base_path}/disclaimer.html">免責事項</a>
            <a href="{base_path}/contact.html">お問い合わせ</a>
        </div>
    </footer>
</body>
</html>
        """
        return header_html, footer_html

    # メインカテゴリーごとのページを生成
    for main_cat, sub_cats in categories.items():
        main_cat_dir = f"category/{main_cat}"
        os.makedirs(main_cat_dir, exist_ok=True)
        
        # メインカテゴリーのindexページを生成 (サブカテゴリーリンクあり)
        main_cat_products = [p for p in products if p['category']['main'] == main_cat]
        page_path = os.path.join(main_cat_dir, "index.html")
        header, footer = generate_header_footer(page_path, sub_cat_links=sub_cats)
        
        products_html = ""
        for product in main_cat_products:
            products_html += f"""
                    <a href="../../{product['page_url']}" class="product-card">
                        <img src="../../{product['image_url']}" alt="{product['name']}">
                        <div class="product-info">
                            <h3 class="product-name">{product['name']}</h3>
                            <p class="product-price">{product['price']}</p>
                            <p class="product-status">AI分析: {product['ai_analysis']}</p>
                        </div>
                    </a>
            """
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + products_html + footer)
        print(f"{page_path} が生成されました。")
        
        # サブカテゴリーごとのページを生成 (サブカテゴリーリンクなし)
        for sub_cat in sub_cats:
            sub_cat_products = [p for p in products if p['category']['sub'] == sub_cat]
            sub_cat_file_name = f"{sub_cat.replace(' ', '')}.html"
            page_path = os.path.join(main_cat_dir, sub_cat_file_name)
            header, footer = generate_header_footer(page_path)
            
            products_html = ""
            for product in sub_cat_products:
                products_html += f"""
                    <a href="../../{product['page_url']}" class="product-card">
                        <img src="../../{product['image_url']}" alt="{product['name']}">
                        <div class="product-info">
                            <h3 class="product-name">{product['name']}</h3>
                            <p class="product-price">{product['price']}</p>
                            <p class="product-status">AI分析: {product['ai_analysis']}</p>
                        </div>
                    </a>
                """
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(header + products_html + footer)
            print(f"{page_path} が生成されました。")

    # トップページのHTMLを生成
    # ----------------------------------------------------
    top_page_path = 'index.html'
    header, footer = generate_header_footer(top_page_path)
    top_page_products = products[:PRODUCTS_PER_PAGE]
    products_html = ""
    for product in top_page_products:
        products_html += f"""
                <a href="{product['page_url']}" class="product-card">
                    <img src="{product['image_url']}" alt="{product['name']}">
                    <div class="product-info">
                        <h3 class="product-name">{product['name']}</h3>
                        <p class="product-price">{product['price']}</p>
                        <p class="product-status">AI分析: {product['ai_analysis']}</p>
                    </div>
                </a>
        """
    with open(top_page_path, 'w', encoding='utf-8') as f:
        f.write(header + products_html + footer)
    print("index.html が生成されました。")

    # 個別ページを商品ごとに生成
    # ----------------------------------------------------
    for product in products:
        page_path = product['page_url']
        header, footer = generate_header_footer(page_path)
        
        item_html_content = f"""
    <main class="container">
        <div class="item-detail">
            <div class="item-image">
                <img src="{product['image_url']}" alt="{product['name']}">
            </div>

            <div class="item-info">
                <h1 class="item-name">{product['name']}</h1>
                <p class="item-category">カテゴリ：<a href="category/{product['category']['main']}/index.html">{product['category']['main']}</a> &gt; <a href="category/{product['category']['main']}/{product['category']['sub'].replace(' ', '')}.html">{product['category']['sub']}</a></p>
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
        """
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + item_html_content + footer)
        print(f"{page_path} が生成されました。")

    print("サイトのファイル生成が完了しました！")

if __name__ == "__main__":
    generate_site()
