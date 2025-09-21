import json
import math
import os
import shutil
import time
from datetime import date, timedelta
import requests
import random
import hashlib

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 12
# AI分析結果を保存するキャッシュファイル
AI_CACHE_FILE = "ai_cache.json"

# OpenAI API設定
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# 楽天API設定
RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
RAKUTEN_API_KEY = os.environ.get("RAKUTEN_API_KEY")
RAKUTEN_GENRE_IDS = {
    'パソコン・周辺機器': 100026,
    '家電': 100040,
}

# GPTモデル
MODEL_NAME = "gpt-4o-mini"

# キャッシュ読み込み/保存
def load_ai_cache():
    if os.path.exists(AI_CACHE_FILE):
        with open(AI_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_ai_cache(cache):
    with open(AI_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

# AI分析＋タグ・サブカテゴリー・要約生成
def generate_ai_analysis(product_name, product_price, price_history, ai_cache):
    cache_key = f"{product_name}-{product_price}"
    if cache_key in ai_cache:
        data = ai_cache[cache_key]
        return data['headline'], data['details'], data['subcategory'], data['tags'], data['short_description']

    if not OPENAI_API_KEY:
        print("警告: OpenAI APIキー未設定。AI分析スキップ")
        return "AI分析準備中", "詳細なAI分析は現在準備中です。", "未分類", [], ""

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }

    history_text = f"過去の価格履歴:\n{json.dumps(price_history, indent=2)}" if price_history else "価格履歴はありません。"

    messages = [
        {"role": "system", "content": "あなたは価格比較の専門家です。JSON形式で次のキーを出力してください。headline, details, subcategory, tags(3〜5個), short_description。"},
        {"role": "user", "content": f"商品名: {product_name}\n現在価格: {product_price}円\n{history_text}\n上記情報を基に分析してください。"}
    ]

    payload = {
        'model': MODEL_NAME,
        'messages': messages,
        'response_format': {"type": "json_object"}
    }

    try:
        response = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        content = json.loads(response.json()['choices'][0]['message']['content'])
        headline = content.get("headline", "分析結果なし")
        details = content.get("details", "詳細分析なし")
        subcategory = content.get("subcategory", "未分類")
        tags = content.get("tags", [])
        short_description = content.get("short_description", "")

        ai_cache[cache_key] = {
            'headline': headline,
            'details': details,
            'subcategory': subcategory,
            'tags': tags,
            'short_description': short_description
        }

        return headline, details, subcategory, tags, short_description

    except Exception as e:
        print(f"AI生成エラー: {e}")
        return "AI分析失敗", "AI生成中にエラー", "未分類", [], ""

# 楽天APIから商品取得
def fetch_products_from_rakuten():
    if not RAKUTEN_API_KEY:
        print("楽天APIキー未設定。ダミー1個生成")
        return []

    products = []
    for category, genre_id in RAKUTEN_GENRE_IDS.items():
        if len(products) >= 1:  # 最小限1件取得
            break
        params = {
            'applicationId': RAKUTEN_API_KEY,
            'genreId': genre_id,
            'hits': 1,
            'format': 'json',
            'formatVersion': 2
        }
        try:
            resp = requests.get(RAKUTEN_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get('Items', [])
            for item_data in items:
                if len(products) >= 1:
                    break
                item = item_data.get('Item', {})
                item_url = item.get('itemUrl')
                if item_url:
                    hash_id = hashlib.sha256(item_url.encode('utf-8')).hexdigest()[:16]
                    page_url = f"products/product_{hash_id}.html"
                    products.append({
                        'name': item.get('itemName'),
                        'price': item.get('itemPrice'),
                        'url': item.get('itemUrl'),
                        'image': item.get('mediumImageUrls')[0] if item.get('mediumImageUrls') else 'https://placehold.co/400x400/cccccc/333333?text=No+Image',
                        'description': item.get('itemCaption', '商品説明なし'),
                        'page_url': page_url,
                        'price_history': {},
                    })
        except:
            continue
    return products

# 検索機能
def search_products(products, keyword):
    keyword = keyword.lower()
    result = []
    for p in products:
        search_text = p['name'] + " " + " ".join(p.get('tags', []))
        if keyword in search_text.lower():
            result.append(p)
    return result

# 以下HTML生成や商品ページ生成などは既存のコードをそのまま利用
# generate_html_file, generate_product_page, generate_index_page, generate_static_pages, create_sitemap など

# ウェブサイト生成メイン
def generate_website():
    output_dir = "dist"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'products'), exist_ok=True)

    ai_cache = load_ai_cache()
    products_data = fetch_products_from_rakuten()

    # ダミー生成1個
    if not products_data:
        product_name = "ダミー商品"
        price_history = {}
        base_price = random.randint(15000, 100000)
        for d in range(60, 0, -1):
            price_history[(date.today() - timedelta(days=d)).isoformat()] = max(10000, base_price + random.randint(-5000, 5000))
        current_price = price_history.get((date.today() - timedelta(days=1)).isoformat(), base_price)
        products_data.append({
            'name': product_name,
            'price': current_price,
            'price_history': price_history,
            'description': f"これは{product_name}の詳細説明です。",
            'url': f"https://example.com/buy/dummy/1",
            'image': f"https://placehold.co/400x400/2180A0/ffffff?text=Dummy+1",
            'page_url': "products/product_dummy_1.html",
            'ai_headline': 'AI分析準備中',
            'ai_details': '詳細なAI分析は現在準備中です。',
            'subcategory': '未分類',
            'tags': [],
            'short_description': ''
        })
    else:
        for product in products_data:
            headline, details, subcategory, tags, short_desc = generate_ai_analysis(
                product['name'], product['price'], product['price_history'], ai_cache
            )
            product['ai_headline'] = headline
            product['ai_details'] = details
            product['subcategory'] = subcategory
            product['tags'] = tags
            product['short_description'] = short_desc
        save_ai_cache(ai_cache)

    # ここでHTML生成関数を呼び出す（既存コードと同じ）
    create_sitemap(products_data, output_dir)
    generate_static_pages(output_dir)
    generate_index_page(products_data, output_dir)
    for product in products_data:
        generate_product_page(product, product['ai_headline'], product['ai_details'], output_dir)

    print("サイト生成完了。検索時にヒットしない場合は「該当する商品はありません」を表示できます。")

if __name__ == "__main__":
    generate_website()
