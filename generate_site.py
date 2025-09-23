import json
import math
import os
import shutil
import time
from datetime import date
import requests
import csv
import urllib.parse

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 24

# APIキーは実行環境が自動的に供給するため、ここでは空の文字列とします。
# OpenAI APIの設定
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # 環境変数からAPIキーを取得
MODEL_NAME = "gpt-4o-mini"
CACHE_FILE = 'products.csv'
# AmazonとYahoo!ショッピングのアフィリエイトリンクを定義
AMAZON_AFFILIATE_LINK = "https://amzn.to/46zr68v"
YAHOO_AFFILIATE_LINK_BASE = "https://shopping.yahoo.co.jp/search?p="

def get_cached_data():
    """CSVファイルからキャッシュされた商品データを読み込む"""
    cached_data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # ヘッダーに'id'が存在しない場合は処理を終了
                if 'id' not in reader.fieldnames:
                    print("警告: CSVファイルに'id'ヘッダーが見つかりません。")
                    return {}

                for row in reader:
                    
                    # 'id'が空の行はスキップ
                    if not row.get('id'):
                        continue

                    product_id = row['id']

                    # 価格履歴の読み込みとエラーハンドリング
                    price_history_str = row.get('price_history', '[]')
                    try:
                        row['price_history'] = json.loads(price_history_str.replace("'", '"'))
                    except json.JSONDecodeError:
                        print(f"価格履歴のパースに失敗しました: ID {product_id}。データ: '{price_history_str}'")
                        row['price_history'] = []

                    # タグの読み込みとエラーハンドリング
                    tags_str = row.get('tags', '[]')
                    try:
                        row['tags'] = json.loads(tags_str.replace("'", '"'))
                    except json.JSONDecodeError:
                        print(f"タグのパースに失敗しました: ID {product_id}。データ: '{tags_str}'")
                        row['tags'] = []

                    # categoryキーが文字列の場合に辞書に変換
                    if isinstance(row.get('category'), str):
                        try:
                            row['category'] = json.loads(row['category'].replace("'", '"'))
                        except json.JSONDecodeError:
                            row['category'] = {"main": "不明", "sub": ""}
                    elif 'category' not in row or not isinstance(row['category'], dict):
                        row['category'] = {"main": "不明", "sub": ""}

                    cached_data[product_id] = row
        except csv.Error as e:
            print(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
            return {}
    return cached_data

def save_to_cache(products):
    """商品データをCSVファイルに保存する"""
    if not products:
        return

    # 全ての商品のキーを収集してフィールド名リストを作成
    fieldnames = set()
    for p in products:
        fieldnames.update(p.keys())
    fieldnames = sorted(list(fieldnames), key=lambda x: ['id', 'name', 'price', 'image_url', 'rakuten_url', 'yahoo_url', 'amazon_url', 'page_url', 'category', 'ai_headline', 'ai_analysis', 'description', 'ai_summary', 'tags', 'date', 'main_ec_site', 'price_history'].index(x) if x in ['id', 'name', 'price', 'image_url', 'rakuten_url', 'yahoo_url', 'amazon_url', 'page_url', 'category', 'ai_headline', 'ai_analysis', 'description', 'ai_summary', 'tags', 'date', 'main_ec_site', 'price_history'] else len(['id', 'name', 'price', 'image_url', 'rakuten_url', 'yahoo_url', 'amazon_url', 'page_url', 'category', 'ai_headline', 'ai_analysis', 'description', 'ai_summary', 'tags', 'date', 'main_ec_site', 'price_history']))

    with open(CACHE_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for product in products:
            # リストや辞書を文字列に変換して保存
            product_to_write = product.copy()
            product_to_write['price_history'] = json.dumps(product_to_write.get('price_history', []), ensure_ascii=False)
            product_to_write['tags'] = json.dumps(product_to_write.get('tags', []), ensure_ascii=False)
            product_to_write['category'] = json.dumps(product_to_write.get('category', {"main": "不明", "sub": ""}), ensure_ascii=False)
            writer.writerow(product_to_write)

def generate_ai_metadata(product_name, product_description):
    """
    OpenAI APIを使用して、商品の要約、タグ、サブカテゴリーを生成する。
    """
    if not OPENAI_API_KEY:
        print("警告: OpenAI APIキーが設定されていません。AIメタデータ生成はスキップされます。")
        return "この商品の詳しい説明は準備中です。", [], ""

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }

    prompt = f"""
    以下の商品情報をもとに、ウェブサイトのコンテンツとして最適な、簡潔で魅力的な要約、関連するタグ（3〜5個）、そして適切なサブカテゴリー（1つ）を日本語で生成してください。
    回答は必ずJSON形式で提供してください。JSONは「summary」、「tags」、「sub_category」の3つのキーを持ちます。

    商品名: {product_name}
    商品説明: {product_description}

    要約の文章には、SEOを意識した「格安」「最安値」「セール」「割引」などのキーワードを自然に含めてください。
    タグは商品の特徴や用途を表す単語をリスト形式で生成してください。
    サブカテゴリーは、商品のジャンルを細分化した単一の単語を生成してください。
    """

    messages = [
        {"role": "system", "content": "あなたは、ウェブサイトのコンテンツ作成をサポートするプロのAIアシスタントです。ユーザーからの指示に従い、商品情報を分析して魅力的なコンテンツを生成します。"},
        {"role_name": "user", "content": prompt}
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(payload), timeout=15)
        response.raise_for_status()
        result = response.json()

        json_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        if json_text:
            metadata = json.loads(json_text)
            summary = metadata.get('summary', "この商品の詳しい説明は準備中です。")
            tags = metadata.get('tags', [])
            sub_category = metadata.get('sub_category', "")
            return summary, tags, sub_category

    except requests.exceptions.Timeout:
        print("OpenAI APIへのリクエストがタイムアウトしました。")
    except requests.exceptions.RequestException as e:
        print(f"OpenAI APIへのリクエスト中にエラーが発生しました: {e}")
    except (IndexError, KeyError, json.JSONDecodeError) as e:
        print(f"OpenAI APIの応答形式が不正です: {e}")

    return "この商品の詳しい説明は準備中です。", [], ""

def generate_ai_analysis(product_name, product_price, price_history):
    """
    OpenAI APIを使用して、商品の価格分析テキストを生成する。
    """
    if not OPENAI_API_KEY:
        print("警告: OpenAI APIキーが設定されていません。AI分析はスキップされます。")
        return "AI分析準備中", "詳細なAI分析は現在準備中です。"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }

    history_text = f"過去の価格履歴は以下の通りです: {price_history}" if price_history else "価格履歴はありません。"

    messages = [
        {"role": "system", "content": "あなたは、価格比較の専門家として、消費者に商品の買い時をアドバイスします。回答は必ずJSON形式で提供してください。JSONは「headline」と「analysis」の2つのキーを持ちます。「headline」は商品の買い時を伝える簡潔な一言で、可能であれば具体的な割引率や数字を使って表現してください。「analysis」はなぜ買い時なのかを説明する詳細な文章です。日本語で回答してください。"},
        {"role_name": "user", "content": f"{product_name}という商品の現在の価格は{product_price}円です。{history_text}。この商品の価格について、市場の動向を踏まえた分析と買い時に関するアドバイスを日本語で提供してください。特に価格が前回と比べて下がっている場合は、**「最安値」**や**「セール」**といったキーワードを使って買い時を強調してください。"}
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        result = response.json()

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

def fetch_rakuten_items():
    """楽天APIから複数のジャンルの商品データを取得する関数"""
    app_id = os.environ.get('RAKUTEN_API_KEY')
    if not app_id:
        print("RAKUTEN_API_KEYが設定されていません。")
        return []

    # ジャンルに特化したキーワードとソート順を定義
    search_queries = [
        {'keyword': 'ノートパソコン', 'sort': '-reviewCount'},
        {'keyword': 'テレビ', 'sort': '-reviewCount'},
        {'keyword': 'デジタルカメラ', 'sort': '-reviewCount'},
        {'keyword': '冷蔵庫', 'sort': '-reviewCount'},
        {'keyword': '洗濯機', 'sort': '-reviewCount'}
    ]

    all_products = []

    for query in search_queries:
        keyword = query['keyword']
        sort_order = query['sort']
        # 取得件数を10個に設定
        url = f"https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706?applicationId={app_id}&keyword={keyword}&format=json&sort={sort_order}&hits=10"
        
        try:
            print(f"楽天APIから商品を取得中... (キーワード: {keyword})")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            items = data.get('Items', [])

            if items:
                for item in items:
                    item_data = item['Item']
                    description = item_data.get('itemCaption', '')

                    # 新しい商品情報を構築
                    new_product = {
                        "id": item_data['itemCode'],
                        "name": item_data['itemName'],
                        "price": str(item_data['itemPrice']),
                        "image_url": item_data.get('mediumImageUrls', [{}])[0].get('imageUrl', ''),
                        "rakuten_url": item_data.get('itemUrl', ''),
                        "yahoo_url": YAHOO_AFFILIATE_LINK_BASE + urllib.parse.quote(item_data['itemName']),
                        "amazon_url": AMAZON_AFFILIATE_LINK,
                        "page_url": f"products/{item_data['itemCode']}.html",
                        "category": {"main": "不明", "sub": ""},
                        "ai_headline": "",
                        "ai_analysis": "",
                        "description": description,
                        "ai_summary": "",
                        "tags": [],
                        "date": date.today().isoformat(),
                        "main_ec_site": "楽天",
                        "price_history": []
                    }
                    all_products.append(new_product)

        except requests.exceptions.RequestException as e:
            print(f"楽天APIへのリクエスト中にエラーが発生しました: {e}")
        except (IndexError, KeyError) as e:
            print(f"楽天APIの応答形式が不正です: {e}")

    return all_products

def update_products_csv(new_products):
    """
    新しい商品データを既存のproducts.csvに統合・更新する関数。
    この関数内でAI分析とメタデータ生成を実行する。
    """
    cached_products = get_cached_data()
    updated_products = {}
    newly_added_count = 0

    # 既存のキャッシュデータをupdated_productsにコピー
    for item_id, product in cached_products.items():
        updated_products[item_id] = product
    
    # 新規商品を処理し、最大10個に制限
    for product in new_products:
        item_id = product['id']
        is_new_product = item_id not in updated_products

        if is_new_product and newly_added_count < 10:
            # 新規商品の場合は、AIメタデータと分析を両方生成
            updated_products[item_id] = product
            try:
                ai_summary, tags, sub_category = generate_ai_metadata(product['name'], product['description'])
                product['ai_summary'] = ai_summary
                product['tags'] = tags
                if 'category' in product and isinstance(product['category'], dict):
                    product['category']['sub'] = sub_category
            except Exception as e:
                print(f"新規商品のAIメタデータ生成中にエラーが発生しました: {e}")

            try:
                price_history = product.get('price_history', [])
                price_int = int(str(product['price']).replace(',', ''))
                ai_headline, ai_analysis_text = generate_ai_analysis(product['name'], price_int, price_history)
                product['ai_headline'] = ai_headline
                product['ai_analysis'] = ai_analysis_text
            except Exception as e:
                print(f"新規商品のAI分析生成中にエラーが発生しました: {e}")
            
            newly_added_count += 1

    # 既存の商品を更新
    for product in new_products:
        item_id = product['id']
        if item_id in updated_products:
            existing_product = updated_products[item_id]
            price_history = existing_product.get('price_history', [])
            current_date = date.today().isoformat()
            
            try:
                current_price = int(product['price'].replace(',', ''))
            except (ValueError, KeyError):
                current_price = 0
            
            # 価格履歴に新しい日付のデータがなければ追加
            if not price_history or price_history[-1]['date'] != current_date:
                price_history.append({"date": current_date, "price": current_price})

            existing_product['price_history'] = price_history
            
            # 価格が変動したかどうかをチェック
            last_price = price_history[-2]['price'] if len(price_history) > 1 else None
            
            if last_price is not None and current_price != last_price:
                print(f"価格変動を検知しました: {product['name']}。AI分析を更新します。")
                ai_headline, ai_analysis_text = generate_ai_analysis(product['name'], current_price, price_history)
                if ai_headline and ai_headline != "AI分析準備中":
                    existing_product['ai_headline'] = ai_headline
                if ai_analysis_text and ai_analysis_text != "詳細なAI分析は現在準備中です。":
                    existing_product['ai_analysis'] = ai_analysis_text
            else:
                print(f"価格変動なし: {product['name']}。AI分析は更新しません。")
                
            updated_products[item_id] = existing_product

    # AIメタデータと分析を更新（新規・既存問わず）
    for item_id, product in updated_products.items():
        # ai_summaryまたはtagsが空の場合は再生成
        if not product.get('ai_summary') or not product.get('tags') or not product['category'].get('sub'):
            print(f"商品: '{product['name']}' のAIメタデータを再生成中...")
            ai_summary, tags, sub_category = generate_ai_metadata(product['name'], product['description'])
            if ai_summary and ai_summary != "この商品の詳しい説明は準備中です。":
                product['ai_summary'] = ai_summary
            if tags:
                product['tags'] = tags
            if sub_category and 'category' in product and isinstance(product['category'], dict):
                product['category']['sub'] = sub_category
        # categoryのsubが空の場合も生成
        elif 'category' in product and isinstance(product['category'], dict) and not product['category'].get('sub'):
            print(f"商品: '{product['name']}' のサブカテゴリーを生成中...")
            ai_summary, tags, sub_category = generate_ai_metadata(product['name'], product['description'])
            if sub_category and sub_category != "":
                product['category']['sub'] = sub_category
        
    # 新規商品をトップに表示するため、日付を更新
    for item_id, product in updated_products.items():
        if item_id in new_products: # 新規商品はすべての日付を最新にする
            product['date'] = date.today().isoformat()
        else: # 既存商品は、既に更新されている日付を維持
            pass

    final_products = list(updated_products.values())
    save_to_cache(final_products)

    print(f"{CACHE_FILE}が更新されました。現在 {len(final_products)} 個の商品を追跡中です。")
    return final_products

def generate_site(products):
    """products.jsonを読み込み、HTMLファイルを生成する関数"""
    today = date.today().isoformat()
    for product in products:
        if 'date' not in product:
            product['date'] = today
    
    # 既存のキャッシュデータを取得
    cached_products = get_cached_data()
    
    # 新規商品を最上位にソート
    new_product_ids = [p['id'] for p in products if p['id'] not in cached_products]
    
    def product_sort_key(product):
        is_new = product['id'] in new_product_ids
        return (not is_new, product.get('date', '1970-01-01'), product.get('name', ''))
        
    products.sort(key=product_sort_key, reverse=True)


    categories = {}
    for product in products:
        main_cat = product.get('category', {}).get('main', '不明')
        sub_cat = product.get('category', {}).get('sub', '')
        if main_cat not in categories:
            categories[main_cat] = []
        if sub_cat and sub_cat not in categories[main_cat]:
            categories[main_cat].append(sub_cat)

    sorted_main_cats = sorted(categories.keys())

    # 独自のカテゴリを追加
    special_categories = {
        '最安値': sorted(list(set(p.get('category', {}).get('sub', '') for p in products if p.get('category', {}).get('sub', '')))),
        '期間限定セール': sorted(list(set(p.get('category', {}).get('sub', '') for p in products if p.get('tags', []) and any(tag in ['セール', '期間限定'] for tag in p['tags']))))
    }

    def generate_header_footer(current_path, sub_cat_links=None, page_title="お得な買い時を見つけよう！"):
        
        # 相対パスを計算
        base_path = ""
        if 'products' in current_path:
            base_path = ".."
        elif 'category' in current_path:
            # category/main_cat.html -> ..
            # category/special/sub_cat.html -> ../..
            base_path = ".." if len(current_path.split('/')) == 2 else "../.."
        elif 'tags' in current_path:
            base_path = ".." if len(current_path.split('/')) == 2 else "../.."
        else:
            base_path = "."

        main_links_html = f'<a href="{base_path}/tags.html">タグから探す</a><span class="separator">|</span>'
        main_links_html += f'<a href="{base_path}/category/最安値.html">最安値</a><span class="separator">|</span>'
        main_links_html += f'<a href="{base_path}/category/期間限定セール.html">期間限定セール</a><span class="separator">|</span>'

        sub_genre_links = ""
        for mc_link in sorted_main_cats:
            sub_genre_links += f'<a href="{base_path}/category/{mc_link}.html">{mc_link}</a><span class="separator">|</span>'

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
            <input type="text" placeholder="商品名、キーワードで検索..." class="search-input">
            <button class="search-button">🔍</button>
        </div>
    </div>
    <div class="genre-links-container">
        <div class="genre-links">
            {main_links_html}
        </div>
    </div>
    <div class="genre-links-container" style="margin-top: -10px;">
        <div class="genre-links">
            {sub_genre_links}
        </div>
    </div>
"""
        sub_cat_links_html = ""
        if sub_cat_links:
            sub_cat_links_html += '<div class="genre-links sub-genre-links">'
            for sub_cat_link in sorted(sub_cat_links):
                # リンクの空白を削除
                sub_cat_links_html += f'<a href="{sub_cat_link.replace(" ", "")}.html">{sub_cat_link}</a><span class="separator">|</span>'
            sub_cat_links_html += '</div>'
            header_html += f"""
    <div class="sub-genre-links-container" style="margin-top: -10px;">
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
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const priceChartCanvas = document.getElementById('priceChart');
            if (priceChartCanvas) {{
                const dataHistory = JSON.parse(priceChartCanvas.getAttribute('data-history'));
                const dates = dataHistory.map(item => item.date);
                const prices = dataHistory.map(item => item.price);

                new Chart(priceChartCanvas, {{
                    type: 'line',
                    data: {{
                        labels: dates,
                        datasets: [{{
                            label: '価格推移',
                            data: prices,
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1
                        }}]
                    }},
                    options: {{
                        responsive: true,
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
                                    text: '価格（円）'
                                }}
                            }}
                        }}
                    }}
                }});
            }}
        }});
    </script>
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
            if file.endswith('.html') and not file in ['privacy.html', 'disclaimer.html', 'contact.html', 'sitemap.xml', 'index.html', 'style.css', 'script.js']:
                os.remove(os.path.join(root, file))
    if os.path.exists('category'):
        shutil.rmtree('category', ignore_errors=True)
    if os.path.exists('pages'):
        shutil.rmtree('pages', ignore_errors=True)
    if os.path.exists('tags'):
        shutil.rmtree('tags', ignore_errors=True)
    if os.path.exists('products'):
        shutil.rmtree('products', ignore_errors=True)

    os.makedirs('products', exist_ok=True)
    os.makedirs('category', exist_ok=True)
    os.makedirs('tags', exist_ok=True)

    # 一般カテゴリのページ生成
    for main_cat, sub_cats in categories.items():
        main_cat_products = [p for p in products if p.get('category', {}).get('main', '') == main_cat]
        page_path = f"category/{main_cat}.html" # URLをシンプルに
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
    <img src="{product.get('image_url', '')}" alt="{product.get('name', '商品画像')}">
    <div class="product-info">
        <h3 class="product-name">{product.get('name', '商品名')[:20] + '...' if len(product.get('name', '')) > 20 else product.get('name', '商品名')}</h3>
        <p class="product-price">{int(product.get('price', 0)):,}円</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product.get('ai_headline', 'AI分析準備中')}</div>
    </div>
</a>
            """
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + products_html + "</div></div>" + footer)
        print(f"category/{main_cat}.html が生成されました。")

    # 独自のカテゴリのページ生成
    for special_cat, sub_cats in special_categories.items():
        page_path = f"category/{special_cat}.html"
        header, footer = generate_header_footer(page_path, sub_cat_links=sub_cats, page_title=f"{special_cat}の商品一覧")

        main_content_html = f"""
    <main class="container">
        <div class="ai-recommendation-section">
            <h2 class="ai-section-title">{special_cat}のサブカテゴリー一覧</h2>
            <div class="genre-links sub-genre-links">
            {"".join([f'<a href="{sub_cat.replace(" ", "")}.html">{sub_cat}</a><span class="separator">|</span>' for sub_cat in sorted(sub_cats)])}
            </div>
        </div>
    """
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + "</main>" + footer)
        print(f"category/{special_cat}.html が生成されました。")

        for sub_cat in sub_cats:
            sub_cat_file_name = f"{sub_cat.replace(' ', '')}.html"
            page_path = f"category/{special_cat}/{sub_cat_file_name}"
            os.makedirs(os.path.dirname(page_path), exist_ok=True)
            
            # 最安値カテゴリの商品フィルタリング
            if special_cat == '最安値':
                filtered_products = [p for p in products if p.get('category', {}).get('sub', '') == sub_cat]
                filtered_products.sort(key=lambda x: int(x.get('price', 0)))  # 価格が低い順にソート
            else:  # 期間限定セールなど
                filtered_products = [p for p in products if p.get('category', {}).get('sub', '') == sub_cat and any(tag in ['セール', '期間限定'] for tag in p.get('tags', []))]

            header, footer = generate_header_footer(page_path, page_title=f"{special_cat} > {sub_cat}の商品一覧")
            main_content_html = f"""
    <main class="container">
        <div class="ai-recommendation-section">
            <h2 class="ai-section-title">{sub_cat}のお得な商品一覧</h2>
            <div class="product-grid">
            """
            products_html = ""
            for product in filtered_products:
                link_path = os.path.relpath(product['page_url'], os.path.dirname(page_path))
                products_html += f"""
<a href="{link_path}" class="product-card">
    <img src="{product.get('image_url', '')}" alt="{product.get('name', '商品画像')}">
    <div class="product-info">
        <h3 class="product-name">{product.get('name', '商品名')[:20] + '...' if len(product.get('name', '')) > 20 else product.get('name', '商品名')}</h3>
        <p class="product-price">{int(product.get('price', 0)):,}円</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product.get('ai_headline', 'AI分析準備中')}</div>
    </div>
</a>
                """
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(header + main_content_html + products_html + "</div></div>" + footer)
            print(f"category/{special_cat}/{sub_cat_file_name} が生成されました。")


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
    <img src="{product.get('image_url', '')}" alt="{product.get('name', '商品画像')}">
    <div class="product-info">
        <h3 class="product-name">{product.get('name', '商品名')[:20] + '...' if len(product.get('name', '')) > 20 else product.get('name', '商品名')}</h3>
        <p class="product-price">{int(product.get('price', 0)):,}円</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product.get('ai_headline', 'AI分析準備中')}</div>
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
        header, footer = generate_header_footer(page_path, page_title=f"{product.get('name', '商品名')}の買い時情報")
        ai_analysis_block_html = f"""
            <div class="ai-analysis-block">
                <div class="ai-analysis-text">
                    <h2>AIによる買い時分析</h2>
                    <p>{product.get('ai_analysis', '詳細なAI分析は現在準備中です。')}</p>
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
        # 価格履歴が空の場合、現在価格を最初のデータとして追加
        price_history_for_chart = product.get('price_history', [])
        if not price_history_for_chart:
            try:
                price_int = int(str(product['price']).replace(',', ''))
                price_history_for_chart = [{"date": date.today().isoformat(), "price": price_int}]
            except (ValueError, KeyError):
                price_history_for_chart = []

        price_history_json = json.dumps(price_history_for_chart)
        price_chart_html = f"""
        <div class="price-chart-section">
            <h2>価格推移グラフ</h2>
            <canvas id="priceChart" data-history='{price_history_json}'></canvas>
        </div>
        """
        purchase_button_html = f"""
        <div class="purchase-buttons">
            <a href="{product.get('rakuten_url', '')}" class="purchase-button rakuten" target="_blank">楽天市場で購入する</a>
        </div>
        """

        affiliate_links_html = f"""
            <div class="lowest-price-section">
                <p class="lowest-price-label">最安値ショップをチェック！</p>
                <div class="lowest-price-buttons">
                    <a href="{AMAZON_AFFILIATE_LINK}" class="btn shop-link amazon" target="_blank">Amazonで見る</a>
                    <a href="{product.get("rakuten_url", "https://www.rakuten.co.jp/")}" class="btn shop-link rakuten" target="_blank">楽天市場で見る</a>
                    <a href="{product.get("yahoo_url", "https://shopping.yahoo.co.jp/")}" class="btn shop-link yahoo" target="_blank">Yahoo!ショッピングで見る</a>
                </div>
            </div>
        """
        item_html_content = f"""
<main class="container">
    <div class="product-detail">
        <div class="item-detail">
            <div class="item-image">
                <img src="{product.get('image_url', '')}" alt="{product.get('name', '商品画像')}" class="main-product-image">
            </div>
            <div class="item-info">
                <h1 class="item-name">{product.get('name', '商品名')}</h1>
                <p class="item-category">カテゴリ：<a href="{os.path.relpath('category/' + product.get('category', {}).get('main', '') + '.html', os.path.dirname(page_path))}">{product.get('category', {}).get('main', '')}</a> &gt; <a href="{os.path.relpath('category/' + product.get('category', {}).get('sub', '').replace(' ', '') + '.html', os.path.dirname(page_path))}">{product.get('category', {}).get('sub', '')}</a></p>
                <div class="price-section">
                    <p class="current-price">現在の価格：<span>{int(product.get('price', 0)):,}</span>円</p>
                </div>
                <div class="ai-recommendation-section">
                    <div class="price-status-title">💡注目ポイント</div>
                    <div class="price-status-content ai-analysis">{product.get('ai_headline', 'AI分析準備中')}</div>
                </div>
                {purchase_button_html}
                {ai_analysis_block_html}
                {price_chart_html}
                {affiliate_links_html}
                <div class="item-description">
                    <h2>AIによる商品ハイライト</h2>
                    <p>{product.get('ai_summary', 'この商品の詳しい説明は準備中です。')}</p>
                </div>
                {specs_html}
                <div class="product-tags">
                    {"".join([f'<a href="{os.path.relpath("tags/" + tag + ".html", os.path.dirname(page_path))}" class="tag-button">#{tag}</a>' for tag in product.get('tags', [])])}
                </div>
            </div>
        </div>
    </div>
</main>
"""
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + item_html_content + footer)
        print(f"{page_path} が生成されました。")

    all_tags = sorted(list(set(tag for product in products for tag in product.get('tags', []))))

    if all_tags:
        os.makedirs('tags', exist_ok=True)
        tag_list_html_content = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">タグから探す</h2>
        <div class="product-tags all-tags-list">
            {"".join([f'<a href="{tag}.html" class="tag-button">#{tag}</a>' for tag in all_tags])}
        </div>
    </div>
</main>
"""
        tag_header, tag_footer = generate_header_footer('tags/index.html', page_title="タグ一覧")
        with open('tags/index.html', 'w', encoding='utf-8') as f:
            f.write(tag_header + tag_list_html_content + tag_footer)
        print("タグ一覧ページ: tags/index.html が生成されました。")

        for tag in all_tags:
            tag_page_path = f'tags/{tag}.html'
            tag_products = [product for product in products if tag in product.get('tags', [])]
            tag_page_content = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">#{tag} の商品一覧</h2>
        <div class="product-grid">
            {"".join([f'''
            <a href="{os.path.relpath(product.get('page_url', ''), os.path.dirname(tag_page_path))}" class="product-card">
                <img src="{product.get('image_url', '')}" alt="{product.get('name', '商品画像')}">
                <div class="product-info">
                    <h3 class="product-name">{product.get('name', '商品名')[:20] + '...' if len(product.get('name', '')) > 20 else product.get('name', '商品名')}</h3>
                    <p class="product-price">{int(product.get('price', 0)):,}円</p>
                    <div class="price-status-title">💡注目ポイント</div>
                    <div class="price-status-content ai-analysis">{product.get('ai_headline', 'AI分析準備中')}</div>
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
            <p>当サイトは、Amazon.co.jp、楽天市場、Yahoo!ショッピングを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定されたアフィリエイトプログラムの参加者です。</p>
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
        # 独自のカテゴリを追加
        for main_cat, sub_cats in special_categories.items():
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}category/{main_cat}.html</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>daily</changefreq>\n'
            sitemap_content += '    <priority>0.8</priority>\n'
            sitemap_content += '  </url>\n'
            for sub_cat in sub_cats:
                sitemap_content += '  <url>\n'
                sitemap_content += f'    <loc>{base_url}category/{sub_cat.replace(" ", "")}.html</loc>\n'
                sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
                sitemap_content += '    <changefreq>daily</changefreq>\n'
                sitemap_content += '    <priority>0.7</priority>\n'
                sitemap_content += '  </url>\n'
        # 一般カテゴリを追加
        for main_cat, sub_cats in categories.items():
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}category/{main_cat}.html</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>daily</changefreq>\n'
            sitemap_content += '    <priority>0.8</priority>\n'
            sitemap_content += '  </url>\n'
            for sub_cat in sub_cats:
                sitemap_content += '  <url>\n'
                sitemap_content += f'    <loc>{base_url}category/{sub_cat.replace(" ", "")}.html</loc>\n'
                sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
                sitemap_content += '    <changefreq>daily</changefreq>\n'
                sitemap_content += '    <priority>0.7</priority>\n'
                sitemap_content += '  </url>\n'
        for tag in all_tags:
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}tags/{tag}.html</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>daily</changefreq>\n'
            sitemap_content += '    <priority>0.6</priority>\n'
            sitemap_content += '  </url>\n'
        for product in products:
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}{product.get("page_url", "")}</loc>\n'
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
    products = update_products_csv(rakuten_products)
    generate_site(products)
