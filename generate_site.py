# -*- coding: utf-8 -*-
import json
import math
import os
import shutil
import time
from datetime import date
import requests
import csv
import urllib.parse

# カテゴリーとサブカテゴリーを定義するリスト
PRODUCT_CATEGORIES = {
    "パソコン・周辺機器": [
        "ノートパソコン", "デスクトップPC", "キーボード", "マウス",
        "モニター", "プリンター", "ルーター", "ゲーミングPC"
    ],
    "家電": [
        "カメラ", "オーディオ", "キッチン家電", "美容家電",
        "照明", "掃除機", "テレビ", "冷蔵庫", "洗濯機"
    ],
    "ゲーム・おもちゃ": [
        "ゲーム機", "ゲームソフト", "フィギュア", "ドローン",
        "知育玩具", "ボードゲーム"
    ]
}

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
YAHOO_TOP_PAGE_AD_URL = "//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3754088&pid=892109155&vc_url=https%3A%2F%2Fshopping.yahoo.co.jp%2F"

def get_cached_data():
    """CSVファイルからキャッシュされた商品データを読み込む"""
    cached_data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if 'id' not in reader.fieldnames:
                    print("警告: CSVファイルに'id'ヘッダーが見つかりません。")
                    return {}

                for row in reader:
                    if not row.get('id'):
                        continue
                    product_id = row['id']

                    # JSON文字列として保存されているデータを正しくパース
                    for key in ['price_history', 'tags', 'category']:
                        if key in row and isinstance(row[key], str):
                            try:
                                row[key] = json.loads(row[key].replace("'", '"'))
                            except (json.JSONDecodeError, TypeError):
                                print(f"警告: ID {product_id} の {key} パースに失敗しました。")
                                row[key] = [] if key in ['price_history', 'tags'] else {"main": "不明", "sub": ""}
                    
                    if 'category' in row and not isinstance(row['category'], dict):
                        row['category'] = {"main": "不明", "sub": ""}

                    cached_data[product_id] = row
        except csv.Error as e:
            print(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
            return {}
    return cached_data

def save_to_cache(products):
    """商品データをCSVファイルに保存する"""
    if not products:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
        return

    fieldnames = set()
    for p in products:
        fieldnames.update(p.keys())
    
    # フィールド名を特定の順序でソート
    preferred_order = ['id', 'name', 'price', 'image_url', 'rakuten_url', 'yahoo_url', 'amazon_url', 'page_url', 'category', 'ai_headline', 'ai_analysis', 'description', 'ai_summary', 'tags', 'date', 'main_ec_site', 'price_history', 'source']
    fieldnames = sorted(list(fieldnames), key=lambda x: preferred_order.index(x) if x in preferred_order else len(preferred_order))

    with open(CACHE_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for product in products:
            product_to_write = product.copy()
            # 辞書やリストはJSON文字列に変換して保存
            product_to_write['price_history'] = json.dumps(product_to_write.get('price_history', []), ensure_ascii=False)
            product_to_write['tags'] = json.dumps(product_to_write.get('tags', []), ensure_ascii=False)
            product_to_write['category'] = json.dumps(product_to_write.get('category', {"main": "不明", "sub": ""}), ensure_ascii=False)
            writer.writerow(product_to_write)

def _call_openai_api(prompt, response_format):
    """OpenAI APIを呼び出す共通関数"""
    if not OPENAI_API_KEY:
        print("警告: OpenAI APIキーが設定されていません。")
        return None

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": "あなたはプロのAIアシスタントです。"}, {"role": "user", "content": prompt}],
        "response_format": {"type": response_format}
    }

    try:
        response = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(payload), timeout=20)
        response.raise_for_status()
        result = response.json()
        return json.loads(result.get('choices', [{}])[0].get('message', {}).get('content', '{}'))
    except requests.exceptions.Timeout:
        print("OpenAI APIへのリクエストがタイムアウトしました。")
    except requests.exceptions.RequestException as e:
        print(f"OpenAI APIへのリクエスト中にエラーが発生しました: {e}")
    except (IndexError, KeyError, json.JSONDecodeError) as e:
        print(f"OpenAI APIの応答形式が不正です: {e}")
    return None

def map_to_defined_category(sub_category, product_name):
    """
    AIが生成したサブカテゴリーを、定義済みリストにマッピングする。
    一致するものがなければ、商品名からメインカテゴリーを推測する。
    """
    # AIが生成したサブカテゴリーが定義済みリストに存在するかチェック
    for main_cat, sub_cats in PRODUCT_CATEGORIES.items():
        if sub_category in sub_cats:
            return main_cat, sub_category
        # 部分一致でも対応できるようにする
        if any(sc in product_name.lower() for sc in sub_cats):
            return main_cat, sub_category

    # 定義済みリストに一致するサブカテゴリーがない場合
    for main_cat in PRODUCT_CATEGORIES.keys():
        if main_cat.replace('・', '').replace(' ', '') in product_name.lower().replace('・', '').replace(' ', ''):
            # メインカテゴリーが商品名に含まれていれば、そのカテゴリーに分類
            return main_cat, sub_category
            
    # いずれにも当てはまらない場合、対象外とする
    return 'その他', '不明'


def generate_ai_metadata(product_name, product_description):
    """商品の要約、タグ、サブカテゴリーを生成する"""
    prompt = f"""
    以下の商品情報をもとに、ウェブサイトのコンテンツとして最適な、簡潔で魅力的な要約、関連するタグ（3〜5個）、そして適切なサブカテゴリー（1つ）を日本語で生成してください。
    回答は必ずJSON形式で提供してください。JSONは「summary」、「tags」、「sub_category」の3つのキーを持ちます。

    商品名: {product_name}
    商品説明: {product_description}

    要約の文章には、SEOを意識した「格安」「最安値」「セール」「割引」などのキーワードを自然に含めてください。
    タグは商品の特徴や用途を表す単語をリスト形式で生成してください。
    サブカテゴリーは、商品のジャンルを細分化した単一の単語を生成してください。
    """
    metadata = _call_openai_api(prompt, "json_object")
    if metadata:
        ai_sub_category = metadata.get('sub_category', "")
        main_cat, sub_cat = map_to_defined_category(ai_sub_category, product_name)
        return metadata.get('summary', "この商品の詳しい説明は準備中です。"), metadata.get('tags', []), main_cat, sub_cat
    
    # AIが失敗した場合も、商品名からカテゴリーを推測
    main_cat, sub_cat = map_to_defined_category("", product_name)
    return "この商品の詳しい説明は準備中です。", [], main_cat, sub_cat

def generate_ai_analysis(product_name, product_price, price_history):
    """商品の価格分析テキストを生成する"""
    history_text = f"過去の価格履歴は以下の通りです: {price_history}" if price_history else "価格履歴はありません。"
    prompt = f"""
    あなたは、価格比較の専門家として、消費者に商品の買い時をアドバイスします。回答は必ずJSON形式で提供してください。JSONは「headline」と「analysis」の2つのキーを持ちます。「headline」は商品の買い時を伝える簡潔な一言で、可能であれば具体的な割引率や数字を使って表現してください。「analysis」はなぜ買い時なのかを説明する詳細な文章です。日本語で回答してください。
    {product_name}という商品の現在の価格は{product_price}円です。{history_text}。この商品の価格について、市場の動向を踏まえた分析と買い時に関するアドバイスを日本語で提供してください。特に価格が前回と比べて下がっている場合は、**「最安値」**や**「セール」**といったキーワードを使って買い時を強調してください。
    """
    analysis_data = _call_openai_api(prompt, "json_object")
    if analysis_data:
        return analysis_data.get('headline', 'AI分析準備中'), analysis_data.get('analysis', '詳細なAI分析は現在準備中です。')
    return "AI分析準備中", "詳細なAI分析は現在準備中です。"


def fetch_rakuten_items():
    """楽天APIから複数の商品データを取得する関数"""
    app_id = os.environ.get('RAKUTEN_API_KEY')
    if not app_id:
        print("RAKUTEN_API_KEYが設定されていません。")
        return []

    # 事前定義したカテゴリーに合わせてキーワードを調整
    keywords = ['ノートパソコン', '冷蔵庫', 'デジタルカメラ', 'ゲームソフト']
    all_products = []

    for keyword in keywords:
        url = f"https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706?applicationId={app_id}&keyword={keyword}&format=json&sort=-reviewCount&hits=1"
        try:
            print(f"キーワード '{keyword}' で商品を検索中...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            items = data.get('Items', [])

            if items:
                print(f"'{keyword}' で {len(items)} 件の商品が見つかりました。")
                for item in items:
                    item_data = item['Item']
                    description = item_data.get('itemCaption', '')

                    new_product = {
                        "id": item_data['itemCode'],
                        "name": item_data['itemName'],
                        "price": str(item_data['itemPrice']),
                        "image_url": item_data.get('mediumImageUrls', [{}])[0].get('imageUrl', ''),
                        "rakuten_url": item_data.get('itemUrl', ''),
                        "yahoo_url": YAHOO_AFFILIATE_LINK_BASE + urllib.parse.quote(item_data['itemName']),
                        "amazon_url": AMAZON_AFFILIATE_LINK,
                        "page_url": f"pages/{item_data['itemCode'].replace(':', '_')}.html",
                        "category": {"main": "", "sub": ""},
                        "ai_headline": "",
                        "ai_analysis": "",
                        "description": description,
                        "ai_summary": "",
                        "tags": [],
                        "date": date.today().isoformat(),
                        "main_ec_site": "楽天",
                        "price_history": [],
                        'source': 'rakuten',
                    }
                    all_products.append(new_product)
        except requests.exceptions.RequestException as e:
            print(f"楽天APIへのリクエスト中にエラーが発生しました: {e}")
        except (IndexError, KeyError) as e:
            print(f"楽天APIの応答形式が不正です: {e}")

    print(f"合計 {len(all_products)} 件の商品を取得しました。")
    return all_products


def update_products_csv(new_products):
    """新しい商品データを既存のproducts.jsonに統合・更新する関数"""
    cached_products = get_cached_data()
    updated_products = {}

    for item_id, product in cached_products.items():
        if 'source' not in product:
            product['source'] = 'rakuten'
        updated_products[item_id] = product

    final_products_to_save = []
    for product in new_products:
        item_id = product['id']
        is_new = item_id not in updated_products
        is_price_changed = False
        current_date = date.today().isoformat()
        try:
            current_price = int(str(product['price']).replace(',', ''))
        except (ValueError, KeyError):
            print(f"価格の変換に失敗しました: {product.get('price', '不明')}")
            continue

        product['source'] = 'rakuten'

        if is_new:
            # 新規商品の処理
            product['price_history'] = [{"date": current_date, "price": current_price}]
            print(f"新規商品 '{product['name']}' を追加します。AIデータを生成します。")
            ai_summary, tags, main_cat, sub_cat = generate_ai_metadata(product['name'], product['description'])
            
            # 定義済みカテゴリーにない場合はスキップ
            if main_cat == 'その他':
                print(f"商品 '{product['name']}' は定義済みカテゴリーに属さないためスキップします。")
                continue
                
            product['ai_summary'] = ai_summary
            product['tags'] = tags
            product['category']['main'] = main_cat
            product['category']['sub'] = sub_cat
            
            ai_headline, ai_analysis_text = generate_ai_analysis(product['name'], current_price, product['price_history'])
            product['ai_headline'] = ai_headline
            product['ai_analysis'] = ai_analysis_text
            final_products_to_save.append(product)

        else:
            # 既存商品の処理
            existing_product = updated_products[item_id]
            price_history = existing_product.get('price_history', [])
            
            if not price_history or price_history[-1].get('date') != current_date:
                price_history.append({"date": current_date, "price": current_price})
            
            last_price = price_history[-2]['price'] if len(price_history) >= 2 else None
            if last_price and last_price != current_price:
                is_price_changed = True
            
            existing_product['price_history'] = price_history
            existing_product['price'] = str(current_price)

            if not existing_product.get('ai_summary') or not existing_product.get('tags') or not existing_product['category'].get('sub'):
                print(f"商品 '{existing_product['name']}' のAIメタデータを補完中...")
                ai_summary, tags, main_cat, sub_cat = generate_ai_metadata(existing_product['name'], existing_product['description'])
                
                if main_cat == 'その他':
                    print(f"商品 '{existing_product['name']}' は定義済みカテゴリーに属さないためスキップします。")
                    continue
                
                existing_product['ai_summary'] = ai_summary if not existing_product.get('ai_summary') else existing_product['ai_summary']
                existing_product['tags'] = tags if not existing_product.get('tags') else existing_product['tags']
                existing_product['category']['main'] = main_cat if not existing_product['category'].get('main') else existing_product['category']['main']
                existing_product['category']['sub'] = sub_cat if not existing_product['category'].get('sub') else existing_product['category']['sub']

            if is_price_changed or not existing_product.get('ai_headline') or not existing_product.get('ai_analysis'):
                print(f"商品 '{existing_product['name']}' のAI分析を更新/生成中...")
                ai_headline, ai_analysis_text = generate_ai_analysis(existing_product['name'], current_price, price_history)
                existing_product['ai_headline'] = ai_headline
                existing_product['ai_analysis'] = ai_analysis_text
            else:
                print(f"商品 '{existing_product['name']}' の価格に変動がないため、AI分析はスキップされました。")
            
            final_products_to_save.append(existing_product)
    
    save_to_cache(final_products_to_save)
    print(f"{CACHE_FILE}が更新されました。現在 {len(final_products_to_save)} 個の商品を追跡中です。")
    return final_products_to_save

def generate_header_footer(current_path, page_title="お得な買い時を見つけよう！"):
    """ヘッダーとフッターのHTMLを生成する"""
    # どの階層にいてもサイトのルートディレクトリへの相対パスを正しく計算する
    # 例：`pages/product.html` -> `../`
    #    `category/pc/index.html` -> `../../`
    #    `index.html` -> `./`
    # `os.path.relpath`は`index.html`が基準なので、
    # `os.path.dirname(current_path)`が`pages`なら`..`を、`category/pc`なら`../..`を返す
    # ルートディレクトリからのパスを生成する
    rel_path_to_root = os.path.relpath('.', os.path.dirname(current_path))
    if rel_path_to_root == '.':
        base_path = './'
    else:
        base_path = rel_path_to_root + '/'

    # ハードコードされたカテゴリリンクを例示
    main_links = [
        ("タグから探す", f"{base_path}tags/index.html"),
        ("最安値", f"{base_path}category/最安値/index.html"),
        ("期間限定セール", f"{base_path}category/期間限定セール/index.html")
    ]
    main_category_links = [
        (cat, f"{base_path}category/{cat}/index.html") for cat in PRODUCT_CATEGORIES.keys()
    ]
    
    def generate_links_html(links):
        return "".join([f'<a href="{url}">{text}</a><span class="separator">|</span>' for text, url in links])

    header_html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>カイドキ-ナビ | {page_title}</title>
    <link rel="stylesheet" href="{base_path}style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <meta name="google-site-verification" content="OmUuOjcxi7HXBKe47sd0WPbzCfbCOFbPj_iueHBk2qo" />
</head>
<body>
    <header>
        <div class="container">
            <h1><a href="{base_path}">カイドキ-ナビ</a></h1>
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
            {generate_links_html(main_links)}
        </div>
    </div>
    <div class="genre-links-container" style="margin-top: -10px;">
        <div class="genre-links">
            {generate_links_html(main_category_links)}
        </div>
    </div>
    """
    
    footer_html = f"""
    </main>
    <footer>
        <p>&copy; 2025 カイドキ-ナビ. All Rights Reserved.</p>
        <div class="footer-links">
            <a href="{base_path}privacy.html">プライバシーポリシー</a>
            <a href="{base_path}disclaimer.html">免責事項</a>
            <a href="{base_path}contact.html">お問い合わせ</a>
        </div>
    </footer>
    <script src="{base_path}script.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const priceChartCanvas = document.getElementById('priceChart');
            if (priceChartCanvas) {{
                try {{
                    const dataHistory = JSON.parse(priceChartCanvas.getAttribute('data-history'));
                    if (dataHistory && Array.isArray(dataHistory) && dataHistory.length > 0) {{
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
                }} catch (e) {{
                    console.error('価格グラフのレンダリングに失敗しました:', e);
                }}
            }}
        }});
    </script>
</body>
</html>"""
    return header_html, footer_html

def generate_product_card_html(product, page_path):
    """商品カードのHTMLを生成する"""
    # 商品カードのリンクは現在のページからの相対パスで良い
    link_path = os.path.relpath(product['page_url'], os.path.dirname(page_path))
    return f"""
<a href="{link_path}" class="product-card">
    <img src="{product.get('image_url', '')}" alt="{product.get('name', '商品画像')}">
    <div class="product-info">
        <h3 class="product-name">{product.get('name', '商品名')[:20] + '...' if len(product.get('name', '')) > 20 else product.get('name', '商品名')}</h3>
        <p class="product-price">{int(product.get('price', 0)):,}円</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product.get('ai_headline', 'AI分析準備中')}</div>
    </div>
</a>"""

def generate_site(products):
    """products.jsonを読み込み、HTMLファイルを生成する関数"""
    today = date.today().isoformat()
    for product in products:
        if 'date' not in product:
            product['date'] = today
    products.sort(key=lambda p: p.get('date', '1970-01-01'), reverse=True)

    # カテゴリーを事前に定義したリストから取得
    categories = PRODUCT_CATEGORIES

    # 既存の生成ディレクトリをクリーンアップ
    for dir_name in ['pages', 'category', 'tags']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name, ignore_errors=True)
        os.makedirs(dir_name, exist_ok=True)
    
    # メインページの生成
    total_pages = math.ceil(len(products) / PRODUCTS_PER_PAGE)
    for i in range(total_pages):
        start_index = i * PRODUCTS_PER_PAGE
        end_index = start_index + PRODUCTS_PER_PAGE
        paginated_products = products[start_index:end_index]
        page_num = i + 1
        page_path = 'index.html' if page_num == 1 else f'pages/page{page_num}.html'
        
        products_html = "".join([generate_product_card_html(p, page_path) for p in paginated_products])
        
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

        main_content_html = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">今が買い時！お得な注目アイテム</h2>
        <div class="product-grid">
            {products_html}
        </div>
        {pagination_html}
    </div>
</main>
"""
        header, footer = generate_header_footer(page_path)
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + footer)
        print(f"{page_path} が生成されました。")
    
    # カテゴリーごとのページ生成
    for main_cat, sub_cats in categories.items():
        main_cat_products = [p for p in products if p.get('category', {}).get('main', '') == main_cat]
        page_path = f"category/{main_cat}/index.html"
        os.makedirs(os.path.dirname(page_path), exist_ok=True)
        products_html = "".join([generate_product_card_html(p, page_path) for p in main_cat_products])
        main_content_html = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">{main_cat}の商品一覧</h2>
        <div class="product-grid">
            {products_html}
        </div>
    </div>
</main>
"""
        header, footer = generate_header_footer(page_path, page_title=f"{main_cat}の商品一覧")
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + footer)
        print(f"category/{main_cat}/index.html が生成されました。")
        
    for sub_cat in sub_cats:
        sub_cat_products = [p for p in products if p.get('category', {}).get('sub', '') == sub_cat]
        
        # 商品が1件以上ある場合のみページを生成する
        if sub_cat_products:
            sub_cat_file_name = f"{sub_cat.replace(' ', '')}.html"
            page_path = f"category/{main_cat}/{sub_cat_file_name}"
            products_html = "".join([generate_product_card_html(p, page_path) for p in sub_cat_products])
            main_content_html = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">{sub_cat}の商品一覧</h2>
        <div class="product-grid">
            {products_html}
        </div>
    </div>
</main>
"""
            header, footer = generate_header_footer(page_path, page_title=f"{sub_cat}の商品一覧")
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(header + main_content_html + footer)
            print(f"{page_path} が生成されました。")
        else:
            print(f"警告: サブカテゴリー '{sub_cat}' に該当する商品がないため、ページ生成をスキップしました。")

    # 特別カテゴリーのページ生成
    special_categories = {
        '最安値': sorted(list(set(p.get('category', {}).get('sub', '') for p in products if p.get('category', {}).get('sub', '')))),
        '期間限定セール': sorted(list(set(p.get('category', {}).get('sub', '') for p in products if p.get('tags', []) and any(tag in ['セール', '期間限定'] for tag in p['tags']))))
    }
    for special_cat, _ in special_categories.items():
        page_path = f"category/{special_cat}/index.html"
        os.makedirs(os.path.dirname(page_path), exist_ok=True)
        
        if special_cat == '最安値':
            filtered_products = sorted([p for p in products], key=lambda x: int(x.get('price', 0)))
        else: # 期間限定セール
            filtered_products = [p for p in products if p.get('tags', []) and any(tag in ['セール', '期間限定'] for tag in p['tags'])]

        products_html = "".join([generate_product_card_html(p, page_path) for p in filtered_products])
        main_content_html = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">{special_cat}のお得な商品一覧</h2>
        <div class="product-grid">
            {products_html}
        </div>
    </div>
</main>
"""
        header, footer = generate_header_footer(page_path, page_title=f"{special_cat}の商品一覧")
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + footer)
        print(f"category/{special_cat}/index.html が生成されました。")

    # タグごとのページ生成
    all_tags = sorted(list(set(tag for product in products for tag in product.get('tags', []))))
    for tag in all_tags:
        # タグ名に含まれる特殊文字を安全な文字に置き換える
        safe_tag_name = tag.replace('/', '_').replace('\\', '_')
        
        tagged_products = [p for p in products if tag in p.get('tags', [])]
        tag_path = f"tags/{safe_tag_name}.html"  # 安全なタグ名を使用
        
        products_html = "".join([generate_product_card_html(p, tag_path) for p in tagged_products])
        main_content_html = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">#{tag}の注目商品</h2>
        <div class="product-grid">
            {products_html}
        </div>
    </div>
</main>
"""
        header, footer = generate_header_footer(tag_path, page_title=f"タグ：#{tag}")
        with open(tag_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + footer)
        print(f"{tag_path} が生成されました。")

    # タグ一覧ページのページネーション
    TAGS_PER_PAGE = 50
    total_tag_pages = math.ceil(len(all_tags) / TAGS_PER_PAGE)
    for i in range(total_tag_pages):
        start_index = i * TAGS_PER_PAGE
        end_index = start_index + TAGS_PER_PAGE
        paginated_tags = all_tags[start_index:end_index]
        page_num = i + 1
        page_path = 'tags/index.html' if page_num == 1 else f'tags/page{page_num}.html'

        # タグ名に特殊文字が含まれていても安全なファイルパスを生成
        tag_links_html = "".join([
            f'<a href="{os.path.relpath("tags/" + t.replace("/", "_").replace(chr(92), "_") + ".html", os.path.dirname(page_path))}" class="tag-button">#{t}</a>'
            for t in paginated_tags
        ])

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

        main_content_html = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">タグから探す</h2>
        <div class="product-tags all-tags-list">
            {tag_links_html}
        </div>
        {pagination_html}
    </div>
</main>
"""
        header, footer = generate_header_footer(page_path, page_title="タグから探す")
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + main_content_html + footer)
        print(f"{page_path} が生成されました。")

    # 商品詳細ページの生成
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
        specs_html = f"""
<div class="item-specs">
    <h2>製品仕様・スペック</h2>
    <p>{product.get('specs', '')}</p>
</div>
""" if "specs" in product else ""

        affiliate_links_html = f"""
<div class="lowest-price-section">
    <p class="lowest-price-label">最安値ショップをチェック！</p>
    <div class="lowest-price-buttons">
        <a href="{AMAZON_AFFILIATE_LINK}" class="btn shop-link amazon" target="_blank">Amazonで見る</a>
        <a href="{product.get("rakuten_url", "https://www.rakuten.co.jp/")}" class="btn shop-link rakuten" target="_blank">楽天市場で見る</a>
        <a href="{YAHOO_TOP_PAGE_AD_URL}" class="btn shop-link yahoo" rel="nofollow" target="_blank">Yahoo!ショッピングで見る</a>
    </div>
</div>
"""

        # 現在のページからルートディレクトリへの相対パスを計算
        rel_path_to_root = os.path.relpath('.', os.path.dirname(page_path))
        if rel_path_to_root == '.':
            base_path = './'
        else:
            base_path = rel_path_to_root + '/'

        item_html_content = f"""
<main class="container">
    <div class="product-detail">
        <div class="item-detail">
            <div class="item-image">
                <img src="{product.get('image_url', '')}" alt="{product.get('name', '商品画像')}" class="main-product-image">
            </div>
            <div class="item-info">
                <h1 class="item-name">{product.get('name', '商品名')}</h1>
                <p class="item-category">カテゴリ：<a href="{base_path}category/{product.get('category', {}).get('main', '')}/index.html">{product.get('category', {}).get('main', '')}</a> &gt; <a href="{base_path}category/{product.get('category', {}).get('main', '')}/index.html">{product.get('category', {}).get('sub', '')}</a></p>
                <div class="price-section">
                    <p class="current-price">現在の価格：<span>{int(product.get('price', 0)):,}</span>円</p>
                </div>
                <div class="ai-recommendation-section">
                    <div class="price-status-title">💡注目ポイント</div>
                    <div class="price-status-content ai-analysis">{product.get('ai_headline', 'AI分析準備中')}</div>
                    <div class="product-card-buttons-full">
                        <a href="{product.get("rakuten_url", "https://www.rakuten.co.jp/")}" class="btn shop-link rakuten" target="_blank">楽天市場で購入する</a>
                    </div>
                </div>
                {affiliate_links_html}
                {ai_analysis_block_html}
                {price_chart_html}
                <div class="item-description">
                    <h2>AIによる商品ハイライト</h2>
                    <p>{product.get('ai_summary', 'この商品の詳しい説明は準備中です。')}</p>
                </div>
                {specs_html}
                <div class="product-tags">
                    {"".join([f'<a href="{base_path}tags/{tag.replace("/", "_").replace(chr(92), "_")}.html" class="tag-button">#{tag}</a>' for tag in product.get("tags", [])])}
                </div>
            </div>
        </div>
    </div>
</main>
"""
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + item_html_content + footer)
        print(f"{page_path} が生成されました。")
        
    # sitemap.xmlの生成
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    base_url = "https://your-website.com/"
    sitemap_urls = [
        (base_url, 'daily', '1.0'),
        (f'{base_url}privacy.html', 'monthly', '0.5'),
        (f'{base_url}disclaimer.html', 'monthly', '0.5'),
        (f'{base_url}contact.html', 'monthly', '0.5')
    ]

    for product in products:
        sitemap_urls.append((f'{base_url}{product.get("page_url", "")}', 'daily', '0.6'))
    
    # ページネーションページを追加
    total_pages = math.ceil(len(products) / PRODUCTS_PER_PAGE)
    for i in range(2, total_pages + 1):
        sitemap_urls.append((f'{base_url}pages/page{i}.html', 'daily', '0.8'))

    # カテゴリーページを追加
    for main_cat in PRODUCT_CATEGORIES.keys():
        sitemap_urls.append((f'{base_url}category/{main_cat}/', 'daily', '0.8'))
        for sub_cat in PRODUCT_CATEGORIES.get(main_cat, []):
            sitemap_urls.append((f'{base_url}category/{main_cat}/{sub_cat.replace(" ", "")}.html', 'daily', '0.7'))
    
    for special_cat in ['最安値', '期間限定セール']:
        sitemap_urls.append((f'{base_url}category/{special_cat}/', 'daily', '0.8'))

    # タグページを追加
    all_tags_sitemap = sorted(list(set(tag for product in products for tag in product.get('tags', []))))
    for tag in all_tags_sitemap:
        safe_tag_name = tag.replace("/", "_").replace("\\", "_")
        sitemap_urls.append((f'{base_url}tags/{safe_tag_name}.html', 'daily', '0.6'))
    
    # タグ一覧ページを追加
    total_tag_pages_sitemap = math.ceil(len(all_tags_sitemap) / TAGS_PER_PAGE)
    for i in range(2, total_tag_pages_sitemap + 1):
        sitemap_urls.append((f'{base_url}tags/page{i}.html', 'daily', '0.6'))

    for url, changefreq, priority in sitemap_urls:
        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>{url}</loc>\n'
        sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
        sitemap_content += f'    <changefreq>{changefreq}</changefreq>\n'
        sitemap_content += f'    <priority>{priority}</priority>\n'
        sitemap_content += '  </url>\n'
    
    sitemap_content += '</urlset>'
    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write(sitemap_content)
    print("sitemap.xmlが生成されました。")

# 新規追加: 検索用JSONを生成する関数
def generate_search_index(products):
    """JavaScriptが検索に使用するためのJSONデータファイルを生成する"""
    try:
        search_data = []
        for p in products:
            # 検索対象となる情報をひとつの文字列にまとめる
            search_text = f"{p['name']} {p.get('description', '')} {' '.join(p.get('tags', []))} {p.get('category', {}).get('main', '')} {p.get('category', {}).get('sub', '')}"
            
            search_data.append({
                "id": p['id'],
                "name": p['name'],
                "page_url": p['page_url'],
                "image_url": p['image_url'],
                "price": p['price'],
                "ai_headline": p.get('ai_headline', ''),
                "searchable_text": search_text.lower() # 検索を効率化するため、小文字で保存
            })
            
        with open('search_index.json', 'w', encoding='utf-8') as f:
            json.dump(search_data, f, ensure_ascii=False, indent=2)
        print("search_index.json が生成されました。")
    except Exception as e:
        print(f"検索インデックスの生成中にエラーが発生しました: {e}")

# 新規追加: 検索結果ページを生成する関数
def generate_search_results_page():
    """検索結果ページを生成する関数"""
    page_path = "search_results.html"
    header, footer = generate_header_footer(page_path, page_title="検索結果")

    # 検索結果はJavaScriptで動的に表示するため、空のコンテナを用意
    main_content_html = """
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">検索結果</h2>
        <div id="search-results-container" class="product-grid">
            <p id="loading-message">検索中です...</p>
            </div>
    </div>
</main>
"""
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(header + main_content_html + footer)
    print(f"{page_path} が生成されました。")

def main():
    new_products = fetch_rakuten_items()
    final_products = update_products_csv(new_products)
    
    # ここから修正・追加
    generate_search_index(final_products)
    generate_search_results_page()
    
    generate_site(final_products)

if __name__ == '__main__':
    main()
