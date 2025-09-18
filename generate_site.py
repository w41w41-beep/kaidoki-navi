import json
import math
import os
import shutil
from datetime import date
import requests

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 24

def fetch_rakuten_items():
    """楽天APIから複数のカテゴリで商品データを取得する関数"""
    app_id = os.environ.get('RAKUTEN_API_KEY')
    if not app_id:
        print("RAKUTEN_API_KEYが設定されていません。")
        return []

    # 検索したいキーワードのリスト
    keywords = ['パソコン', '家電']
    all_products = []

    for keyword in keywords:
        # 各キーワードでAPIを呼び出す（それぞれ10件取得）
        url = f"https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706?applicationId={app_id}&keyword={keyword}&format=json&sort=-reviewCount&hits=10"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            items = data.get('Items', [])
            
            for item in items:
                item_data = item['Item']
                
                # カテゴリを正しく設定
                main_cat = keyword
                
                all_products.append({
                    "id": item_data['itemCode'],
                    "name": item_data['itemName'],
                    "price": f"{int(item_data['itemPrice']):,}",
                    "image_url": item_data['mediumImageUrls'][0]['imageUrl'],
                    "rakuten_url": item_data['itemUrl'],
                    "page_url": f"pages/{item_data['itemCode']}.html",
                    "category": {
                        "main": main_cat,
                        "sub": item_data['genreName']
                    },
                    "ai_analysis": "AIによる価格分析は近日公開！",
                    "date": date.today().isoformat()
                })
        except requests.exceptions.RequestException as e:
            print(f"楽天APIへのリクエスト中にエラーが発生しました: {e}")

    # 合計20件までを返す
    return all_products[:20]

def update_products_json(new_products):
    """新しい商品データを既存のproducts.jsonに統合・更新する関数"""
    try:
        if os.path.exists('products.json'):
            with open('products.json', 'r', encoding='utf-8') as f:
                existing_products = json.load(f)
        else:
            existing_products = []
    except json.JSONDecodeError:
        print("products.jsonが破損しているため、新規作成します。")
        existing_products = []

    updated_products = {p['id']: p for p in existing_products}
    for new_product in new_products:
        updated_products[new_product['id']] = new_product
    
    final_products = list(updated_products.values())
    
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(final_products, f, ensure_ascii=False, indent=4)
    
    print(f"products.jsonが更新されました。現在 {len(final_products)} 個の商品を追跡中です。")
    return final_products

def generate_site(products):
    """products.jsonを読み込み、HTMLファイルを生成する関数"""
    today = date.today().isoformat()
    for product in products:
        if 'date' not in product:
            product['date'] = today
    products.sort(key=lambda p: p['date'], reverse=True)
    categories = {}
    for product in products:
        main_cat = product['category']['main']
        sub_cat = product['category']['sub']
        if main_cat not in categories:
            categories[main_cat] = []
        if sub_cat not in categories[main_cat]:
            categories[main_cat].append(sub_cat)
    sorted_main_cats = sorted(categories.keys())

    def generate_header_footer(current_path, sub_cat_links=None, page_title="お得な買い時を見つけよう！"):
        if "pages" in current_path:
            base_path = ".."
        elif "category" in current_path:
            base_path = "../.."
        elif "tags" in current_path:
            base_path = ".."
        else:
            base_path = "."
        main_links_html = f'<a href="{base_path}/tags/index.html">タグから探す</a><span class="separator">|</span>'
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
    <meta name="google-site-verification" content="OmUuOjcxi7HXBKe47sd0WPbzCfbCOFbPj_iueHBk2qo" />
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

    def generate_static_page(file_name, title, content_html):
        page_path = file_name
        header, footer = generate_header_footer(page_path, page_title=title)
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + content_html + footer)
        print(f"{page_path} が生成されました。")
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.html') and not file in ['privacy.html', 'disclaimer.html', 'contact.html']:
                os.remove(os.path.join(root, file))
    if os.path.exists('category'):
        shutil.rmtree('category')
    if os.path.exists('pages'):
        shutil.rmtree('pages')
    if os.path.exists('tags'):
        shutil.rmtree('tags')

    for main_cat, sub_cats in categories.items():
        main_cat_products = [p for p in products if p['category']['main'] == main_cat]
        page_path = f"category/{main_cat}/index.html"
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
            link_path = os.path.relpath(product['page_url'], os.path.dirname(page_path))
            products_html += f"""
<a href="{link_path}" class="product-card">
    <img src="{product['image_url']}" alt="{product['name']}">
    <div class="product-info">
        <h3 class="product-name">{product['name'][:20] + '...' if len(product['name']) > 20 else product['name']}</h3>
        <p class="product-price">{product['price']}</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product['ai_analysis']}</div>
    </div>
</a>
            """
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + products_html + footer)
        print(f"category/{main_cat}/index.html が生成されました。")
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
                link_path = os.path.relpath(product['page_url'], os.path.dirname(page_path))
                products_html += f"""
<a href="{link_path}" class="product-card">
    <img src="{product['image_url']}" alt="{product['name']}">
    <div class="product-info">
        <h3 class="product-name">{product['name'][:20] + '...' if len(product['name']) > 20 else product['name']}</h3>
        <p class="product-price">{product['price']}</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product['ai_analysis']}</div>
    </div>
</a>
                """
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(header + main_content_html + products_html + footer)
            print(f"{page_path} が生成されました。")

    total_pages = math.ceil(len(products) / PRODUCTS_PER_PAGE)
    for i in range(total_pages):
        start_index = i * PRODUCTS_PER_PAGE
        end_index = start_index + PRODUCTS_PER_PAGE
        paginated_products = products[start_index:end_index]
        page_num = i + 1
        page_path = 'index.html' if page_num == 1 else f'pages/page{page_num}.html'
        if page_num > 1:
            os.makedirs(os.path.dirname(page_path), exist_ok=True)
        header, footer = generate_header_footer(page_path)
        products_html = ""
        for product in paginated_products:
            link_path = os.path.relpath(product['page_url'], os.path.dirname(page_path))
            products_html += f"""
<a href="{link_path}" class="product-card">
    <img src="{product['image_url']}" alt="{product['name']}">
    <div class="product-info">
        <h3 class="product-name">{product['name'][:20] + '...' if len(product['name']) > 20 else product['name']}</h3>
        <p class="product-price">{product['price']}</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product['ai_analysis']}</div>
    </div>
</a>
            """
        pagination_html = ""
        if total_pages > 1:
            pagination_html += '<div class="pagination">'
            if page_num > 1:
                prev_link = 'index.html' if page_num == 2 else f'pages/page{page_num - 1}.html'
                pagination_html += f'<a href="{os.path.relpath(prev_link, os.path.dirname(page_path))}" class="prev">前へ</a>'
            for p in range(1, total_pages + 1):
                page_link = 'index.html' if p == 1 else f'pages/page{p}.html'
                active_class = 'active' if p == page_num else ''
                pagination_html += f'<a href="{os.path.relpath(page_link, os.path.dirname(page_path))}" class="{active_class}">{p}</a>'
            if page_num < total_pages:
                next_link = f'pages/page{page_num + 1}.html'
                pagination_html += f'<a href="{os.path.relpath(next_link, os.path.dirname(page_path))}" class="next">次へ</a>'
            pagination_html += '</div>'
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + '<main class="container"><div class="ai-recommendation-section"><h2 class="ai-section-title">今が買い時！お得な注目アイテム</h2><div class="product-grid">' + products_html + '</div>' + pagination_html + '</main>' + footer)
        print(f"{page_path} が生成されました。")

    for product in products:
        page_path = product['page_url']
        dir_name = os.path.dirname(page_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        header, footer = generate_header_footer(page_path, page_title=f"{product['name']}の買い時情報")
        ai_analysis_block_html = f"""
            <div class="ai-analysis-block">
                <div class="ai-analysis-text">
                    <h2>AIによる買い時分析</h2>
                    <p>価格推移グラフとAIによる詳細分析を近日公開！乞うご期待！</p>
                </div>
            </div>
        """
        specs_html = ""
        if "specs" in product:
            specs_html = f"""
                <div class="item-specs">
                    <h2>製品仕様・スペック</h2>
                    <p>{product['specs']}</p>
                </div>
            """
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
            <div class="lowest-price-section">
                <p class="lowest-price-label">最安値ショップをチェック！</p>
                <div class="lowest-price-buttons">
                    {f'<a href="{product["amazon_url"]}" class="btn shop-link" target="_blank">Amazonで見る</a>' if "amazon_url" in product else ''}
                    {f'<a href="{product["rakuten_url"]}" class="btn shop-link" target="_blank">楽天市場で見る</a>' if "rakuten_url" in product else ''}
                    {f'<a href="{product["yahoo_url"]}" class="btn shop-link" target="_blank">Yahoo!ショッピングで見る</a>' if "yahoo_url" in product else ''}
                </div>
            </div>
        """
        item_html_content = f"""
<main class="container">
    <div class="product-detail">
        <div class="item-detail">
            <div class="item-image">
                <img src="{product['image_url']}" alt="{product['name']}" class="main-product-image">
            </div>
            <div class="item-info">
                <h1 class="item-name">{product['name']}</h1>
                <p class="item-category">カテゴリ：<a href="{os.path.relpath('category/' + product['category']['main'] + '/index.html', os.path.dirname(page_path))}">{product['category']['main']}</a> &gt;
                <a href="{os.path.relpath('category/' + product['category']['main'] + '/' + product['category']['sub'].replace(' ', '') + '.html', os.path.dirname(page_path))}">{product['category']['sub']}</a></p>
                <div class="price-section">
                    <p class="current-price">現在の価格：<span>{product['price']}</span></p>
                </div>
                <div class="ai-recommendation-section">
                    <div class="price-status-title">💡注目ポイント</div>
                    <div class="price-status-content ai-analysis">{product['ai_analysis']}</div>
                    {purchase_button_html}
                </div>
                {ai_analysis_block_html}
                {affiliate_links_html}
                <div class="item-description">
                    <h2>商品説明</h2>
                    <p>{product['description']}</p>
                </div>
                {specs_html}
                <div class="product-tags">
                    {"".join([f'<a href="../tags/{tag}.html" class="tag-button">#{tag}</a>' for tag in product.get('tags', [])])}
                </div>
            </div>
        </div>
    </div>
</main>
"""
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + item_html_content + footer)
        print(f"{page_path} が生成されました。")

    TAGS_PER_PAGE = 50
    all_tags = sorted(list(set(tag for product in products for tag in product.get('tags', []))))
    total_tag_pages = math.ceil(len(all_tags) / TAGS_PER_PAGE)
    os.makedirs('tags', exist_ok=True)
    for i in range(total_tag_pages):
        start_index = i * TAGS_PER_PAGE
        end_index = start_index + TAGS_PER_PAGE
        paginated_tags = all_tags[start_index:end_index]
        page_num = i + 1
        page_path = 'tags/index.html' if page_num == 1 else f'tags/page{page_num}.html'
        tag_list_html_content = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">タグから探す</h2>
        <div class="product-tags all-tags-list">
            {"".join([f'<a href="{tag}.html" class="tag-button">#{tag}</a>' for tag in paginated_tags])}
        </div>
    </div>
</main>
"""
        pagination_html = ""
        if total_tag_pages > 1:
            pagination_html += '<div class="pagination">'
            if page_num > 1:
                prev_link = 'index.html' if page_num == 2 else f'page{page_num - 1}.html'
                pagination_html += f'<a href="{prev_link}" class="prev">前へ</a>'
            for p in range(1, total_tag_pages + 1):
                page_link = 'index.html' if p == 1 else f'page{p}.html'
                active_class = 'active' if p == page_num else ''
                pagination_html += f'<a href="{page_link}" class="{active_class}">{p}</a>'
            if page_num < total_tag_pages:
                next_link = f'page{page_num + 1}.html'
                pagination_html += f'<a href="{next_link}" class="next">次へ</a>'
            pagination_html += '</div>'
        tag_header, tag_footer = generate_header_footer(page_path, page_title="タグ一覧")
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(tag_header + tag_list_html_content + pagination_html + tag_footer)
        print(f"タグページ: {page_path} が生成されました。")
        
    all_tags = set(tag for product in products for tag in product.get('tags', []))
    for tag in all_tags:
        tag_page_path = f'tags/{tag}.html'
        tag_products = [product for product in products if tag in product.get('tags', [])]
        tag_page_content = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">#{tag} の商品一覧</h2>
        <div class="product-grid">
            {"".join([f'''
            <a href="../{product['page_url']}" class="product-card">
                <img src="{product['image_url']}" alt="{product['name']}">
                <div class="product-info">
                    <h3 class="product-name">{product['name'][:20] + '...' if len(product['name']) > 20 else product['name']}</h3>
                    <p class="product-price">{product['price']}</p>
                    <div class="price-status-title">💡注目ポイント</div>
                    <div class="price-status-content ai-analysis">{product['ai_analysis']}</div>
                </div>
            </a>
            ''' for product in tag_products])}
        </div>
    </div>
</main>
"""
        tag_header, tag_footer = generate_header_footer(tag_page_path, page_title=f"#{tag} の商品一覧")
        with open(tag_page_path, 'w', encoding='utf-8') as f:
            f.write(tag_header + tag_page_content + tag_footer)
        print(f"タグページ: {tag_page_path} が生成されました。")
    
    contact_content = """
    <main class="container">
        <div class="static-content">
            <h1>お問い合わせ</h1>
            <p>ご質問やご要望がございましたら、以下のメールアドレスまでご連絡ください。</p>
            <p>メールアドレス: sokux001@gmail.com</p>
        </div>
    </main>
    """
    generate_static_page("contact.html", "お問い合わせ", contact_content)
    privacy_content = """
    <main class="container">
        <div class="static-content">
            <h1>プライバシーポリシー</h1>
            <p>当サイトは、Googleアナリティクスを使用しています。収集される情報やその利用目的については、Googleのプライバシーポリシーをご確認ください。</p>
            <p>当サイトは、Amazon.co.jpを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定されたアフィリエイトプログラムである、Amazonアソシエイト・プログラムの参加者です。</p>
        </div>
    </main>
    """
    generate_static_page("privacy.html", "プライバシーポリシー", privacy_content)
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

    def create_sitemap():
        base_url = "https://w41w41-beep.github.io/kaidoki-navi/"
        sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>{base_url}</loc>\n'
        sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
        sitemap_content += '    <changefreq>daily</changefreq>\n'
        sitemap_content += '    <priority>1.0</priority>\n'
        sitemap_content += '  </url>\n'
        categories = {}
        for product in products:
            main_cat = product['category']['main']
            sub_cat = product['category']['sub']
            if main_cat not in categories:
                categories[main_cat] = set()
            categories[main_cat].add(sub_cat)
        for main_cat, sub_cats in categories.items():
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}category/{main_cat}/index.html</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>daily</changefreq>\n'
            sitemap_content += '    <priority>0.8</priority>\n'
            sitemap_content += '  </url>\n'
            for sub_cat in sub_cats:
                sitemap_content += '  <url>\n'
                sitemap_content += f'    <loc>{base_url}category/{main_cat}/{sub_cat.replace(" ", "")}.html</loc>\n'
                sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
                sitemap_content += '    <changefreq>daily</changefreq>\n'
                sitemap_content += '    <priority>0.7</priority>\n'
                sitemap_content += '  </url>\n'
        for product in products:
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}{product["page_url"]}</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>daily</changefreq>\n'
            sitemap_content += '    <priority>0.6</priority>\n'
            sitemap_content += '  </url>\n'
        static_pages = ["privacy.html", "disclaimer.html", "contact.html"]
        for page in static_pages:
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}{page}</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>monthly</changefreq>\n'
            sitemap_content += '    <priority>0.5</priority>\n'
            sitemap_content += '  </url>\n'
        sitemap_content += '</urlset>'
        with open('sitemap.xml', 'w', encoding='utf-8') as f:
            f.write(sitemap_content)
        print("sitemap.xml が生成されました。")
    create_sitemap()
    print("サイトのファイル生成が完了しました！")

if __name__ == "__main__":
    new_products = fetch_rakuten_items()
    products = update_products_json(new_products)
    generate_site(products)
