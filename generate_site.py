import json
import math
import os
import shutil

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 24

def generate_site():
    """products.jsonを読み込み、HTMLファイルを生成する関数"""

    # 既存のHTMLファイルとディレクトリを削除
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.html') and not file in ['privacy.html', 'disclaimer.html', 'contact.html']:
                os.remove(os.path.join(root, file))
    
    if os.path.exists('category'):
        shutil.rmtree('category')
    
    if os.path.exists('pages'):
        shutil.rmtree('pages')

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
    def generate_header_footer(current_path, sub_cat_links=None, page_title="お得な買い時を見つけよう！"):
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
    <title>カイドキ-ナビ | {page_title}</title>
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
    <div class="sub-genre-links-container">
        {sub_cat_links_html}
    </div>
"""
        footer_html = f"""
    </main>
    <footer>
        <p>&copy; 2025 カイドキ-ナビ. All Rights Reserved.</p>
        <div class="footer-links">
            <a href="{base_path}/privacy.html">プライバシーポリシー</a>
            <a href="{base_path}/disclaimer.html">免責事項</a>
            <a href="{base_path}/contact.html">お問い合わせ</a>
        </div>
    </footer>
    <script src="{base_path}/script.js"></script>
</body>
</html>
        """
        return header_html, footer_html

    # 静的ページを生成する関数
    def generate_static_page(file_name, title, content_html):
        page_path = file_name
        header, footer = generate_header_footer(page_path, page_title=title)
        
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + content_html + footer)
        print(f"{page_path} が生成されました。")


    # メインカテゴリーごとのページを生成
    for main_cat, sub_cats in categories.items():
        main_cat_products = [p for p in products if p['category']['main'] == main_cat]
        page_path = f"category/{main_cat}/index.html"
        
        # ディレクトリを作成
        os.makedirs(os.path.dirname(page_path), exist_ok=True)
        
        header, footer = generate_header_footer(page_path, sub_cat_links=sub_cats, page_title=f"{main_cat}の商品一覧")
        
        main_content_html = f"""
    <main class="container">
        <div class="ai-recommendation-section">
            <h2 class="ai-section-title">{main_cat}の商品一覧</h2>
            <div class="product-grid">
            """
        
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
            f.write(header + main_content_html + products_html + footer)
        print(f"category/{main_cat}/index.html が生成されました。")
        
        # サブカテゴリーごとのページを生成 (サブカテゴリーリンクなし)
        for sub_cat in sub_cats:
            sub_cat_products = [p for p in products if p['category']['sub'] == sub_cat]
            sub_cat_file_name = f"{sub_cat.replace(' ', '')}.html"
            page_path = f"category/{main_cat}/{sub_cat_file_name}"
            header, footer = generate_header_footer(page_path, page_title=f"{sub_cat}の商品一覧")
            
            main_content_html = f"""
    <main class="container">
        <div class="ai-recommendation-section">
            <h2 class="ai-section-title">{sub_cat}の商品一覧</h2>
            <div class="product-grid">
            """
            
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
                f.write(header + main_content_html + products_html + footer)
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
        f.write(header + '<main class="container"><div class="ai-recommendation-section"><h2 class="ai-section-title">今が買い時！お得な注目アイテム</h2><div class="product-grid">' + products_html + '</div></div></main>' + footer)
    print("index.html が生成されました。")

    # 個別ページを商品ごとに生成
    # ----------------------------------------------------
    for product in products:
        page_path = product['page_url']
        
        # 親ディレクトリが存在しない場合は作成
        dir_name = os.path.dirname(page_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        header, footer = generate_header_footer(page_path, page_title=f"{product['name']}の買い時情報")
        
        specs_html = ""
        if "specs" in product:
            specs_html = f"""
                <div class="item-specs">
                    <h2>製品仕様・スペック</h2>
                    <p>{product['specs']}</p>
                </div>
            """
        
        # 購入ボタンをECサイトの指定に基づいて生成するロジック
        purchase_button_html = ""
        main_ec_site = product.get("main_ec_site")
        
        if main_ec_site == "Amazon" and "amazon_url" in product:
            purchase_button_html = f'<a href="{product["amazon_url"]}" class="purchase-button" target="_blank">Amazonで購入する</a>'
        elif main_ec_site == "楽天" and "rakuten_url" in product:
            purchase_button_html = f'<a href="{product["rakuten_url"]}" class="purchase-button" target="_blank">楽天市場で購入する</a>'
        elif main_ec_site == "Yahoo!" and "yahoo_url" in product:
            purchase_button_html = f'<a href="{product["yahoo_url"]}" class="purchase-button" target="_blank">Yahoo!ショッピングで購入する</a>'
        elif main_ec_site == "Yahoo" and "yahoo_url" in product:
            purchase_button_html = f'<a href="{product["yahoo_url"]}" class="purchase-button" target="_blank">Yahoo!ショッピングで購入する</a>'
        
        affiliate_links_html = f"""
            <div class="affiliate-links">
                <p class="links-title">最安値ショップをチェック！</p>
                <div class="shop-buttons">
                    {f'<a href="{product["amazon_url"]}" class="shop-link" target="_blank">Amazonで見る</a>' if "amazon_url" in product else ''}
                    {f'<a href="{product["rakuten_url"]}" class="shop-link" target="_blank">楽天市場で見る</a>' if "rakuten_url" in product else ''}
                    {f'<a href="{product["yahoo_url"]}" class="shop-link" target="_blank">Yahoo!ショッピングで見る</a>' if "yahoo_url" in product else ''}
                </div>
            </div>
        """
        
        item_html_content = f"""
    <main class="container">
        <div class="item-detail">
            <div class="item-image">
                <img src="../../{product['image_url']}" alt="{product['name']}">
            </div>

            <div class="item-info">
                <h1 class="item-name">{product['name']}</h1>
                <p class="item-category">カテゴリ：<a href="category/{product['category']['main']}/index.html">{product['category']['main']}</a> &gt; <a href="category/{product['category']['main']}/{product['category']['sub'].replace(' ', '')}.html">{product['category']['sub']}</a></p>
                <div class="price-section">
                    <p class="current-price">現在の価格：<span>{product['price']}</span></p>
                </div>
                <div class="ai-recommendation-section">
                    <p class="price-status">AI分析：**{product['ai_analysis']}**</p>
                    {purchase_button_html}
                </div>
                {affiliate_links_html}

                <div class="item-description">
                    <h2>商品説明</h2>
                    <p>{product['description']}</p>
                </div>
                {specs_html}
            </div>
        </div>
    </main>
        """
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + item_html_content + footer)
        print(f"{page_path} が生成されました。")
    
    # 静的ページを生成
    # ----------------------------------------------------
    # お問い合わせページ
    contact_content = """
    <main class="container">
        <div class="static-content">
            <h1>お問い合わせ</h1>
            <p>ご質問やご要望がございましたら、以下のメールアドレスまでご連絡ください。</p>
            <p>メールアドレス: your-email@example.com</p>
        </div>
    </main>
    """
    generate_static_page("contact.html", "お問い合わせ", contact_content)

    # プライバシーポリシーページ
    privacy_content = """
    <main class="container">
        <div class="static-content">
            <h1>プライバシーポリシー</h1>
            <p>このサイトはGoogleアナリティクスを使用しています。</p>
            <p>収集される情報やその利用目的については、Googleのプライバシーポリシーをご確認ください。</p>
        </div>
    </main>
    """
    generate_static_page("privacy.html", "プライバシーポリシー", privacy_content)

    # 免責事項ページ
    disclaimer_content = """
    <main class="container">
        <div class="static-content">
            <h1>免責事項</h1>
            <p>本サイトに掲載されている情報は、正確性や完全性を保証するものではありません。</p>
            <p>アフィリエイトリンクを通じて購入された商品に関するトラブルについては、当サイトは一切の責任を負いません。</p>
        </div>
    </main>
    """
    generate_static_page("disclaimer.html", "免責事項", disclaimer_content)

    print("サイトのファイル生成が完了しました！")

if __name__ == "__main__":
    generate_site()
