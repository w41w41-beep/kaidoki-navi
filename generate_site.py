import json
import math
import os
import shutil
from datetime import date

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 24

def generate_site():
    """products.jsonを読み込み、HTMLファイルを生成する関数"""
    
    # products.jsonから商品データを読み込む
    with open('products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)

    # 日付データを追加
    today = date.today().isoformat()
    for product in products:
        if 'date' not in product:
            product['date'] = today

    # 日付順に並び替え
    products.sort(key=lambda p: p['date'], reverse=True)

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
        
        # パスに応じてベースパスを動的に決定
        if "pages" in current_path:
            base_path = ".."
        elif "category" in current_path:
            base_path = "../.."
        elif "tags" in current_path:
            base_path = ".."
        else:
            base_path = "."

        main_links_html = ""
        # 「すべてのタグを見る」リンクを先頭に固定
        main_links_html += f'<a href="{base_path}/tags/index.html">タグから探す</a><span class="separator">|</span>'
        
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
        
        # サブカテゴリーリンクのセクション
        sub_cat_links_html = ""
        if sub_cat_links:
            sub_cat_links_html += '<div class="genre-links sub-genre-links">'
            for sub_cat_link in sorted(sub_cat_links):
                # サブカテゴリーのリンクは、カテゴリフォルダ内なのでパスを変更する必要なし
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
    
    # 既存のHTMLファイルとディレクトリを削除
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

    # メインカテゴリーごとのページを生成
    # ----------------------------------------------------
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
            # カテゴリーページ内の画像パスとリンクパスを修正
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
                # サブカテゴリーページ内の画像パスとリンクパスを修正
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

    # トップページのHTMLを生成 (ページネーション付き)
    # ----------------------------------------------------
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
        
        # ページネーションのHTMLを生成
        pagination_html = ""
        if total_pages > 1:
            pagination_html += '<div class="pagination">'

            # 「前へ」ボタン
            if page_num > 1:
                prev_link = 'index.html' if page_num == 2 else f'pages/page{page_num - 1}.html'
                pagination_html += f'<a href="{os.path.relpath(prev_link, os.path.dirname(page_path))}" class="prev">前へ</a>'

            # ページ番号
            for p in range(1, total_pages + 1):
                page_link = 'index.html' if p == 1 else f'pages/page{p}.html'
                active_class = 'active' if p == page_num else ''
                pagination_html += f'<a href="{os.path.relpath(page_link, os.path.dirname(page_path))}" class="{active_class}">{p}</a>'

            # 「次へ」ボタン
            if page_num < total_pages:
                next_link = f'pages/page{page_num + 1}.html'
                pagination_html += f'<a href="{os.path.relpath(next_link, os.path.dirname(page_path))}" class="next">次へ</a>'

            pagination_html += '</div>'
            
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + '<main class="container"><div class="ai-recommendation-section"><h2 class="ai-section-title">今が買い時！お得な注目アイテム</h2><div class="product-grid">' + products_html + '</div>' + pagination_html + '</main>' + footer)
        print(f"{page_path} が生成されました。")

    # 個別ページを商品ごとに生成
    # ----------------------------------------------------
    for product in products:
        page_path = product['page_url']
        
        # 親ディレクトリが存在しない場合は作成
        dir_name = os.path.dirname(page_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        header, footer = generate_header_footer(page_path, page_title=f"{product['name']}の買い時情報")

        # AI分析のブロックを定義
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
                <div class="swiper">
                    <div class="swiper-wrapper">
                        <div class="swiper-slide"><img src="{product['image_url']}" alt="{product['name']}"></div>
                        {"".join([f'<div class="swiper-slide"><img src="{img}" alt="{product["name"]}"></div>' for img in product.get('images', [])])}
                    </div>
                    <div class="swiper-pagination"></div>
                    <div class="swiper-button-prev"></div>
                    <div class="swiper-button-next"></div>
                </div>
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

    # タグの一覧ページを生成（ページネーション付き）
    # ----------------------------------------------------
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
        # ページネーションのHTMLを生成
        pagination_html = ""
        if total_tag_pages > 1:
            pagination_html += '<div class="pagination">'

            # 「前へ」ボタン
            if page_num > 1:
                prev_link = 'index.html' if page_num == 2 else f'page{page_num - 1}.html'
                pagination_html += f'<a href="{prev_link}" class="prev">前へ</a>'

            # ページ番号
            for p in range(1, total_tag_pages + 1):
                page_link = 'index.html' if p == 1 else f'page{p}.html'
                active_class = 'active' if p == page_num else ''
                pagination_html += f'<a href="{page_link}" class="{active_class}">{p}</a>'

            # 「次へ」ボタン
            if page_num < total_tag_pages:
                next_link = f'page{page_num + 1}.html'
                pagination_html += f'<a href="{next_link}" class="next">次へ</a>'

            pagination_html += '</div>'
            
        tag_header, tag_footer = generate_header_footer(page_path, page_title="タグ一覧")
        
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(tag_header + tag_list_html_content + pagination_html + tag_footer)
        print(f"タグページ: {page_path} が生成されました。")
        
    # 個別のタグページを生成
    # ----------------------------------------------------
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
        
    # 静的ページを生成
    # ----------------------------------------------------
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

    # サイトマップを生成する関数
    def create_sitemap():
        base_url = "https://w41w41-beep.github.io/kaidoki-navi/"
        
        # XML形式のサイトマップを構築
        sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        # トップページのURLを追加
        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>{base_url}</loc>\n'
        sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
        sitemap_content += '    <changefreq>daily</changefreq>\n'
        sitemap_content += '    <priority>1.0</priority>\n'
        sitemap_content += '  </url>\n'

        # カテゴリページのURLを追加
        # カテゴリ情報を収集する既存のロジックから取得
        categories = {}
        for product in products:
            main_cat = product['category']['main']
            sub_cat = product['category']['sub']

            if main_cat not in categories:
                categories[main_cat] = set()
            categories[main_cat].add(sub_cat)

        for main_cat, sub_cats in categories.items():
            # メインカテゴリーのURLを追加
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}category/{main_cat}/index.html</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>daily</changefreq>\n'
            sitemap_content += '    <priority>0.8</priority>\n'
            sitemap_content += '  </url>\n'
            
            # サブカテゴリーのURLを追加
            for sub_cat in sub_cats:
                sitemap_content += '  <url>\n'
                sitemap_content += f'    <loc>{base_url}category/{main_cat}/{sub_cat.replace(" ", "")}.html</loc>\n'
                sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
                sitemap_content += '    <changefreq>daily</changefreq>\n'
                sitemap_content += '    <priority>0.7</priority>\n'
                sitemap_content += '  </url>\n'

        # 商品ごとのURLを追加
        for product in products:
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}{product["page_url"]}</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>daily</changefreq>\n'
            sitemap_content += '    <priority>0.6</priority>\n'
            sitemap_content += '  </url>\n'
            
        # 静的ページのURLを追加
        static_pages = ["privacy.html", "disclaimer.html", "contact.html"]
        for page in static_pages:
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}{page}</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>monthly</changefreq>\n'
            sitemap_content += '    <priority>0.5</priority>\n'
            sitemap_content += '  </url>\n'
            
        sitemap_content += '</urlset>'

        # sitemap.xmlファイルとして保存
        with open('sitemap.xml', 'w', encoding='utf-8') as f:
            f.write(sitemap_content)
        print("sitemap.xml が生成されました。")
    
    # generate_site関数の最後にサイトマップ生成関数を呼び出す
    create_sitemap()
    print("サイトのファイル生成が完了しました！")

# スクリプトを実行
if __name__ == "__main__":
    generate_site()
