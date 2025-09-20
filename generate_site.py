import json
import math
import os
import shutil
from datetime import date
import requests
import time

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 24

# OpenAI APIの設定
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
# APIキーは実行環境が自動的に供給するため、ここでは空の文字列とします。
OPENAI_API_KEY = ""
MODEL_NAME = "gpt-4o-mini"

def generate_ai_analysis(product_name, product_price, price_history):
    """
    OpenAI APIを使用して、商品の価格分析テキストを生成する。
    応答は一言アピールと詳細分析の2つの部分から構成される。
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }

    # 価格履歴データをプロンプトに追加
    history_text = f"過去の価格履歴は以下の通りです:\n{price_history}" if price_history else "価格履歴はありません。"
    
    messages = [
        {"role": "system", "content": "あなたは、価格比較の専門家として、消費者に商品の買い時をアドバイスします。回答は必ずJSON形式で提供してください。JSONは「headline」と「analysis」の2つのキーを持ちます。「headline」は商品の買い時を伝える簡潔な一言で、可能であれば具体的な割引率や数字を使って表現してください。「analysis」はなぜ買い時なのかを説明する詳細な文章です。日本語で回答してください。"},
        {"role": "user", "content": f"{product_name}という商品の現在の価格は{product_price}円です。{history_text}。この商品の価格について、市場の動向を踏まえた分析と買い時に関するアドバイスを日本語で提供してください。"}
    ]
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "google_search",
                    "description": "Google検索を実行して、最新の価格動向や市場情報を取得します。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "queries": {
                                "type": "array",
                                "items": { "type": "string" }
                            }
                        },
                        "required": ["queries"]
                    }
                }
            }
        ],
        "tool_choice": "auto"
    }

    try:
        response = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        
        # 応答からJSONテキストを抽出してパース
        json_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        if json_text:
            analysis_data = json.loads(json_text)
            return analysis_data.get('headline', 'AI分析準備中'), analysis_data.get('analysis', '詳細なAI分析は現在準備中です。')
        
    except requests.exceptions.RequestException as e:
        print(f"OpenAI APIへのリクエスト中にエラーが発生しました: {e}")
    except (IndexError, KeyError, json.JSONDecodeError) as e:
        print(f"OpenAI APIの応答形式が不正です: {e}")
    
    return "AI分析準備中", "詳細なAI分析は現在準備中です。"

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
                
                # 'genreName'が存在しない場合を考慮してget()メソッドを使用
                genre_name = item_data.get('genreName', '')
                
                # カテゴリを正しく設定
                main_cat = keyword
                
                # サンプルデータとして、いくつかの商品に商品説明を追加
                description = "高品質な素材を使用した多機能製品です。快適な使用感と優れた耐久性を提供します。"
                if item_data['itemCode'] == "10000001":  # 例: 特定のIDに説明を追加
                    description = "このモデルは、最新のプロセッサーを搭載し、高速なパフォーマンスを実現します。動画編集やゲームなど、重い作業にも対応できるパワフルな一台です。"

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
                    "ai_headline": "AI分析準備中",
                    "ai_analysis": "詳細なAI分析は現在準備中です。",
                    "description": description,
                    "date": date.today().isoformat(),
                    "main_ec_site": "楽天", # メインのECサイトを記録
                    "price_history": []
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

    # 検索したいキーワードのリスト
    keywords = ['掃除機', 'イヤホン']
    all_products = []
    
    for keyword in keywords:
        url = f"https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch?appid={app_id}&query={keyword}&sort=-review_count&hits=5"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            items = data.get('hits', [])
            
            for item in items:
                # Yahoo!ショッピングのデータ構造に合わせて変換
                all_products.append({
                    "id": item['jan_code'], # JANコードをIDとして使用
                    "name": item['name'],
                    "price": f"{int(item['price']):,}",
                    "image_url": item['image']['medium'],
                    "rakuten_url": "https://www.rakuten.co.jp/",
                    "yahoo_url": item['url'],
                    "amazon_url": "https://www.amazon.co.jp/ref=as_li_ss_il?ie=UTF8&linkCode=ilc&tag=soc07-22&linkId=db3c1808e6f1f516353d266e76811a7c&language=ja_JP",
                    "page_url": f"pages/{item['jan_code']}.html",
                    "category": {
                        "main": keyword, # キーワードをメインカテゴリに
                        "sub": item.get('category_name', '') # カテゴリ名を取得
                    },
                    "ai_headline": "AI分析準備中",
                    "ai_analysis": "詳細なAI分析は現在準備中です。",
                    "description": item.get('description', 'お手入れが簡単なコードレスタイプで、吸引力もパワフル。狭い隙間も楽々お掃除できます。'),
                    "date": date.today().isoformat(),
                    "main_ec_site": "Yahoo!", # メインのECサイトを記録
                    "price_history": []
                })
        except requests.exceptions.RequestException as e:
            print(f"Yahoo! APIへのリクエスト中にエラーが発生しました: {e}")
            
    return all_products

def update_products_json(new_products):
    """
    新しい商品データを既存のproducts.jsonに統合・更新する関数。
    この関数内でAI分析を実行する。
    """
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
        if new_product['id'] in updated_products:
            # 既存の商品の場合、価格履歴を更新
            existing_product = updated_products[new_product['id']]
            if 'price_history' not in existing_product:
                existing_product['price_history'] = []
            
            # 最新の価格を履歴に追加（重複は避ける）
            current_date = date.today().isoformat()
            current_price = int(new_product['price'].replace(',', ''))
            
            # 既に今日の価格が記録されていなければ追加
            if not existing_product['price_history'] or existing_product['price_history'][-1]['date'] != current_date:
                existing_product['price_history'].append({"date": current_date, "price": current_price})

            # 他の最新情報で上書き
            existing_product.update(new_product)
        else:
            # 新規商品の場合はそのまま追加
            new_product['price_history'] = [{"date": date.today().isoformat(), "price": int(new_product['price'].replace(',', ''))}]
            updated_products[new_product['id']] = new_product
    
    final_products = list(updated_products.values())
    
    # ここからAI分析の処理を追加
    print("AIによる価格分析を開始します。")
    for i, product in enumerate(final_products):
        print(f"商品 {i+1}/{len(final_products)}: '{product['name']}' のAI分析を生成中...")
        try:
            price_int = int(product['price'].replace(',', ''))
            price_history = product.get('price_history', [])
            ai_headline, ai_analysis_text = generate_ai_analysis(product['name'], price_int, price_history)
            product['ai_headline'] = ai_headline
            product['ai_analysis'] = ai_analysis_text
            time.sleep(1)
        except ValueError:
            print(f"価格の変換に失敗しました: {product['price']}")
            product['ai_headline'] = "AI分析準備中"
            product['ai_analysis'] = "詳細なAI分析は現在準備中です。"

    print("AIによる価格分析が完了しました。")
    
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
            if file.endswith('.html') and not file in ['privacy.html', 'disclaimer.html', 'contact.html', 'sitemap.xml']:
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
        <div class="price-status-content ai-analysis">{product['ai_headline']}</div>
    </div>
</a>
            """
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + products_html + "</div>" + footer)
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
        <div class="price-status-content ai-analysis">{product['ai_headline']}</div>
    </div>
</a>
                """
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(header + main_content_html + products_html + "</div>" + footer)
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
        <p class="product-price">{product['price']}円</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product['ai_headline']}</div>
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
                    <p>{product['ai_analysis']}</p>
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
        # メインECサイトの購入ボタンを生成
        purchase_button_html = ""
        main_ec_site = product.get("main_ec_site")
        
        if main_ec_site == "Amazon":
            purchase_button_html = f'<a href="{product["amazon_url"]}" class="purchase-button" target="_blank">Amazonで購入する</a>'
        elif main_ec_site == "楽天":
            purchase_button_html = f'<a href="{product["rakuten_url"]}" class="purchase-button" target="_blank">楽天市場で購入する</a>'
        elif main_ec_site == "Yahoo!":
            purchase_button_html = f'<a href="{product["yahoo_url"]}" class="purchase-button" target="_blank">Yahoo!ショッピングで購入する</a>'

        # 最安値ショップのボタンを常に3つ表示
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
                    <div class="price-status-content ai-analysis">{product['ai_headline']}</div>
                    {purchase_button_html}
                </div>
                {ai_analysis_block_html}
                {affiliate_links_html}
                <div class="item-description">
                    <h2>商品説明</h2>
                    <p>{product.get('description', '商品説明は現在準備中です。')}</p>
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
                    <p class="product-price">{product['price']}円</p>
                    <div class="price-status-title">💡注目ポイント</div>
                    <div class="price-status-content ai-analysis">{product['ai_headline']}</div>
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
    rakuten_products = fetch_rakuten_items()
    yahoo_products = fetch_yahoo_items()
    
    # 2つのAPIからの結果を結合
    new_products = rakuten_products + yahoo_products
    
    products = update_products_json(new_products)
    generate_site(products)
