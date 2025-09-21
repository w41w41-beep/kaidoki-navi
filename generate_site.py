import json
import os
import shutil
import hashlib
import requests
from urllib.parse import quote_plus

# --------------------
# 設定
# --------------------
OUTPUT_DIR = "dist"
AI_CACHE_FILE = "ai_cache.json"
RAKUTEN_API_KEY = os.environ.get("RAKUTEN_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
MODEL_NAME = "gpt-4o-mini"

# ジャンルIDを指定
RAKUTEN_GENRE_IDS = {
    'パソコン・周辺機器': 100026,
    '家電': 100040
}

PRODUCTS_PER_PAGE = 12

# --------------------
# キャッシュ
# --------------------
def load_ai_cache():
    if os.path.exists(AI_CACHE_FILE):
        with open(AI_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_ai_cache(cache):
    with open(AI_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

# --------------------
# AI分析
# --------------------
def generate_ai_analysis(product_name, product_price, price_history, ai_cache):
    cache_key = f"{product_name}-{product_price}"
    if cache_key in ai_cache:
        return ai_cache[cache_key]['headline'], ai_cache[cache_key]['details'], ai_cache[cache_key].get('tags', []), ai_cache[cache_key].get('subcategory', '')

    # ダミーでキャッシュに保存（実際はOpenAI API呼び出し）
    headline = f"{product_name} の分析結果"
    details = f"{product_name} の詳細説明です。価格: {product_price}円"
    tags = ["タグ1", "タグ2"]
    subcategory = "サブカテゴリー"
    ai_cache[cache_key] = {'headline': headline, 'details': details, 'tags': tags, 'subcategory': subcategory}
    return headline, details, tags, subcategory

# --------------------
# 楽天API商品取得
# --------------------
def fetch_products_from_rakuten():
    products = []
    if not RAKUTEN_API_KEY:
        return []

    for category, genre_id in RAKUTEN_GENRE_IDS.items():
        params = {
            'applicationId': RAKUTEN_API_KEY,
            'genreId': genre_id,
            'hits': 1,
            'format': 'json',
            'formatVersion': 2
        }
        try:
            res = requests.get(RAKUTEN_API_URL, params=params)
            res.raise_for_status()
            data = res.json()
            items = data.get('Items', [])
            for item_data in items:
                item = item_data.get('Item', {})
                url = item.get('itemUrl')
                if url:
                    unique_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
                    page_url = f"products/product_{unique_hash}.html"
                    products.append({
                        'name': item.get('itemName'),
                        'price': item.get('itemPrice'),
                        'url': url,
                        'image': item.get('mediumImageUrls')[0] if item.get('mediumImageUrls') else 'https://placehold.co/400x400/cccccc/333333?text=No+Image',
                        'description': item.get('itemCaption', '商品説明はありません。'),
                        'page_url': page_url,
                        'price_history': {},
                    })
        except:
            continue
    # ダミー1件
    if not products:
        products = [{
            'name': "ダミー商品",
            'price': 10000,
            'url': "https://example.com",
            'image': "https://placehold.co/400x400/2180A0/ffffff?text=Dummy",
            'description': "ダミー商品です。",
            'page_url': "products/product_dummy.html",
            'price_history': {},
        }]
    return products

# --------------------
# HTML生成共通
# --------------------
def generate_html_file(title, content, filepath):
    head = f"""
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    </head>
    """
    html = f"<!DOCTYPE html><html lang='ja'>{head}<body class='p-4'>{content}</body></html>"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

# --------------------
# 商品ページ
# --------------------
def generate_product_page(product, output_dir):
    content = f"""
    <h1 class='text-2xl font-bold'>{product['name']}</h1>
    <p class='mt-2 text-lg'>{product['price']}円</p>
    <img src='{product['image']}' alt='{product['name']}' class='mt-2 w-64'>
    <p class='mt-4'>{product.get('ai_details','')}</p>
    <p class='mt-2'>{product['description']}</p>
    <p class='mt-2'>タグ: {', '.join(product.get('tags', []))}</p>
    <p class='mt-2'>サブカテゴリー: {product.get('subcategory','')}</p>
    <a href='../index.html' class='mt-4 inline-block text-blue-600'>トップページへ戻る</a>
    """
    generate_html_file(product['name'], content, os.path.join(output_dir, product['page_url']))

# --------------------
# インデックスページ + 検索
# --------------------
def generate_index_page(products, output_dir, search_query=None):
    filtered = products
    if search_query:
        q = search_query.lower()
        filtered = [p for p in products if q in p['name'].lower() or q in p['description'].lower()]
    if not filtered:
        content = "<p class='text-center text-xl mt-8'>該当の商品はありません。</p>"
    else:
        content = "<div class='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>"
        for p in filtered:
            content += f"""
            <div class='border p-4 rounded'>
                <a href='{p['page_url']}' class='font-bold text-lg'>{p['name']}</a>
                <p>{p['price']}円</p>
                <img src='{p['image']}' class='mt-2 w-48'>
            </div>
            """
        content += "</div>"
    # 検索フォーム
    content = f"""
    <form method='get' class='mb-4'>
        <input type='text' name='q' placeholder='商品検索' class='border p-2 rounded'>
        <button type='submit' class='ml-2 px-4 py-2 bg-blue-500 text-white rounded'>検索</button>
    </form>
    """ + content
    generate_html_file("商品一覧", content, os.path.join(output_dir, "index.html"))

# --------------------
# 静的ページ
# --------------------
def generate_static_pages(output_dir):
    pages = {
        'about.html': "このサイトについて",
        'privacy.html': "プライバシーポリシー",
        'disclaimer.html': "免責事項",
        'contact.html': "お問い合わせ"
    }
    for filename, title in pages.items():
        content = f"<h1 class='text-2xl font-bold'>{title}</h1>"
        generate_html_file(title, content, os.path.join(output_dir, filename))

# --------------------
# サイトマップ生成
# --------------------
def create_sitemap(products, output_dir):
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    base_url = "https://your-website.com/"
    static_pages = ["index.html", "about.html", "privacy.html", "disclaimer.html", "contact.html"]
    for page in static_pages:
        sitemap_content += f"<url><loc>{base_url}{page}</loc></url>"
    for p in products:
        sitemap_content += f"<url><loc>{base_url}{p['page_url']}</loc></url>"
    sitemap_content += "</urlset>"
    with open(os.path.join(output_dir, "sitemap.xml"), 'w', encoding='utf-8') as f:
        f.write(sitemap_content)

# --------------------
# メイン
# --------------------
def generate_website():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(os.path.join(OUTPUT_DIR, "products"), exist_ok=True)

    ai_cache = load_ai_cache()
    products = fetch_products_from_rakuten()

    for p in products:
        headline, details, tags, subcat = generate_ai_analysis(p['name'], p['price'], p['price_history'], ai_cache)
        p['ai_headline'] = headline
        p['ai_details'] = details
        p['tags'] = tags
        p['subcategory'] = subcat
    save_ai_cache(ai_cache)

    generate_static_pages(OUTPUT_DIR)
    generate_index_page(products, OUTPUT_DIR)
    for p in products:
        generate_product_page(p, OUTPUT_DIR)
    create_sitemap(products, OUTPUT_DIR)
    print("サイト生成完了")

if __name__ == "__main__":
    generate_website()
