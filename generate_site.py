import json
import math
import os
import shutil
import requests
import time
from datetime import date

# 1ページあたりの商品数を定義
# この値は、AIが選別した注目アイテムの最大表示数となります。
PRODUCTS_PER_PAGE = 10

def generate_ai_analysis(product_name, product_description, main_category):
    """OpenAI APIを使用して商品分析の文章と注目アイテム判定を生成する関数"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("OPENAI_API_KEYが設定されていません。AI分析はスキップされます。")
        return "AIによる価格分析は近日公開！", False, "AIによる価格分析は近日公開！"
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # システムプロンプトを調整して、2つの役割を明確に指示
    system_prompt = "あなたは、大手家電量販店の店員として、お客様におすすめの商品を説明するプロフェッショナルです。専門的で信頼性の高い情報を、親しみやすく簡潔に、魅力的な言葉で伝えてください。特に、「今が買い時」であることを強調し、具体的なセールスポイントを挙げてください。語尾は「です」や「ます」調にしてください。価格や割引率、ポイントの情報がなければ、その商品自体が持つ魅力や機能、品質を強調してください。"

    # AIに生成させる内容の指示
    user_prompt = f"""以下の商品について、お客様に「今が買い時だ！」と思わせるような、最も重要なセールスポイントを**1つだけ**教えてください。
このポイントは、トップページで一目でわかるように、簡潔な一言でまとめてください。

例:
・AI分析の結果

次に、この商品がなぜ買い時なのか、なぜ魅力的なのかを、より詳しく、簡潔で読みやすい要約として説明してください。

最後に、この商品が**注目アイテム**であるかどうかを、**はい**か**いいえ**で回答してください。
判断基準は以下の点を総合的に考慮してください。
- 商品名や説明に「最新」「新モデル」「2024年モデル」などのキーワードが含まれているか。
- 商品に魅力的な機能や特徴があるか（商品説明から推測）。
- 割引やポイントアップなど、お得感があるか（商品説明から推測）。

---
商品名: {product_name}
カテゴリ: {main_category}
商品説明: {product_description}
"""
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 400,
        "temperature": 0.7
    }

    retries = 3
    for i in range(retries):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            data = response.json()
            text_result = data['choices'][0]['message']['content'].strip()

            lines = text_result.split('\n')
            
            # 注目アイテム判定の行を特定
            is_attention_item_result = "いいえ"
            long_analysis = ""
            short_analysis = "AIによる分析は近日公開！"

            # 注目ポイントと詳細分析を分離
            # 最初の行を短い分析、残りを長い分析とする
            if lines:
                short_analysis = lines[0].strip().replace("- ", "").replace("・", "")
                long_analysis = "\n".join(lines[1:-1]).strip()
                last_line = lines[-1].strip().lower()
                if 'はい' in last_line:
                    is_attention_item_result = "はい"
            
            # もし長い分析がなければ短い分析をそのまま使う
            if not long_analysis:
                long_analysis = short_analysis
            
            return short_analysis, (is_attention_item_result == "はい"), long_analysis

        except requests.exceptions.RequestException as e:
            print(f"APIリクエストエラー ({i+1}/{retries}): {e}")
            time.sleep(2 ** i)
        except (IndexError, KeyError) as e:
            print(f"API応答の解析エラー: {e}")
            return "AIによる価格分析は近日公開！", False, "AIによる価格分析は近日公開！"
            
    print("APIリクエストが失敗しました。")
    return "AIによる価格分析は近日公開！", False, "AIによる価格分析は近日公開！"

def fetch_rakuten_items():
    """楽天APIから複数のカテゴリで商品データを取得する関数"""
    app_id = os.environ.get('RAKUTEN_API_KEY')
    if not app_id:
        print("RAKUTEN_API_KEYが設定されていません。")
        return []

    keywords = ['パソコン', '家電']
    all_products = []

    for keyword in keywords:
        # 新着順で検索
        url = f"https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706?applicationId={app_id}&keyword={keyword}&format=json&sort=+itemCreatedAt&hits={PRODUCTS_PER_PAGE}"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            items = data.get('Items', [])
            
            for item in items:
                item_data = item['Item']
                genre_name = item_data.get('genreName', '')
                main_cat = keyword
                
                all_products.append({
                    "id": item_data['itemCode'],
                    "name": item_data['itemName'],
                    "price": f"{int(item_data['itemPrice']):,}",
                    "image_url": item_data['mediumImageUrls'][0]['imageUrl'],
                    "rakuten_url": item_data['itemUrl'],
                    "yahoo_url": "https://shopping.yahoo.co.jp/",
                    "amazon_url": "https://www.amazon.co.jp/ref=as_li_ss_il?ie=UTF8&linkCode=ilc&tag=soc07-22&linkId=db3c1808e6f1f516353d266e76811a7c&language=ja_JP",
                    "page_url": f"pages/{item_data['itemCode']}.html",
                    "category": {
                        "main": main_cat,
                        "sub": genre_name
                    },
                    "short_ai_analysis": "placeholder", # 新しい短い分析用フィールド
                    "long_ai_analysis": "placeholder",  # 新しい長い分析用フィールド
                    "description": item_data.get('itemCaption', '商品説明は現在準備中です。'),
                    "date": date.today().isoformat(),
                    "main_ec_site": "楽天",
                    "is_attention_item": False
                })
        except requests.exceptions.RequestException as e:
            print(f"楽天APIへのリクエスト中にエラーが発生しました: {e}")

    return all_products

def fetch_yahoo_items():
    """Yahoo!ショッピングAPIから商品データを取得する関数"""
    app_id = os.environ.get('YAHOO_API_KEY')
    if not app_id:
        print("YAHOO_API_KEYが設定されていません。")
        return []

    keywords = ['掃除機', 'イヤホン']
    all_products = []
    
    for keyword in keywords:
        # 新着順で検索
        url = f"https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch?appid={app_id}&query={keyword}&sort=create_datetime&hits={PRODUCTS_PER_PAGE}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            items = data.get('hits', [])
            
            for item in items:
                all_products.append({
                    "id": item['jan_code'],
                    "name": item['name'],
                    "price": f"{int(item['price']):,}",
                    "image_url": item['image']['medium'],
                    "rakuten_url": "https://www.rakuten.co.jp/",
                    "yahoo_url": item['url'],
                    "amazon_url": "https://www.amazon.co.jp/ref=as_li_ss_il?ie=UTF8&linkCode=ilc&tag=soc07-22&linkId=db3c1808e6f1f516353d266e76811a7c&language=ja_JP",
                    "page_url": f"pages/{item['jan_code']}.html",
                    "category": {
                        "main": keyword,
                        "sub": item.get('category_name', '')
                    },
                    "short_ai_analysis": "placeholder", # 新しい短い分析用フィールド
                    "long_ai_analysis": "placeholder",  # 新しい長い分析用フィールド
                    "description": item.get('description', '商品説明は現在準備中です。'),
                    "date": date.today().isoformat(),
                    "main_ec_site": "Yahoo!",
                    "is_attention_item": False
                })
        except requests.exceptions.RequestException as e:
            print(f"Yahoo! APIへのリクエスト中にエラーが発生しました: {e}")
            
    return all_products

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
        if sub_cat and sub_cat not in categories[main_cat]:
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
        <p class="product-price">{product['price']}円</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product['short_ai_analysis']}</div>
    </div>
</a>
            """
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + products_html + "</div></main>" + footer)
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
        <p class="product-price">{product['price']}円</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product['short_ai_analysis']}</div>
    </div>
</a>
                """
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(header + main_content_html + products_html + "</div></main>" + footer)
            print(f"{page_path} が生成されました。")

    attention_items = [p for p in products if p.get('is_attention_item')]

    total_pages = math.ceil(len(attention_items) / PRODUCTS_PER_PAGE)
    for i in range(total_pages):
        start_index = i * PRODUCTS_PER_PAGE
        end_index = start_index + PRODUCTS_PER_PAGE
        paginated_products = attention_items[start_index:end_index]
        page_num = i + 1
        page_path = 'index.html' if page_num == 1 else f'pages/page{page_num}.html'
        if page_num > 1:
            os.makedirs(os.path.dirname(page_path), exist_ok=True)
        header, footer = generate_header_footer(page_path)
        
        main_content_html = ""
        # 注目アイテムセクションをトップページに追加
        attention_html = ""
        if attention_items:
            attention_html += """
            <div class="ai-recommendation-section">
                <h2 class="ai-section-title">AIが選別した注目アイテム</h2>
                <div class="product-grid">
            """
            for product in paginated_products:
                link_path = os.path.relpath(product['page_url'], os.path.dirname(page_path))
                attention_html += f"""
<a href="{link_path}" class="product-card">
    <img src="{product['image_url']}" alt="{product['name']}">
    <div class="product-info">
        <h3 class="product-name">{product['name'][:20] + '...' if len(product['name']) > 20 else product['name']}</h3>
        <p class="product-price">{product['price']}円</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product['short_ai_analysis']}</div>
    </div>
</a>
                """
            attention_html += "</div></div>"
        else:
            attention_html = """
            <div class="ai-recommendation-section">
                <h2 class="ai-section-title">AIが選別した注目アイテム</h2>
                <p class="no-items-message">現在、注目アイテムはありません。最新情報をお待ちください！</p>
            </div>
            """

        main_content_html += attention_html
        
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
            f.write(header + '<main class="container">' + main_content_html + '</div>' + pagination_html + '</main>' + footer)
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
                    <p class="long-analysis-text">{product['long_ai_analysis']}</p>
                </div>
            </div>
        """
        specs_html = ""
        if "specs" in product:
            specs_html = f"""
                <div class="item-specs">
                    <h2>製品仕様・スペック</h2>
                    <p>{product.get('specs', '')}</p>
                </div>
            """
        purchase_button_html = ""
        main_ec_site = product.get("main_ec_site")
        
        if main_ec_site == "Amazon":
            purchase_button_html = f'<a href="{product["amazon_url"]}" class="purchase-button" target="_blank">Amazonで購入する</a>'
        elif main_ec_site == "楽天":
            purchase_button_html = f'<a href="{product["rakuten_url"]}" class="purchase-button" target="_blank">楽天市場で購入する</a>'
        elif main_ec_site == "Yahoo!":
            purchase_button_html = f'<a href="{product["yahoo_url"]}" class="purchase-button" target="_blank">Yahoo!ショッピングで購入する</a>'

        affiliate_links_html = f"""
            <div class="lowest-price-section">
                <p class="lowest-price-label">最安値ショップをチェック！</p>
                <div class="lowest-price-buttons">
                    <a href="{product.get("amazon_url", "https://www.amazon.co.jp/")}" class="btn shop-link" target="_blank">Amazonで見る</a>
                    <a href="{product.get("rakuten_url", "https://www.rakuten.co.jp/")}" class="btn shop-link" target="_blank">楽天市場で見る</a>
                    <a href="{product.get("yahoo_url", "https://shopping.yahoo.co.jp/")}" class="btn shop-link" target="_blank">Yahoo!ショッピングで見る</a>
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
                    <p class="current-price">現在の価格：<span>{product['price']}</span>円</p>
                </div>
                <div class="ai-recommendation-section">
                    <div class="price-status-title">💡注目ポイント</div>
                    <div class="price-status-content ai-analysis">{product['short_ai_analysis']}</div>
                    {purchase_button_html}
                </div>
                {ai_analysis_block_html}
                {affiliate_links_html}
                <div class="item-description">
                    <h2>商品説明</h2>
                    <p>{product.get('description', '商品説明は現在準備中です。')}</p>
                </div>
                {specs_html}
            </div>
        </div>
    </div>
</main>
"""
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + item_html_content + footer)
        print(f"{page_path} が生成されました。")
    
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
    rakuten_products = fetch_rakuten_items()
    yahoo_products = fetch_yahoo_items()
    
    new_products = rakuten_products + yahoo_products
    
    print("新しい商品のAI分析を生成中です...")
    for product in new_products:
        product['short_ai_analysis'], product['is_attention_item'], product['long_ai_analysis'] = generate_ai_analysis(product['name'], product['description'], product['category']['main'])
        time.sleep(1)
    
    products = update_products_json(new_products)
    generate_site(products)
