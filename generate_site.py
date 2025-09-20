import json
import math
import os
import shutil
import time
from datetime import date
import requests

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 24

# APIキーは実行環境が自動的に供給するため、ここでは空の文字列とします。
# OpenAI APIの設定
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # 環境変数からAPIキーを取得
MODEL_NAME = "gpt-4o-mini"

def generate_ai_analysis(product_name, product_price, price_history):
    """
    OpenAI APIを使用して、商品の価格分析テキストを生成する。
    応答は一言アピールと詳細分析の2つの部分から構成される。
    """
    if not OPENAI_API_KEY:
        print("警告: OpenAI APIキーが設定されていません。AI分析はスキップされます。")
        return "AI分析準備中", "詳細なAI分析は現在準備中です。"
    
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
        response = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(payload), timeout=10) # タイムアウトを追加
        response.raise_for_status() # HTTPエラーを確認
        result = response.json()
        
        # 応答からJSONテキストを抽出してパース
        json_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        if json_text:
            analysis_data = json.loads(json_text)
            return analysis_data.get('headline', 'AI分析準備中'), analysis_data.get('analysis', '詳細なAI分析は現在準備中です。')
        
    except requests.exceptions.Timeout:
        print("OpenAI APIへのリクエストがタイムアウトしました。")
    except requests.exceptions.RequestException as e:
        print(f"OpenAI APIへのリクエスト中にエラーが発生しました: {e}")
    except (IndexError, KeyError, json.JSONDecodeError) as e:
        print(f"OpenAI APIの応答形式が不正です: {e}")
    
    return "AI分析準備中", "詳細なAI分析は現在準備中です。"

def generate_ai_summary(text):
    """
    与えられたテキストをAIに要約させる関数
    """
    if not OPENAI_API_KEY:
        print("警告: OpenAI APIキーが設定されていません。商品説明の要約はスキップされます。")
        return "この商品の詳しい説明は準備中です。恐れ入りますが、しばらくしてから再度お試しください。"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }

    messages = [
        {"role": "system", "content": "あなたは、ウェブサイトのコンテンツ作成をサポートするプロのライターです。ユーザーから提供された商品説明の文章を読み、ウェブサイトに掲載するのに適した、簡潔で魅力的な要約を生成してください。キーワードを適切に含み、ユーザーの購入意欲を高めるような文章にしてください。出力は要約された文章のみにしてください。"},
        {"role": "user", "content": f"以下の商品説明を要約してください。\n\n{text}"}
    ]
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages
    }
    
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        result = response.json()
        
        summary_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        if summary_text:
            return summary_text
    
    except requests.exceptions.Timeout:
        print("OpenAI APIへのリクエストがタイムアウトしました。")
    except requests.exceptions.RequestException as e:
        print(f"OpenAI APIへのリクエスト中にエラーが発生しました: {e}")
    except (IndexError, KeyError) as e:
        print(f"OpenAI APIの応答形式が不正です: {e}")
    
    return "この商品の詳しい説明は準備中です。恐れ入りますが、しばらくしてから再度お試しください。"

def generate_ai_subcategory(product_name):
    """
    OpenAI APIを使用して、商品のサブカテゴリーを生成する。
    """
    if not OPENAI_API_KEY:
        print("警告: OpenAI APIキーが設定されていません。AIサブカテゴリーはスキップされます。")
        return "未分類"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }
    
    messages = [
        {"role": "system", "content": "あなたは商品のカテゴリー分類の専門家です。与えられた商品名から、最も適切で短いサブカテゴリー名を1つだけ日本語で答えてください。例：スマートフォンケース, ワイヤレスイヤホン, ノートパソコン, 電動歯ブラシ"},
        {"role": "user", "content": f"商品名: {product_name}"}
    ]
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages
    }
    
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(payload), timeout=5)
        response.raise_for_status()
        subcategory = response.json()['choices'][0]['message']['content'].strip()
        return subcategory
    except requests.exceptions.RequestException as e:
        print(f"AIサブカテゴリー生成中にエラーが発生しました: {e}")
    except (IndexError, KeyError) as e:
        print(f"AIの応答形式が不正です: {e}")
    
    return "未分類"


def fetch_rakuten_items(summary_dict):
    """楽天APIから複数のカテゴリで商品データを取得する関数"""
    app_id = os.environ.get('RAKUTEN_API_KEY')
    if not app_id:
        print("RAKUTEN_API_KEYが設定されていません。")
        return []

    keywords = ['パソコン', '家電']
    all_products = []

    for keyword in keywords:
        url = f"https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706?applicationId={app_id}&keyword={keyword}&format=json&sort=-reviewCount&hits=10"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            items = data.get('Items', [])
            
            for item in items:
                item_data = item['Item']
                item_id = item_data['itemCode']
                
                # 要約が既に存在するか確認
                ai_summary = summary_dict.get(item_id, {}).get('ai_summary')
                
                if ai_summary is None:
                    # 要約がなければ新しく生成
                    description = item_data.get('itemCaption', '')
                    ai_summary = generate_ai_summary(description) if description else "この商品の詳しい説明は準備中です。恐れ入りますが、しばらくしてから再度お試しください。"

                # サブカテゴリーをAIで生成
                ai_subcategory = generate_ai_subcategory(item_data['itemName'])

                all_products.append({
                    "id": item_id,
                    "name": item_data['itemName'],
                    "price": f"{int(item_data['itemPrice']):,}",
                    "image_url": item_data['mediumImageUrls'][0]['imageUrl'],
                    "rakuten_url": item_data['itemUrl'],
                    "yahoo_url": "https://shopping.yahoo.co.jp/", 
                    "amazon_url": "https://www.amazon.co.jp/ref=as_li_ss_il?ie=UTF8&linkCode=ilc&tag=soc07-22&linkId=db3c1808e6f1f516353d266e76811a7c&language=ja_JP",
                    "page_url": f"pages/{item_id}.html",
                    "category": {
                        "main": keyword,
                        "sub": ai_subcategory
                    },
                    "ai_headline": "AI分析準備中",
                    "ai_analysis": "詳細なAI分析は現在準備中です。",
                    "description": item_data.get('itemCaption', ''),
                    "ai_summary": ai_summary,
                    "date": date.today().isoformat(),
                    "main_ec_site": "楽天",
                    "price_history": []
                })
        except requests.exceptions.RequestException as e:
            print(f"楽天APIへのリクエスト中にエラーが発生しました: {e}")
            
    return all_products

def fetch_yahoo_items(summary_dict):
    """Yahoo!ショッピングAPIから商品データを取得する関数"""
    app_id = os.environ.get('YAHOO_API_KEY')
    if not app_id:
        print("YAHOO_API_KEYが設定されていません。")
        return []

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
                item_id = item['jan_code']
                
                # 要約が既に存在するか確認
                ai_summary = summary_dict.get(item_id, {}).get('ai_summary')
                
                if ai_summary is None:
                    # 要約がなければ新しく生成
                    description = item.get('description', '')
                    ai_summary = generate_ai_summary(description) if description else "この商品の詳しい説明は準備中です。恐れ入りますが、しばらくしてから再度お試しください。"
                
                # サブカテゴリーをAIで生成
                ai_subcategory = generate_ai_subcategory(item['name'])

                all_products.append({
                    "id": item_id,
                    "name": item['name'],
                    "price": f"{int(item['price']):,}",
                    "image_url": item['image']['medium'],
                    "rakuten_url": "https://www.rakuten.co.jp/",
                    "yahoo_url": item['url'],
                    "amazon_url": "https://www.amazon.co.jp/ref=as_li_ss_il?ie=UTF8&linkCode=ilc&tag=soc07-22&linkId=db3c1808e6f1f516353d266e76811a7c&language=ja_JP",
                    "page_url": f"pages/{item_id}.html",
                    "category": {
                        "main": keyword,
                        "sub": ai_subcategory
                    },
                    "ai_headline": "AI分析準備中",
                    "ai_analysis": "詳細なAI分析は現在準備中です。",
                    "description": item.get('description', ''),
                    "ai_summary": ai_summary,
                    "date": date.today().isoformat(),
                    "main_ec_site": "Yahoo!",
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
            existing_product = updated_products[new_product['id']]
            if 'price_history' not in existing_product:
                existing_product['price_history'] = []
            
            current_date = date.today().isoformat()
            try:
                current_price = int(new_product['price'].replace(',', ''))
                if not existing_product['price_history'] or existing_product['price_history'][-1]['date'] != current_date:
                    existing_product['price_history'].append({"date": current_date, "price": current_price})
            except ValueError:
                print(f"価格の変換に失敗しました: {new_product['price']}")

            existing_product.update(new_product)
        else:
            try:
                new_product['price_history'] = [{"date": date.today().isoformat(), "price": int(new_product['price'].replace(',', ''))}]
                updated_products[new_product['id']] = new_product
            except ValueError:
                print(f"価格の変換に失敗したため、商品 {new_product['id']} はスキップされます。")
    
    final_products = list(updated_products.values())
    
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
                # ファイル名として無効な文字を削除・置換
                safe_sub_cat = sub_cat_link.replace(' ', '').replace('/', '').replace('\\', '')
                if safe_sub_cat:  # ファイル名が空でないことを確認
                    sub_cat_links_html += f'<a href="{safe_sub_cat}.html">{sub_cat_link}</a><span class="separator">|</span>'
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

    # 古いファイルを削除
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
            
            # --- ここが修正点です ---
            # サブカテゴリ名が空または不適切な場合はスキップ
            safe_sub_cat = sub_cat.replace(' ', '').replace('/', '').replace('\\', '')
            if not safe_sub_cat:
                print(f"警告: 不正なサブカテゴリ名 '{sub_cat}' をスキップしました。")
                continue

            sub_cat_file_name = f"{safe_sub_cat}.html"
            page_path = f"category/{main_cat}/{sub_cat_file_name}"
            os.makedirs(os.path.dirname(page_path), exist_ok=True)
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
        page_path = f"index.html" if page_num == 1 else f"page/{page_num}.html"
        os.makedirs(os.path.dirname(page_path), exist_ok=True)
        header, footer = generate_header_footer(page_path, page_title=f"商品一覧（{page_num}ページ目）")
        
        pagination_html = '<div class="pagination-buttons">'
        if page_num > 1:
            prev_page_url = f"index.html" if page_num == 2 else f"page/{page_num - 1}.html"
            pagination_html += f'<a href="{prev_page_url}" class="pagination-button">前のページ</a>'
        if page_num < total_pages:
            next_page_url = f"page/{page_num + 1}.html"
            pagination_html += f'<a href="{next_page_url}" class="pagination-button">次のページ</a>'
        pagination_html += '</div>'
        
        main_content_html = f"""
<main class="container">
 <div class="ai-recommendation-section">
 <h2 class="ai-section-title">AIおすすめ商品</h2>
 <div class="product-grid">
 """
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
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + products_html + "</div>" + pagination_html + footer)
        print(f"{page_path} が生成されました。")

    os.makedirs('pages', exist_ok=True)
    for product in products:
        page_path = f"pages/{product['id']}.html"
        header, footer = generate_header_footer(page_path, page_title=product['name'])
        
        price_history_html = ""
        if product['price_history']:
            price_history_html = """
<div class="product-detail-section">
<h3>価格履歴</h3>
<div class="price-history-chart">
<canvas id="priceChart"></canvas>
</div>
</div>
"""
        
        affiliate_links_html = ""
        if 'affiliateLinks' in product:
            for link in product['affiliateLinks']:
                affiliate_links_html += f'<li><a href="{link["url"]}" target="_blank" rel="noopener noreferrer">{link["shop"]}で詳細を見る</a></li>'
        else:
            # 存在しない場合のために、ダミーのリンクを追加
            affiliate_links_html = f"""
<li><a href="{product['rakuten_url']}" target="_blank" rel="noopener noreferrer">楽天市場で詳細を見る</a></li>
<li><a href="{product['yahoo_url']}" target="_blank" rel="noopener noreferrer">Yahoo!ショッピングで詳細を見る</a></li>
<li><a href="{product['amazon_url']}" target="_blank" rel="noopener noreferrer">Amazonで詳細を見る</a></li>
"""


        main_content_html = f"""
<main class="container product-detail">
 <div class="product-detail-header">
 <img src="{product['image_url']}" alt="{product['name']}" class="product-image">
 <h2>{product['name']}</h2>
 </div>
 <div class="product-detail-section">
 <h3>AIによる商品ハイライト</h3>
 <p>{product.get('ai_summary', '')}</p>
 </div>
 <div class="product-detail-section">
 <h3>AI価格分析</h3>
 <h4>{product['ai_headline']}</h4>
 <p>{product['ai_analysis']}</p>
 </div>
 <div class="product-detail-section">
 <h3>商品説明</h3>
 <p>{product['description']}</p>
 </div>
 <div class="product-detail-section">
 <h3>購入はこちらから</h3>
 <ul class="affiliate-links">
 {affiliate_links_html}
 </ul>
 </div>
 {price_history_html}
</main>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
 const priceData = {json.dumps(product['price_history'])};
 if (priceData.length > 0) {{
 const labels = priceData.map(d => d.date);
 const data = priceData.map(d => d.price);
 const ctx = document.getElementById('priceChart').getContext('2d');
 new Chart(ctx, {{
 type: 'line',
 data: {{
 labels: labels,
 datasets: [{{
 label: '価格 (円)',
 data: data,
 borderColor: 'rgb(75, 192, 192)',
 tension: 0.1
 }}]
 }},
 options: {{
 responsive: true,
 maintainAspectRatio: false,
 scales: {{
 x: {{
 title: {{
 display: true,
 text: '日付'
 }}
 }},
 y: {{
 title: {{
 display: true,
 text: '価格 (円)'
 }}
 }}
 }}
 }}
 }});
 }}
</script>
        """
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + footer)
        print(f"{page_path} が生成されました。")
    
    # 静的ページを生成する関数呼び出しを削除
    # generate_static_page('privacy.html', 'プライバシーポリシー', '<main class="container"><div class="static-content"><h2>プライバシーポリシー</h2><p>当サイトは、ユーザーの個人情報の保護に最大限の注意を払っています。...</p></div>')
    # generate_static_page('disclaimer.html', '免責事項', '<main class="container"><div class="static-content"><h2>免責事項</h2><p>当サイトで提供される情報や価格は、掲載時点のものであり、その正確性や完全性を保証するものではありません。...</p></div>')
    # generate_static_page('contact.html', 'お問い合わせ', '<main class="container"><div class="static-content"><h2>お問い合わせ</h2><p>当サイトに関するお問い合わせは、以下のメールアドレスまでお願いいたします。...</p></div>')

def create_sitemap(products):
    """
    商品データからsitemap.xmlを生成する関数。
    """
    base_url = "https://your-domain.com/"
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap_content += '  <url>\n'
    sitemap_content += f'    <loc>{base_url}</loc>\n'
    sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
    sitemap_content += '    <changefreq>daily</changefreq>\n'
    sitemap_content += '    <priority>1.0</priority>\n'
    sitemap_content += '  </url>\n'
    genres = ['パソコン', '家電', '掃除機', 'イヤホン']
    for genre in genres:
        genre_url = f"{base_url}category/{genre}/"
        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>{genre_url}</loc>\n'
        sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
        sitemap_content += '    <changefreq>daily</changefreq>\n'
        sitemap_content += '    <priority>0.8</priority>\n'
        sitemap_content += '  </url>\n'
    total_pages = math.ceil(len(products) / PRODUCTS_PER_PAGE)
    for i in range(1, total_pages + 1):
        page_url = f"page/{i}.html" if i > 1 else ""
        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>{base_url}{page_url}</loc>\n'
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
    # 静的ページのsitemap生成を削除
    # static_pages = ["privacy.html", "disclaimer.html", "contact.html"]
    # for page in static_pages:
    #     sitemap_content += '  <url>\n'
    #     sitemap_content += f'    <loc>{base_url}{page}</loc>\n'
    #     sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
    #     sitemap_content += '    <changefreq>monthly</changefreq>\n'
    #     sitemap_content += '    <priority>0.5</priority>\n'
    #     sitemap_content += '  </url>\n'
    sitemap_content += '</urlset>'
    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write(sitemap_content)
    print("sitemap.xml が生成されました。")


def main():
    """
    メイン処理
    """
    print("サイトのファイル生成を開始します...")

    if not OPENAI_API_KEY:
        print("警告: OpenAI APIキーが設定されていません。AI要約とAI分析は生成されません。")
    
    # ai_summaries.jsonが存在すれば読み込む
    try:
        if os.path.exists('ai_summaries.json'):
            with open('ai_summaries.json', 'r', encoding='utf-8') as f:
                summary_dict = json.load(f)
        else:
            summary_dict = {}
    except json.JSONDecodeError:
        print("ai_summaries.jsonが破損しているため、新規作成します。")
        summary_dict = {}
    
    # 各ECサイトから商品データを取得
    rakuten_products = fetch_rakuten_items(summary_dict)
    yahoo_products = fetch_yahoo_items(summary_dict)
    
    # データを結合
    all_products = rakuten_products + yahoo_products
    
    # 新しく生成された要約をsummary_dictに追加
    newly_generated_summaries = {}
    for p in all_products:
        item_id = p.get('id')
        ai_summary = p.get('ai_summary')
        if ai_summary and summary_dict.get(item_id, {}).get('ai_summary') is None:
            newly_generated_summaries[item_id] = {'ai_summary': ai_summary}

    summary_dict.update(newly_generated_summaries)
    
    # 更新された要約をファイルに保存
    with open('ai_summaries.json', 'w', encoding='utf-8') as f:
        json.dump(summary_dict, f, ensure_ascii=False, indent=4)
        print(f"ai_summaries.json が更新されました。")

    # 商品データをproducts.jsonに統合・更新し、AI分析を実行
    final_products = update_products_json(all_products)
    
    # サイトファイルを生成
    generate_site(final_products)
    
    # sitemap.xmlを生成
    create_sitemap(final_products)

    print("サイトのファイル生成が完了しました。")

if __name__ == "__main__":
    main()
