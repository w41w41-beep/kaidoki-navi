import json
import math
import os

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
        sub_cat = product['category']['sub']

        if main_cat not in categories:
            categories[main_cat] = []
        if sub_cat not in categories[main_cat]:
            categories[main_cat].append(sub_cat)

    # メインカテゴリーごとのページを生成
    for main_cat, sub_cats in categories.items():
        main_cat_dir = f"category/{main_cat}"
        os.makedirs(main_cat_dir, exist_ok=True)
        
        main_cat_products = [p for p in products if p['category']['main'] == main_cat]
        
        # サブカテゴリーリンクのHTMLを生成
        sub_cat_links_html = ""
        for sub_cat_link in sub_cats:
            sub_cat_links_html += f'<a href="{sub_cat_link.replace(" ", "")}.html" class="sub-category-link">{sub_cat_link}</a>'
            
        main_cat_html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{main_cat}の商品一覧 | カイドキ-ナビ</title>
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1><a href="../index.html">カイドキ-ナビ</a></h1>
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
    """
    
        main_links_html = ""
        for mc_link in categories:
            link_path = f"../category/{mc_link}/index.html"
            main_links_html += f'<a href="{link_path}">{mc_link}</a><span class="separator">|</span>'
        
        main_cat_html_content += f"""
            {main_links_html}
        </div>
    </div>
    
    <main class="container">
        <h2 class="ai-section-title">{main_cat}の商品一覧</h2>
        <div class="sub-category-links">
            {sub_cat_links_html}
        </div>
        <div class="product-grid">
    """
    
        for product in main_cat_products:
            main_cat_html_content += f"""
                <a href="../{product['page_url']}" class="product-card">
                    <img src="../{product['image_url']}" alt="{product['name']}">
                    <div class="product-info">
                        <h3 class="product-name">{product['name']}</h3>
                        <p class="product-price">{product['price']}</p>
                        <p class="product-status">AI分析: {product['ai_analysis']}</p>
                    </div>
                </a>
            """

        main_cat_html_content += """
        </div>
    </main>
    <footer>
        <p>&copy; 2025 カイドキ-ナビ. All Rights Reserved.</p>
        <div class="footer-links">
            <a href="../privacy.html">プライバシーポリシー</a>
            <a href="../disclaimer.html">免責事項</a>
            <a href="../contact.html">お問い合わせ</a>
        </div>
    </footer>
</body>
</html>
        """
        with open(os.path.join(main_cat_dir, "index.html"), 'w', encoding='utf-8') as f:
            f.write(main_cat_html_content)
        print(f"category/{main_cat}/index.html が生成されました。")
        
        # サブカテゴリーごとのページを生成
        for sub_cat in sub_cats:
            sub_cat_products = [p for p in products if p['category']['sub'] == sub_cat]
            
            sub_cat_html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{sub_cat}の商品一覧 | カイドキ-ナビ</title>
    <link rel="stylesheet" href="../../style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1><a href="../../index.html">カイドキ-ナビ</a></h1>
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
    """
            sub_links_html = ""
            for mc_link in categories:
                sub_links_html += f'<a href="../../category/{mc_link}/index.html">{mc_link}</a><span class="separator">|</span>'
            
            sub_cat_html_content += f"""
            {sub_links_html}
        </div>
    </div>
    
    <main class="container">
        <h2 class="ai-section-title">{sub_cat}の商品一覧</h2>
        <div class="product-grid">
            """
            for product in sub_cat_products:
                sub_cat_html_content += f"""
                    <a href="../../{product['page_url']}" class="product-card">
                        <img src="../../{product['image_url']}" alt="{product['name']}">
                        <div class="product-info">
                            <h3 class="product-name">{product['name']}</h3>
                            <p class="product-price">{product['price']}</p>
                            <p class="product-status">AI分析: {product['ai_analysis']}</p>
                        </div>
                    </a>
                """
            sub_cat_html_content += """
        </div>
    </main>
    <footer>
        <p>&copy; 2025 カイドキ-ナビ. All Rights Reserved.</p>
        <div class="footer-links">
            <a href="../../privacy.html">プライバシーポリシー</a>
            <a href="../../disclaimer.html">免責事項</a>
            <a href="../../contact.html">お問い合わせ</a>
        </div>
    </footer>
</body>
</html>
            """
            file_name = f"{main_cat_dir}/{sub_cat.replace(' ', '')}.html"
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(sub_cat_html_content)
            print(f"{file_name} が生成されました。")


    # トップページのHTMLを生成
    # ----------------------------------------------------
    total_products = len(products)
    total_pages = math.ceil(total_products / PRODUCTS_PER_PAGE)
    
    pagination_html = ""
    if total_pages > 1:
        pagination_html += '<div class="pagination-container">\n'
        for i in range(1, total_pages + 1):
            is_active = " active" if i == 1 else ""
            pagination_html += f'    <a href="page-{i}.html" class="pagination-link{is_active}">{i}</a>\n'
        pagination_html += '</div>\n'
    
    category_links_html = ""
    for main_cat in categories:
        category_links_html += f'<a href="category/{main_cat}/index.html">{main_cat}</a><span class="separator">|</span>'
        
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
