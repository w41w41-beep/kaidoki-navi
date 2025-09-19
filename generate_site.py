import os
import requests
import json
import pandas as pd
from openai import OpenAI
import re
from datetime import datetime

# APIキーを環境変数から読み込み
# GitHub Actionsで設定したSecretがここに渡されます
RAKUTEN_API_KEY = os.getenv('RAKUTEN_API_KEY')
YAHOO_API_KEY = os.getenv('YAHOO_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# APIクライアントの初期化
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# 楽天APIの設定
RAKUTEN_SEARCH_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
RAKUTEN_AFFILIATE_ID = os.getenv('RAKUTEN_AFFILIATE_ID') # アフィリエイトIDも環境変数から取得

# Yahoo!ショッピングAPIの設定
YAHOO_SEARCH_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
YAHOO_AFFILIATE_ID = os.getenv('YAHOO_AFFILIATE_ID') # アフィリエイトIDも環境変数から取得

# 商品リストを保存するCSVファイル名
PRODUCTS_CSV_FILE = "products.csv"

# カテゴリIDの定義
RAKUTEN_CATEGORY_IDS = {
    "掃除機": "200109",
    "空気清浄機": "200139",
    "ノートPC": "100040",
    "冷蔵庫": "200102",
    "ドライヤー": "200155",
    "照明器具": "100316",
    "洗濯機": "200105",
    "テレビ": "100287",
    "キッチン家電": "200108",
    "イヤホン": "100216"
}

# AIによる情報生成
def generate_ai_info(product_name, description, category):
    """
    OpenAI APIを使って商品の詳細情報、スペック、タグを生成する
    """
    if not OPENAI_API_KEY:
        print("OpenAI APIキーが設定されていません。AI情報生成をスキップします。")
        return {
            "ai_description": "AIによる商品説明は現在準備中です。",
            "specs": "AIによる製品仕様・スペックは現在準備中です。",
            "tags": "[]"
        }

    prompt = f"""
    以下の商品情報をもとに、日本語で商品の詳細、製品仕様、スペック、および5つの重要なタグを生成してください。
    - 商品名: {product_name}
    - 説明: {description}
    - カテゴリ: {category}

    出力はJSON形式で、以下のキーを含めてください。
    1. "ai_description": ユーザーが興味を持つような、簡潔で魅力的な商品説明。
    2. "specs": 重要な製品仕様をリスト形式で列挙してください。
    3. "tags": 商品を説明する重要なキーワードを5つ、JSON形式の配列で提供してください。

    例:
    {{
        "ai_description": "この商品は、...",
        "specs": "- 画面サイズ: 15.6インチ\n- CPU: Intel Core i7\n- メモリ: 16GB\n- ストレージ: 512GB SSD",
        "tags": ["ゲーミング", "高性能", "軽量", "長時間バッテリー", "テレワーク"]
    }}
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates product information in JSON format."},
                {"role": "user", "content": prompt}
            ]
        )
        content = response.choices[0].message.content
        ai_data = json.loads(content)
        
        # specsのフォーマットを調整
        specs_list = ai_data.get("specs", [])
        if isinstance(specs_list, list):
            ai_data["specs"] = "\n".join(f"- {spec}" for spec in specs_list)
        
        return ai_data
    except Exception as e:
        print(f"OpenAI API呼び出し中にエラーが発生しました: {e}")
        return {
            "ai_description": "AIによる商品説明は現在準備中です。",
            "specs": "AIによる製品仕様・スペックは現在準備中です。",
            "tags": "[]"
        }

# 楽天APIから商品情報を取得
def fetch_rakuten_items(category_id, keyword, max_items=10):
    """
    楽天APIから特定カテゴリの商品を取得
    """
    if not RAKUTEN_API_KEY:
        print("楽天APIキーが設定されていません。楽天からの商品取得をスキップします。")
        return []

    params = {
        "format": "json",
        "keyword": keyword,
        "applicationId": RAKUTEN_API_KEY,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "hits": max_items,
        "sort": "standard"
    }

    try:
        response = requests.get(RAKUTEN_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        items = data.get("Items", [])
        
        # 取得した商品情報から必要なデータだけを抽出
        products = []
        for item in items:
            p = item["Item"]
            products.append({
                "id": f"rakuten_{p['itemCode']}",
                "name": p["itemName"],
                "description": p["itemCaption"],
                "price": p["itemPrice"],
                "image_url": p["mediumImageUrls"][0]["imageUrl"].replace("?_ex=128x128", "?_ex=300x300"),
                "url": p["itemUrl"],
                "shop": "楽天市場",
                "category": keyword
            })
        return products
    except requests.exceptions.RequestException as e:
        print(f"楽天API呼び出し中にエラーが発生しました: {e}")
        return []

# Yahoo!ショッピングAPIから商品情報を取得
def fetch_yahoo_items(category_id, keyword, max_items=10):
    """
    Yahoo!ショッピングAPIから特定カテゴリの商品を取得
    """
    if not YAHOO_API_KEY:
        print("Yahoo! APIキーが設定されていません。Yahoo!からの商品取得をスキップします。")
        return []

    params = {
        "appid": YAHOO_API_KEY,
        "query": keyword,
        "results": max_items,
        "affiliateId": YAHOO_AFFILIATE_ID
    }

    try:
        response = requests.get(YAHOO_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        # 商品情報がない場合は空のリストを返す
        if "hits" not in data:
            return []

        products = []
        for item in data["hits"]:
            products.append({
                "id": f"yahoo_{item['id']}",
                "name": item["name"],
                "description": item["description"],
                "price": item["price"],
                "image_url": item["image"]["medium"],
                "url": item["url"],
                "shop": "Yahoo!ショッピング",
                "category": keyword
            })
        return products
    except requests.exceptions.RequestException as e:
        print(f"Yahoo! API呼び出し中にエラーが発生しました: {e}")
        return []

def update_products_csv():
    """
    楽天とYahoo!ショッピングから商品情報を取得し、CSVを更新する。
    既存の商品についてはAI情報生成をスキップする。
    """
    # 既存のCSVを読み込む
    existing_products = {}
    if os.path.exists(PRODUCTS_CSV_FILE):
        df = pd.read_csv(PRODUCTS_CSV_FILE)
        existing_products = {row['id']: row.to_dict() for _, row in df.iterrows()}

    all_products = []
    
    # 楽天から商品情報を取得
    for category_name, category_id in RAKUTEN_CATEGORY_IDS.items():
        all_products.extend(fetch_rakuten_items(category_id, category_name))

    # Yahoo!ショッピングから商品情報を取得
    for category_name, category_id in RAKUTEN_CATEGORY_IDS.items():
        all_products.extend(fetch_yahoo_items(category_id, category_name))

    # 重複を削除し、最新の20件に絞り込む
    unique_products = {p['id']: p for p in all_products}
    
    # 新しい商品、またはAI情報がない商品に対してAIを呼び出す
    products_to_process = list(unique_products.values())[:20] # 最新の20件に絞る
    
    for product in products_to_process:
        product_id = product["id"]
        # 既存の商品データにAI情報が含まれているか確認
        if product_id in existing_products and "ai_description" in existing_products[product_id] and \
           existing_products[product_id]["ai_description"] not in ["AIによる商品説明は現在準備中です。", "AI generated content not available."]:
            # 既存のAI情報を利用
            product["ai_description"] = existing_products[product_id].get("ai_description", "")
            product["specs"] = existing_products[product_id].get("specs", "")
            product["tags"] = existing_products[product_id].get("tags", "[]")
        else:
            # 新規の商品、またはAI情報がない場合は生成
            print(f"AI情報を生成中: {product['name']}")
            ai_data = generate_ai_info(product["name"], product["description"], product["category"])
            product["ai_description"] = ai_data["ai_description"]
            product["specs"] = ai_data["specs"]
            product["tags"] = json.dumps(ai_data["tags"], ensure_ascii=False)

    # 最終的な商品リストをデータフレームに変換
    if not products_to_process:
        print("処理する商品が見つかりませんでした。")
        return

    df_new = pd.DataFrame(products_to_process)
    df_new.to_csv(PRODUCTS_CSV_FILE, index=False, encoding='utf-8-sig')
    print(f"CSVファイルが正常に更新されました: {PRODUCTS_CSV_FILE}")

def _generate_product_detail_pages(products):
    """
    各商品に対応する詳細ページを生成
    """
    os.makedirs("pages", exist_ok=True)
    os.makedirs("category", exist_ok=True)
    os.makedirs("tags", exist_ok=True)
    
    all_tags = set()
    
    for product in products:
        page_path = f"pages/{product['id']}.html"
        
        # AIが生成したタグ
        tags_html = ""
        if "tags" in product and product["tags"]:
            try:
                tags = json.loads(product["tags"])
                all_tags.update(tags)
                tags_html = f"""
                <div class="product-tags my-4 flex flex-wrap gap-2 justify-center sm:justify-start">
                    {''.join([f'<a href="../tags/{tag}.html" class="bg-blue-100 text-blue-800 text-sm font-medium px-2.5 py-0.5 rounded-full hover:bg-blue-200 transition-colors duration-200">#{tag}</a>' for tag in tags])}
                </div>
                """
            except json.JSONDecodeError:
                tags_html = ""

        # HTMLコンテンツの作成
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{product['name']} - 商品詳細</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                body {{
                    font-family: 'Noto Sans JP', sans-serif;
                }}
            </style>
        </head>
        <body class="bg-gray-100 min-h-screen flex flex-col">
            <nav class="bg-white shadow-md">
                <div class="container mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center">
                    <a href="../index.html" class="text-2xl font-bold text-gray-800">カイドキナビ</a>
                    <div class="mt-4 sm:mt-0 flex flex-wrap justify-center sm:justify-start gap-4">
                        <a href="../index.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">トップ</a>
                        <a href="../contact.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">お問い合わせ</a>
                        <a href="../privacy.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">プライバシーポリシー</a>
                        <a href="../disclaimer.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">免責事項</a>
                    </div>
                </div>
            </nav>

            <main class="flex-grow container mx-auto p-4 sm:p-8">
                <div class="bg-white rounded-xl shadow-lg p-6 md:p-10 flex flex-col md:flex-row items-center md:items-start gap-8">
                    <div class="w-full md:w-1/2 flex justify-center items-center">
                        <img src="{product['image_url']}" alt="{product['name']}" class="max-w-full max-h-96 object-contain rounded-lg shadow-md">
                    </div>
                    <div class="w-full md:w-1/2 flex flex-col gap-4">
                        <h1 class="text-3xl sm:text-4xl font-bold text-gray-800">{product['name']}</h1>
                        <p class="text-2xl font-bold text-red-500">{int(product['price']):,}円</p>
                        
                        <div class="mt-4">
                            <h2 class="text-xl font-bold border-b pb-2 mb-2 text-gray-700">商品概要</h2>
                            <p class="text-gray-600 whitespace-pre-wrap">{product['description']}</p>
                        </div>

                        {tags_html}

                        <div class="mt-6">
                            <h2 class="text-xl font-bold border-b pb-2 mb-2 text-gray-700">AIによる詳細分析</h2>
                            <p class="text-gray-600 whitespace-pre-wrap">{product['ai_description']}</p>
                        </div>
                        
                        <div class="mt-6">
                            <h2 class="text-xl font-bold border-b pb-2 mb-2 text-gray-700">AIによる製品仕様・スペック</h2>
                            <p class="text-gray-600 whitespace-pre-wrap">{product['specs']}</p>
                        </div>
                        
                        <a href="{product['url']}" target="_blank" class="mt-8 text-center bg-blue-600 text-white font-bold py-3 px-6 rounded-full hover:bg-blue-700 transition duration-300 w-full text-lg shadow-lg">
                            {product['shop']}で詳細を見る
                        </a>
                    </div>
                </div>
            </main>

            <footer class="bg-gray-800 text-white p-6 mt-12">
                <div class="container mx-auto text-center">
                    <p class="text-sm">&copy; 2025 カイドキナビ. All Rights Reserved.</p>
                </div>
            </footer>
        </body>
        </html>
        """
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    # タグごとのページを生成
    for tag in all_tags:
        tag_path = f"tags/{tag}.html"
        tag_products = [p for p in products if tag in json.loads(p.get("tags", "[]"))]
        
        product_cards = ""
        for p in tag_products:
            product_cards += f"""
            <a href="../pages/{p['id']}.html" class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow duration-300">
                <img src="{p['image_url']}" alt="{p['name']}" class="w-full h-48 object-cover">
                <div class="p-4">
                    <h2 class="text-lg font-semibold text-gray-800">{p['name']}</h2>
                    <p class="text-gray-600">{int(p['price']):,}円</p>
                </div>
            </a>
            """
        
        tag_html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>#{tag} の商品一覧</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                body {{
                    font-family: 'Noto Sans JP', sans-serif;
                }}
            </style>
        </head>
        <body class="bg-gray-100 min-h-screen flex flex-col">
            <nav class="bg-white shadow-md">
                <div class="container mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center">
                    <a href="../index.html" class="text-2xl font-bold text-gray-800">カイドキナビ</a>
                    <div class="mt-4 sm:mt-0 flex flex-wrap justify-center sm:justify-start gap-4">
                        <a href="../index.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">トップ</a>
                        <a href="../contact.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">お問い合わせ</a>
                        <a href="../privacy.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">プライバシーポリシー</a>
                        <a href="../disclaimer.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">免責事項</a>
                    </div>
                </div>
            </nav>
            <main class="flex-grow container mx-auto p-4 sm:p-8">
                <a href="../index.html" class="text-blue-500 hover:underline mb-4 inline-block text-lg">← トップページに戻る</a>
                <h1 class="text-3xl sm:text-4xl font-bold text-gray-800 mb-6">#{tag} の商品一覧</h1>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {product_cards}
                </div>
            </main>
            <footer class="bg-gray-800 text-white p-6 mt-12">
                <div class="container mx-auto text-center">
                    <p class="text-sm">&copy; 2025 カイドキナビ. All Rights Reserved.</p>
                </div>
            </footer>
        </body>
        </html>
        """
        with open(tag_path, "w", encoding="utf-8") as f:
            f.write(tag_html)

def _generate_category_pages(products):
    """
    カテゴリごとのページを生成
    """
    categories = {}
    for product in products:
        category = product.get("category", "その他")
        if category not in categories:
            categories[category] = []
        categories[category].append(product)
    
    for category, category_products in categories.items():
        page_path = f"category/{category}.html"
        product_cards = ""
        for p in category_products:
            product_cards += f"""
            <a href="../pages/{p['id']}.html" class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow duration-300">
                <img src="{p['image_url']}" alt="{p['name']}" class="w-full h-48 object-cover">
                <div class="p-4">
                    <h2 class="text-lg font-semibold text-gray-800">{p['name']}</h2>
                    <p class="text-gray-600">{int(p['price']):,}円</p>
                </div>
            </a>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{category} - 商品一覧</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                body {{
                    font-family: 'Noto Sans JP', sans-serif;
                }}
            </style>
        </head>
        <body class="bg-gray-100 min-h-screen flex flex-col">
            <nav class="bg-white shadow-md">
                <div class="container mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center">
                    <a href="../index.html" class="text-2xl font-bold text-gray-800">カイドキナビ</a>
                    <div class="mt-4 sm:mt-0 flex flex-wrap justify-center sm:justify-start gap-4">
                        <a href="../index.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">トップ</a>
                        <a href="../contact.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">お問い合わせ</a>
                        <a href="../privacy.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">プライバシーポリシー</a>
                        <a href="../disclaimer.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">免責事項</a>
                    </div>
                </div>
            </nav>
            <main class="flex-grow container mx-auto p-4 sm:p-8">
                <a href="../index.html" class="text-blue-500 hover:underline mb-4 inline-block text-lg">← トップページに戻る</a>
                <h1 class="text-3xl sm:text-4xl font-bold text-gray-800 mb-6">{category}の商品一覧</h1>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {product_cards}
                </div>
            </main>
            <footer class="bg-gray-800 text-white p-6 mt-12">
                <div class="container mx-auto text-center">
                    <p class="text-sm">&copy; 2025 カイドキナビ. All Rights Reserved.</p>
                </div>
            </footer>
        </body>
        </html>
        """
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(html_content)

def _generate_index_page(products):
    """
    トップページ（index.html）を生成
    """
    category_html = ""
    for category_name in RAKUTEN_CATEGORY_IDS.keys():
        category_html += f"""
        <a href="category/{category_name}.html" class="py-2 px-4 rounded-full border border-gray-300 text-gray-700 text-sm font-semibold hover:bg-gray-200 transition duration-300">
            {category_name}
        </a>
        """

    product_cards = ""
    for product in products:
        product_cards += f"""
        <a href="pages/{product['id']}.html" class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow duration-300">
            <img src="{product['image_url']}" alt="{product['name']}" class="w-full h-48 object-cover">
            <div class="p-4">
                <h2 class="text-lg font-semibold text-gray-800">{product['name']}</h2>
                <p class="text-gray-600">{int(product['price']):,}円</p>
            </div>
        </a>
        """
        
    # AIによる注目アイテムのセクション
    ai_featured_products = product_cards[:4]
    remaining_products = product_cards[4:]

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>カイドキナビ | 最新の家電・ガジェット</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{
                font-family: 'Noto Sans JP', sans-serif;
            }}
        </style>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col">
        <nav class="bg-white shadow-md">
            <div class="container mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center">
                <a href="index.html" class="text-2xl font-bold text-gray-800">カイドキナビ</a>
                <div class="mt-4 sm:mt-0 flex flex-wrap justify-center sm:justify-start gap-4">
                    <a href="index.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">トップ</a>
                    <a href="contact.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">お問い合わせ</a>
                    <a href="privacy.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">プライバシーポリシー</a>
                    <a href="disclaimer.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">免責事項</a>
                </div>
            </div>
        </nav>

        <header class="text-center py-12 bg-white shadow-sm">
            <h1 class="text-4xl sm:text-5xl font-extrabold text-gray-800 mb-2">最新の人気商品</h1>
            <p class="text-gray-500 text-lg">最新の人気商品とAIによる分析情報をチェック</p>
        </header>
        
        <main class="flex-grow container mx-auto p-4 sm:p-8">
            <section class="mb-12">
                <h2 class="text-2xl sm:text-3xl font-bold text-gray-800 mb-6">カテゴリから探す</h2>
                <div class="flex flex-wrap gap-3 justify-center sm:justify-start">
                    {category_html}
                </div>
            </section>

            <section>
                <h2 class="text-2xl sm:text-3xl font-bold text-gray-800 mb-6">商品一覧</h2>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {product_cards}
                </div>
            </section>
        </main>
        
        <footer class="bg-gray-800 text-white p-6 mt-12">
            <div class="container mx-auto text-center">
                <p class="text-sm">&copy; 2025 カイドキナビ. All Rights Reserved.</p>
            </div>
        </footer>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def _generate_static_pages():
    """
    プライバシーポリシー、免責事項、お問い合わせページを生成
    """
    contact_content = """
    <main class="flex-grow container mx-auto p-4 sm:p-8">
        <div class="bg-white rounded-xl shadow-lg p-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-6">お問い合わせ</h1>
            <p class="text-gray-600">ご質問やご要望がございましたら、以下のメールアドレスまでご連絡ください。</p>
            <p class="mt-4 text-blue-600 font-semibold">メールアドレス: sokux001@gmail.com</p>
        </div>
    </main>
    """
    _write_static_page("contact.html", "お問い合わせ", contact_content)

    privacy_content = """
    <main class="flex-grow container mx-auto p-4 sm:p-8">
        <div class="bg-white rounded-xl shadow-lg p-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-6">プライバシーポリシー</h1>
            <p class="text-gray-600">当サイトは、Googleアナリティクスを使用しています。収集される情報やその利用目的については、Googleのプライバシーポリシーをご確認ください。</p>
            <p class="mt-4 text-gray-600">当サイトは、Amazon.co.jpを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定されたアフィリエイトプログラムである、Amazonアソシエイト・プログラムの参加者です。</p>
        </div>
    </main>
    """
    _write_static_page("privacy.html", "プライバシーポリシー", privacy_content)

    disclaimer_content = """
    <main class="flex-grow container mx-auto p-4 sm:p-8">
        <div class="bg-white rounded-xl shadow-lg p-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-6">免責事項</h1>
            <p class="text-gray-600">本サイトに掲載されている情報は、正確性や完全性を保証するものではありません。</p>
            <p class="mt-4 text-gray-600">アフィリエイトリンクを通じて購入された商品に関するトラブルについては、当サイトは一切の責任を負いません。</p>
        </div>
    </main>
    """
    _write_static_page("disclaimer.html", "免責事項", disclaimer_content)

def _write_static_page(file_name, title, content):
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>カイドキナビ | {title}</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{
                font-family: 'Noto Sans JP', sans-serif;
            }}
        </style>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col">
        <nav class="bg-white shadow-md">
            <div class="container mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center">
                <a href="index.html" class="text-2xl font-bold text-gray-800">カイドキナビ</a>
                <div class="mt-4 sm:mt-0 flex flex-wrap justify-center sm:justify-start gap-4">
                    <a href="index.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">トップ</a>
                    <a href="contact.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">お問い合わせ</a>
                    <a href="privacy.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">プライバシーポリシー</a>
                    <a href="disclaimer.html" class="text-gray-600 hover:text-gray-900 transition-colors duration-300 font-medium">免責事項</a>
                </div>
            </div>
        </nav>
        {content}
        <footer class="bg-gray-800 text-white p-6 mt-12">
            <div class="container mx-auto text-center">
                <p class="text-sm">&copy; 2025 カイドキナビ. All Rights Reserved.</p>
            </div>
        </footer>
    </body>
    </html>
    """
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"{file_name} が正常に生成されました。")


def _generate_sitemap(products):
    """
    サイトマップ（sitemap.xml）を生成
    """
    urls = []
    base_url = "https://w41w41-beep.github.io/kaidoki-navi/" # このURLはGitHub PagesのURLに合わせて変更してください
    
    # トップページ
    urls.append(f"<url><loc>{base_url}</loc><lastmod>{datetime.now().isoformat()}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>")
    
    # カテゴリページ
    for category_name in RAKUTEN_CATEGORY_IDS.keys():
        urls.append(f"<url><loc>{base_url}category/{category_name}.html</loc><lastmod>{datetime.now().isoformat()}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>")

    # タグページ
    all_tags = set()
    for product in products:
        try:
            tags = json.loads(product.get("tags", "[]"))
            all_tags.update(tags)
        except json.JSONDecodeError:
            continue

    for tag in all_tags:
        urls.append(f"<url><loc>{base_url}tags/{tag}.html</loc><lastmod>{datetime.now().isoformat()}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>")

    # 商品詳細ページ
    for product in products:
        urls.append(f"<url><loc>{base_url}pages/{product['id']}.html</loc><lastmod>{datetime.now().isoformat()}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>")
        
    # 静的ページ
    static_pages = ["contact.html", "privacy.html", "disclaimer.html"]
    for page in static_pages:
        urls.append(f"<url><loc>{base_url}{page}</loc><lastmod>{datetime.now().isoformat()}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>")

    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{"".join(urls)}
</urlset>"""

    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_content)
        
    print("sitemap.xmlが正常に生成されました。")


def main():
    """
    メインの実行関数
    """
    # 古いファイルをクリーンアップ
    if os.path.exists("pages"):
        import shutil
        shutil.rmtree("pages")
    if os.path.exists("category"):
        import shutil
        shutil.rmtree("category")
    if os.path.exists("tags"):
        import shutil
        shutil.rmtree("tags")
    if os.path.exists("sitemap.xml"):
        os.remove("sitemap.xml")
    if os.path.exists("index.html"):
        os.remove("index.html")
    if os.path.exists("contact.html"):
        os.remove("contact.html")
    if os.path.exists("privacy.html"):
        os.remove("privacy.html")
    if os.path.exists("disclaimer.html"):
        os.remove("disclaimer.html")
    # products.jsonが存在する場合は削除
    if os.path.exists("products.json"):
        os.remove("products.json")


    # CSVを更新
    update_products_csv()
    
    # 更新されたCSVから商品データを読み込み
    products_df = pd.read_csv(PRODUCTS_CSV_FILE)
    products = products_df.to_dict('records')
    
    # HTMLファイルとサイトマップを生成
    _generate_index_page(products)
    _generate_product_detail_pages(products)
    _generate_category_pages(products)
    _generate_static_pages()
    _generate_sitemap(products)

if __name__ == "__main__":
    main()
