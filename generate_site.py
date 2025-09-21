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
PRODUCTS_PER_PAGE = 1
# AI分析結果を保存するキャッシュファイル
AI_CACHE_FILE = "ai_cache.json"

# APIキーは実行環境が自動的に供給するため、ここでは空の文字列とします。
# OpenAI APIの設定
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
# 環境変数からAPIキーを取得
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# 楽天APIの設定
RAKUTEN_API_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
RAKUTEN_API_KEY = os.environ.get("RAKUTEN_API_KEY")
# 楽天のジャンルIDを複数設定
RAKUTEN_GENRE_IDS = {
    '食品': 100227
}

# GPT-4o-miniモデルを使用
MODEL_NAME = "gpt-4o-mini"

def load_ai_cache():
    """AI分析のキャッシュファイルを読み込む"""
    if os.path.exists(AI_CACHE_FILE):
        with open(AI_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_ai_cache(cache):
    """AI分析のキャッシュをファイルに保存する"""
    with open(AI_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def generate_ai_analysis(product_name, product_price, price_history, ai_cache):
    """
    OpenAI APIを使用して、商品の価格分析テキストを生成する。
    キャッシュに存在する場合は、APIを呼び出さずに再利用する。
    """
    cache_key = f"{product_name}-{product_price}"
    if cache_key in ai_cache:
        print(f"商品 '{product_name}' のAI分析をキャッシュから読み込みます。")
        return ai_cache[cache_key]['headline'], ai_cache[cache_key]['details']

    if not OPENAI_API_KEY:
        print("警告: OpenAI APIキーが設定されていません。AI分析はスキップされます。")
        return "AI分析準備中", "詳細なAI分析は現在準備中です。"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }

    history_text = f"過去の価格履歴は以下の通りです:\n{json.dumps(price_history, indent=2)}" if price_history else "価格履歴はありません。"

    messages = [
        {"role": "system", "content": "あなたは、価格比較の専門家として、消費者に商品の買い時をアドバイスします。回答は必ずJSON形式で提供してください。JSONは「headline」（一言アピール）と「details」（詳細分析）の2つのキーを持ちます。日本語で簡潔に、しかし洞察に富んだ分析を提供してください。価格履歴に基づいて、購入を推奨するか、または待つべきかを判断します。"},
        {"role": "user", "content": f"商品名: {product_name}\n現在の価格: {product_price}円\n{history_text}\nこの商品の現在の価格について分析し、買い時かどうかをアドバイスしてください。"}
    ]

    payload = {
        'model': MODEL_NAME,
        'messages': messages,
        'response_format': {"type": "json_object"}
    }

    try:
        print(f"商品 '{product_name}' のAI分析を生成するため、APIを呼び出しています...")
        response = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        analysis_data = response.json()
        content = json.loads(analysis_data['choices'][0]['message']['content'])
        headline = content.get("headline", "分析結果なし")
        details = content.get("details", "詳細分析は提供されていません。")
        
        # キャッシュに保存
        ai_cache[cache_key] = {'headline': headline, 'details': details}
        return headline, details
    except requests.exceptions.RequestException as e:
        print(f"OpenAI APIへのリクエスト中にエラーが発生しました: {e}")
        return "AI分析失敗", "ネットワークエラーまたはAPIの問題により分析を完了できませんでした。"
    except (json.JSONDecodeError, KeyError) as e:
        print(f"APIからの応答を解析中にエラーが発生しました: {e}")
        return "AI分析失敗", "無効な応答形式です。"

def fetch_products_from_rakuten():
    """
    楽天APIから最新の商品情報を1個取得する
    """
    if not RAKUTEN_API_KEY:
        print("警告: 楽天APIキーが設定されていません。ダミー商品を使用します。")
        return []

    products = []
    # 複数のカテゴリーから、itemUrlを持つ商品が見つかるまで検索
    for category, genre_id in RAKUTEN_GENRE_IDS.items():
        # APIリクエストパラメータ
        params = {
            'applicationId': RAKUTEN_API_KEY,
            'genreId': genre_id,
            'hits': 10,  # 1つのジャンルで複数の商品を試す
            'format': 'json',
            'formatVersion': 2,
        }

        try:
            print(f"楽天APIから'{category}'の商品情報を取得しています...")
            response = requests.get(RAKUTEN_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            items = data.get('Items', [])
            
            for item_data in items:
                item = item_data.get('Item', {})
                item_url = item.get('itemUrl')
                # itemUrl があれば、その商品を products リストに追加してループを抜ける
                if item_url:
                    unique_hash = hashlib.sha256(item_url.encode('utf-8')).hexdigest()[:16]
                    page_url = f"products/product_{unique_hash}.html"

                    products.append({
                        'name': item.get('itemName'),
                        'price': item.get('itemPrice'),
                        'url': item.get('itemUrl'),
                        'image': item.get('mediumImageUrls')[0] if item.get('mediumImageUrls') else 'https://placehold.co/400x400/cccccc/333333?text=No+Image',
                        'description': item.get('itemCaption', '商品説明はありません。'),
                        'page_url': page_url,
                        'price_history': {},
                    })
                    return products # 有効な商品が見つかったので、ここで終了
        except requests.exceptions.RequestException as e:
            print(f"楽天APIへのリクエスト中にエラーが発生しました: {e}")
            continue
        except (json.JSONDecodeError, KeyError) as e:
            print(f"楽天APIからの応答を解析中にエラーが発生しました: {e}")
            continue

    return [] # どのジャンルでも有効な商品が見つからなかった場合

def generate_html_file(title, content, filepath):
    """
    共通のヘッダー、フッター、スタイルを含むHTMLファイルを生成する。
    """
    head = f"""
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Inter', sans-serif;
                background-color: #f3f4f6;
            }}
            .card {{
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
            }}
        </style>
    </head>
    """
    
    header = """
    <header class="bg-indigo-600 text-white p-4 shadow-md sticky top-0 z-50">
        <div class="container mx-auto flex justify-between items-center">
            <a href="/" class="text-2xl font-bold rounded-lg px-3 py-1 hover:bg-indigo-700 transition">PricePilot</a>
            <nav>
                <a href="/about.html" class="mx-2 hover:underline">このサイトについて</a>
                <a href="/contact.html" class="mx-2 hover:underline">お問い合わせ</a>
            </nav>
        </div>
    </header>
    """
    
    footer = """
    <footer class="bg-gray-800 text-white p-6 mt-12">
        <div class="container mx-auto text-center">
            <p>&copy; 2024 PricePilot. All rights reserved.</p>
            <div class="mt-4">
                <a href="/privacy.html" class="mx-2 hover:underline">プライバシーポリシー</a> | 
                <a href="/disclaimer.html" class="mx-2 hover:underline">免責事項</a>
            </div>
        </div>
    </footer>
    """

    html_content = f"""
<!DOCTYPE html>
<html lang="ja">
{head}
<body class="bg-gray-100 flex flex-col min-h-screen">
    {header}
    <main class="container mx-auto p-4 flex-grow">
        {content}
    </main>
    {footer}
</body>
</html>
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
def generate_product_page(product, ai_headline, ai_details, output_dir):
    """
    個別の商品ページのHTMLファイルを生成する。
    """
    content = f"""
    <div class="bg-white rounded-xl shadow-lg overflow-hidden p-8 flex flex-col md:flex-row items-center md:items-start space-y-6 md:space-y-0 md:space-x-12">
        <div class="flex-shrink-0 w-64 h-64 flex items-center justify-center">
            <img src="{product['image']}" alt="{product['name']}" class="max-w-full max-h-full object-contain rounded-lg">
        </div>
        <div class="flex-grow text-center md:text-left">
            <h1 class="text-4xl font-bold text-gray-800 mb-4">{product['name']}</h1>
            <p class="text-5xl font-extrabold text-indigo-600 mb-6">{product['price']}円</p>
            
            <div class="bg-indigo-50 border-l-4 border-indigo-400 p-6 mb-8 rounded-lg">
                <h3 class="text-2xl font-bold text-indigo-800 mb-2">AI価格分析</h3>
                <p class="text-xl font-bold text-indigo-600 mb-2">「{ai_headline}」</p>
                <p class="text-gray-700 leading-relaxed">{ai_details}</p>
            </div>
            
            <div class="mb-8">
                <h3 class="text-2xl font-bold text-gray-800 mb-2">商品概要</h3>
                <p class="text-gray-600">{product['description']}</p>
            </div>

            <div>
                <h3 class="text-2xl font-bold text-gray-800 mb-2">価格履歴</h3>
                <div class="bg-gray-100 rounded-lg p-4">
                    <pre class="text-gray-600 text-sm overflow-x-auto">{json.dumps(product['price_history'], indent=2)}</pre>
                </div>
            </div>
        </div>
    </div>
    """
    
    # 購入ボタンを追加
    content += f"""
    <div class="fixed bottom-0 left-0 right-0 bg-white p-4 shadow-lg flex justify-center items-center">
        <a href="{product['url']}" target="_blank" rel="noopener noreferrer" class="block bg-indigo-600 text-white py-3 px-8 rounded-full font-semibold shadow-lg hover:bg-indigo-700 transition transform hover:scale-105">
            商品ページを見る
        </a>
    </div>
    """

    filepath = os.path.join(output_dir, product['page_url'])
    generate_html_file(f"PricePilot - {product['name']}", content, filepath)
    print(f"商品ページが生成されました: {filepath}")

def generate_index_page(products, output_dir):
    """
    トップページ（商品一覧）のHTMLファイルを生成する。
    """
    total_products = len(products)
    total_pages = math.ceil(total_products / PRODUCTS_PER_PAGE)
    
    for page_num in range(1, total_pages + 1):
        start_index = (page_num - 1) * PRODUCTS_PER_PAGE
        end_index = start_index + PRODUCTS_PER_PAGE
        page_products = products[start_index:end_index]
        
        products_html = ""
        for product in page_products:
            products_html += f"""
            <a href="/{product['page_url']}" class="block card">
                <div class="bg-white rounded-xl shadow-lg p-6 flex flex-col items-center text-center">
                    <img src="{product['image']}" alt="{product['name']}" class="w-48 h-48 object-contain rounded-lg mb-4">
                    <h2 class="text-xl font-semibold text-gray-800 mb-2 truncate w-full">{product['name']}</h2>
                    <p class="text-3xl font-bold text-indigo-600 mb-2">{product['price']}円</p>
                    <div class="text-sm text-gray-500">
                        <span class="font-bold text-green-600">{product['ai_headline']}</span>
                    </div>
                </div>
            </a>
            """
        
        pagination_html = ""
        if total_pages > 1:
            pagination_html = '<div class="flex justify-center mt-8 space-x-2">'
            for i in range(1, total_pages + 1):
                page_file = f'index.html' if i == 1 else f'index_{i}.html'
                is_current_page = 'bg-indigo-600 text-white' if i == page_num else 'bg-white text-indigo-600 hover:bg-gray-200'
                pagination_html += f"""
                <a href="/{page_file}" class="px-4 py-2 border rounded-lg {is_current_page}">{i}</a>
                """
            pagination_html += '</div>'
            
        content = f"""
        <h1 class="text-4xl font-bold text-center text-gray-800 mb-8">商品一覧</h1>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
            {products_html}
        </div>
        {pagination_html}
        """

        filename = 'index.html' if page_num == 1 else f'index_{page_num}.html'
        filepath = os.path.join(output_dir, filename)
        generate_html_file('PricePilot - 商品一覧', content, filepath)
        
    print("商品一覧ページが生成されました。")

def generate_static_pages(output_dir):
    """
    静的ページ（プライバシー、免責事項など）を生成する。
    """
    pages = {
        'about.html': {
            'title': 'このサイトについて',
            'content': """
            <h1 class="text-4xl font-bold text-gray-800 mb-8">このサイトについて</h1>
            <p class="text-gray-600">PricePilotは、最新のAI技術を活用して、様々な商品の価格動向を分析し、ユーザーにとって最適な「買い時」を提案する価格比較サイトです。私たちの目標は、消費者が情報過多の時代に正しい選択ができるよう、信頼性の高い情報を提供することです。</p>
            <p class="text-gray-600 mt-4">当サイトは、膨大なデータをAIが解析することで、市場のトレンドや価格の変動パターンを予測します。これにより、ユーザーはより賢く、よりお得に商品を購入することができます。</p>
            """
        },
        'privacy.html': {
            'title': 'プライバシーポリシー',
            'content': """
            <h1 class="text-4xl font-bold text-gray-800 mb-8">プライバシーポリシー</h1>
            <p class="text-gray-600">このサイトは、ユーザーのプライバシー保護を最優先に考えており、個人情報の収集や利用は行いません。</p>
            <p class="text-gray-600 mt-4">当サイトは、商品の情報比較と分析のみを目的としており、外部サービスへのリンクを除き、ユーザーの追跡やデータの保存は行いません。安心してご利用ください。</p>
            """
        },
        'disclaimer.html': {
            'title': '免責事項',
            'content': """
            <h1 class="text-4xl font-bold text-gray-800 mb-8">免責事項</h1>
            <p class="text-gray-600">当サイトで提供される情報は、商品の価格比較と分析を目的としたものであり、その正確性、完全性、信頼性を保証するものではありません。情報の利用は、ユーザー自身の責任において行ってください。</p>
            <p class="text-gray-600 mt-4">当サイトの情報に基づき発生したいかなる損害についても、一切の責任を負いません。最終的な購入判断は、必ず販売元の公式サイトで詳細を確認してください。</p>
            """
        },
        'contact.html': {
            'title': 'お問い合わせ',
            'content': """
            <h1 class="text-4xl font-bold text-gray-800 mb-8">お問い合わせ</h1>
            <p class="text-gray-600">このサイトに関するご意見やご質問がある場合は、以下のメールアドレスまでご連絡ください。</p>
            <p class="text-gray-600 mt-4 font-bold">contact@pricepilot.com</p>
            """
        }
    }
    
    for filename, page_info in pages.items():
        filepath = os.path.join(output_dir, filename)
        generate_html_file(page_info['title'], page_info['content'], filepath)
    
    print("静的ページが生成されました。")

def create_sitemap(products, output_dir):
    """
    サイトマップ（sitemap.xml）を生成する。
    """
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""
    base_url = "https://your-website.com/"
    
    static_pages = ["index.html", "about.html", "privacy.html", "disclaimer.html", "contact.html"]
    for page in static_pages:
        sitemap_content += f"""  <url>
    <loc>{base_url}{page}</loc>
    <lastmod>{date.today().isoformat()}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
"""

    for product in products:
        sitemap_content += f"""  <url>
    <loc>{base_url}{product['page_url']}</loc>
    <lastmod>{date.today().isoformat()}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
"""

    sitemap_content += "</urlset>"
    with open(os.path.join(output_dir, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sitemap_content)
    
    print("sitemap.xml が生成されました。")

def generate_website():
    """
    ウェブサイトの全ファイルを生成するメイン関数。
    """
    output_dir = "dist"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'products'), exist_ok=True)
    
    ai_cache = load_ai_cache()
    
    print("商品データを準備中...")
    
    # 楽天APIから商品を取得
    products_data = fetch_products_from_rakuten()
    
    # APIから商品が取得できなかった場合は、ダミー商品を1個生成する
    if not products_data:
        print("警告: 楽天APIからの商品取得に失敗したため、ダミー商品を1個生成します。")
        # --- 修正箇所：ダミー生成を1個に限定 ---
        product_name = "ダミー商品 1"
        price_history = {}
        base_price = random.randint(15000, 100000)
        for d in range(60, 0, -1):
            price_history[(date.today() - timedelta(days=d)).isoformat()] = max(10000, base_price + random.randint(-5000, 5000))
        current_price = price_history.get((date.today() - timedelta(days=1)).isoformat(), base_price)
        page_url = f"products/product_dummy_1.html"
        products_data.append({
            'name': product_name,
            'price': current_price,
            'price_history': price_history,
            'description': f"これは、{product_name}に関する詳細な商品説明です。画期的な機能と優れたデザインを備えています。",
            'url': f"https://example.com/buy/dummy/1",
            'image': f"https://placehold.co/400x400/2180A0/ffffff?text=Product+1",
            'page_url': page_url,
            'ai_headline': 'AI分析準備中',
            'ai_details': '詳細なAI分析は現在準備中です。',
        })
        # ----------------------------------
    else:
        # AI分析を生成して商品データに追加 (楽天APIから商品が取得できた場合のみ実行)
        for product in products_data:
            ai_headline, ai_detail = generate_ai_analysis(product['name'], product['price'], product['price_history'], ai_cache)
            product['ai_headline'] = ai_headline
            product['ai_details'] = ai_detail

    # AI分析キャッシュを保存 (楽天APIから商品が取得できた場合のみ実行)
    if products_data and 'ダミー商品' not in products_data[0]['name']:
        save_ai_cache(ai_cache)
    
    print("ウェブサイトのファイル生成を開始します。")
    
    create_sitemap(products_data, output_dir)
    generate_static_pages(output_dir)
    generate_index_page(products_data, output_dir)
    
    for product in products_data:
        generate_product_page(product, product['ai_headline'], product['ai_details'], output_dir)
    
    print("サイトのファイル生成が完了しました。")

if __name__ == "__main__":
    generate_website()
