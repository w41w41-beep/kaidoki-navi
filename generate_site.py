import os
import requests
import json
import pandas as pd
from openai import OpenAI
import re

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
                <div class="product-tags my-4">
                    {''.join([f'<a href="../tags/{tag}.html" class="tag-button">#{tag}</a>' for tag in tags])}
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
            <link rel="stylesheet" href="../style.css">
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-100 font-sans">
            <div class="container mx-auto p-4 sm:p-8">
                <a href="../index.html" class="text-blue-500 hover:underline mb-4 inline-block">← トップページに戻る</a>
                
                <div class="bg-white rounded-xl shadow-lg overflow-hidden md:flex">
                    <div class="md:flex-shrink-0">
                        <img src="{product['image_url']}" alt="{product['name']}" class="w-full h-64 object-cover md:h-full md:w-64">
                    </div>
                    <div class="p-6 flex flex-col justify-between w-full">
                        <div>
                            <h1 class="text-3xl font-bold text-gray-800 mb-2">{product['name']}</h1>
                            <p class="text-xl font-semibold text-gray-600 mb-4">{int(product['price']):,}円</p>
                            
                            <h2 class="text-2xl font-semibold text-gray-700 mt-4 mb-2">商品説明</h2>
                            <p class="text-gray-600 leading-relaxed whitespace-pre-wrap">{product['description']}</p>
                            
                            {tags_html}

                            <h2 class="text-2xl font-semibold text-gray-700 mt-6 mb-2">AIによる商品説明</h2>
                            <p class="text-gray-600 leading-relaxed whitespace-pre-wrap">{product['ai_description']}</p>

                            <h2 class="text-2xl font-semibold text-gray-700 mt-6 mb-2">AIによる製品仕様・スペック</h2>
                            <p class="text-gray-600 leading-relaxed whitespace-pre-wrap">{product['specs']}</p>
                            
                        </div>
                        <div class="mt-6 flex flex-wrap gap-4">
                            <a href="{product['url']}" target="_blank" class="flex-1 text-center bg-blue-600 text-white font-bold py-3 px-6 rounded-lg hover:bg-blue-700 transition duration-300">
                                {product['shop']}で詳細を見る
                            </a>
                        </div>
                    </div>
                </div>
            </div>
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
            <div class="bg-white rounded-lg shadow-md overflow-hidden">
                <a href="../pages/{p['id']}.html" class="block">
                    <img src="{p['image_url']}" alt="{p['name']}" class="w-full h-48 object-cover">
                    <div class="p-4">
                        <h2 class="text-lg font-semibold text-gray-800">{p['name']}</h2>
                        <p class="text-gray-600">{int(p['price']):,}円</p>
                    </div>
                </a>
            </div>
            """
        
        tag_html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>#{tag} の商品一覧</title>
            <link rel="stylesheet" href="../style.css">
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-100 font-sans">
            <div class="container mx-auto p-4 sm:p-8">
                <a href="../index.html" class="text-blue-500 hover:underline mb-4 inline-block">← トップページに戻る</a>
                <h1 class="text-3xl font-bold text-gray-800 mb-6">#{tag} の商品一覧</h1>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {product_cards}
                </div>
            </div>
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
            <div class="bg-white rounded-lg shadow-md overflow-hidden">
                <a href="../pages/{p['id']}.html" class="block">
                    <img src="{p['image_url']}" alt="{p['name']}" class="w-full h-48 object-cover">
                    <div class="p-4">
                        <h2 class="text-lg font-semibold text-gray-800">{p['name']}</h2>
                        <p class="text-gray-600">{int(p['price']):,}円</p>
                    </div>
                </a>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{category} - 商品一覧</title>
            <link rel="stylesheet" href="../style.css">
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-100 font-sans">
            <div class="container mx-auto p-4 sm:p-8">
                <a href="../index.html" class="text-blue-500 hover:underline mb-4 inline-block">← トップページに戻る</a>
                <h1 class="text-3xl font-bold text-gray-800 mb-6">{category}の商品一覧</h1>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {product_cards}
                </div>
            </div>
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
        <div class="bg-white rounded-lg shadow-md overflow-hidden">
            <a href="category/{category_name}.html" class="block p-4 text-center">
                <h2 class="text-lg font-bold text-gray-800">{category_name}</h2>
            </a>
        </div>
        """

    product_cards = ""
    for product in products:
        product_cards += f"""
        <div class="bg-white rounded-lg shadow-md overflow-hidden">
            <a href="pages/{product['id']}.html" class="block">
                <img src="{product['image_url']}" alt="{product['name']}" class="w-full h-48 object-cover">
                <div class="p-4">
                    <h2 class="text-lg font-semibold text-gray-800">{product['name']}</h2>
                    <p class="text-gray-600">{int(product['price']):,}円</p>
                </div>
            </a>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>商品紹介サイト</title>
        <link rel="stylesheet" href="style.css">
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 font-sans">
        <div class="container mx-auto p-4 sm:p-8">
            <header class="text-center mb-8">
                <h1 class="text-4xl font-bold text-gray-800 mb-2">最新の人気商品</h1>
                <p class="text-gray-600">最新の人気商品とAIによる分析情報をチェック</p>
            </header>
            
            <section class="mb-8">
                <h2 class="text-2xl font-bold text-gray-700 mb-4">カテゴリから探す</h2>
                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
                    {category_html}
                </div>
            </section>

            <section>
                <h2 class="text-2xl font-bold text-gray-700 mb-4">商品一覧</h2>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {product_cards}
                </div>
            </section>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

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
    if os.path.exists("index.html"):
        os.remove("index.html")
    # products.jsonが存在する場合は削除
    if os.path.exists("products.json"):
        os.remove("products.json")

    # CSVを更新
    update_products_csv()
    
    # 更新されたCSVから商品データを読み込み
    products_df = pd.read_csv(PRODUCTS_CSV_FILE)
    products = products_df.to_dict('records')
    
    # HTMLファイルを生成
    _generate_index_page(products)
    _generate_product_detail_pages(products)
    _generate_category_pages(products)

if __name__ == "__main__":
    main()
