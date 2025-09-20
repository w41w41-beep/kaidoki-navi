# generate_site.py

import json
import os
import shutil
import time
from datetime import date, timedelta
import requests
import random
from collections import defaultdict

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 24
# AI分析結果を保存するキャッシュファイル
AI_CACHE_FILE = "ai_cache.json"

# APIキーは実行環境が自動的に供給するため、ここでは空の文字列とします。
# 環境変数からAPIキーを取得
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# GPT-4o-miniモデルを使用
MODEL_NAME = "gpt-4o-mini"

# OpenAI APIのベースURL
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

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

def generate_html_file(title, content, filepath, categories_data=None):
    """
    共通のヘッダー、フッター、スタイルを含むHTMLファイルを生成する。
    """
    
    # ナビゲーションバーを動的に生成
    nav_html = ""
    if categories_data:
        for category, subcategories in categories_data.items():
            sub_menu_items = "".join([f'<li><a href="/products/{sub.get("url", "#")}.html" class="block px-4 py-2 hover:bg-indigo-100">{sub["name"]}</a></li>' for sub in subcategories])
            nav_html += f"""
            <li class="relative group">
                <a href="#" class="inline-flex items-center px-4 py-2 hover:bg-indigo-700 transition rounded-lg">
                    {category} <svg class="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                </a>
                <ul class="absolute z-10 hidden group-hover:block bg-white text-gray-800 shadow-lg rounded-lg w-48 py-2 mt-2">
                    {sub_menu_items}
                </ul>
            </li>
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
    
    header = f"""
    <header class="bg-indigo-600 text-white p-4 shadow-md sticky top-0 z-50">
        <div class="container mx-auto flex justify-between items-center">
            <a href="/index.html" class="text-2xl font-bold rounded-lg px-3 py-1 hover:bg-indigo-700 transition">PricePilot</a>
            <nav>
                <a href="/index.html" class="mx-2 hover:underline">ホーム</a>
                <a href="/about.html" class="mx-2 hover:underline">このサイトについて</a>
            </nav>
        </div>
        <div class="bg-indigo-700 mt-4 rounded-lg">
            <nav class="container mx-auto">
                <ul class="flex justify-center text-white py-2">
                    {nav_html}
                </ul>
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
                <a href="/disclaimer.html" class="mx-2 hover:underline">免責事項</a> | 
                <a href="/contact.html" class="mx-2 hover:underline">お問い合わせ</a>
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
    
def generate_product_page(product, ai_headline, ai_details, output_dir, categories_data):
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
    generate_html_file(f"PricePilot - {product['name']}", content, filepath, categories_data)
    print(f"商品ページが生成されました: {filepath}")

def generate_index_page(products, categories_data, output_dir):
    """
    トップページ（商品一覧）のHTMLファイルを生成する。
    """
    products_html = ""
    for product in products:
        badges_html = ""
        if product.get('is_on_sale'):
            badges_html += '<span class="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full absolute top-2 right-2">お買い得！</span>'
        if product.get('is_new'):
            badges_html += '<span class="bg-blue-500 text-white text-xs font-bold px-2 py-1 rounded-full absolute top-2 left-2">新作</span>'
        
        products_html += f"""
        <a href="/{product['page_url']}" class="block card relative">
            <div class="bg-white rounded-xl shadow-lg p-6 flex flex-col items-center text-center">
                {badges_html}
                <img src="{product['image']}" alt="{product['name']}" class="w-48 h-48 object-contain rounded-lg mb-4">
                <h2 class="text-xl font-semibold text-gray-800 mb-2 truncate w-full">{product['name']}</h2>
                <p class="text-3xl font-bold text-indigo-600 mb-2">{product['price']}円</p>
                <div class="text-sm text-gray-500">
                    <span class="font-bold text-green-600">{product['ai_headline']}</span>
                </div>
            </div>
        </a>
        """
    
    content = f"""
    <h1 class="text-4xl font-bold text-center text-gray-800 mb-8">AIが選ぶお買い得商品</h1>
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
        {products_html}
    </div>
    """

    filepath = os.path.join(output_dir, 'index.html')
    generate_html_file('PricePilot - お買い得商品', content, filepath, categories_data)
    
    print("商品一覧ページが生成されました。")

def generate_subcategory_page(subcategory_name, products, categories_data, output_dir):
    """
    サブカテゴリー別の商品一覧ページを生成する。
    """
    products_html = ""
    for product in products:
        badges_html = ""
        if product.get('is_on_sale'):
            badges_html += '<span class="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full absolute top-2 right-2">お買い得！</span>'
        if product.get('is_new'):
            badges_html += '<span class="bg-blue-500 text-white text-xs font-bold px-2 py-1 rounded-full absolute top-2 left-2">新作</span>'
        
        products_html += f"""
        <a href="/{product['page_url']}" class="block card relative">
            <div class="bg-white rounded-xl shadow-lg p-6 flex flex-col items-center text-center">
                {badges_html}
                <img src="{product['image']}" alt="{product['name']}" class="w-48 h-48 object-contain rounded-lg mb-4">
                <h2 class="text-xl font-semibold text-gray-800 mb-2 truncate w-full">{product['name']}</h2>
                <p class="text-3xl font-bold text-indigo-600 mb-2">{product['price']}円</p>
                <div class="text-sm text-gray-500">
                    <span class="font-bold text-green-600">{product['ai_headline']}</span>
                </div>
            </div>
        </a>
        """
        
    content = f"""
    <h1 class="text-4xl font-bold text-center text-gray-800 mb-8">{subcategory_name.capitalize()}の商品一覧</h1>
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
        {products_html}
    </div>
    """

    # URL用に名前を変換
    url_name = subcategory_name.replace(' ', '_').lower()
    filepath = os.path.join(output_dir, f'products/{url_name}.html')
    generate_html_file(f'PricePilot - {subcategory_name}', content, filepath, categories_data)
    print(f"サブカテゴリーページ '{subcategory_name}' が生成されました。")


def generate_static_pages(output_dir, categories_data):
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
        generate_html_file(page_info['title'], page_info['content'], filepath, categories_data)
    
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
    
    print("ダミー商品データを準備中...")

    products_data = []
    
    # カテゴリーとサブカテゴリーの定義
    categories_data = {
        "家電": [{"name": "テレビ", "url": "tv"}, {"name": "冷蔵庫", "url": "refrigerator"}, {"name": "パソコン", "url": "pc"}],
        "本": [{"name": "小説", "url": "novel"}, {"name": "漫画", "url": "manga"}, {"name": "技術書", "url": "tech_books"}],
        "ファッション": [{"name": "トップス", "url": "tops"}, {"name": "ボトムス", "url": "bottoms"}, {"name": "アウター", "url": "outerwear"}],
        "食品": [{"name": "お菓子", "url": "snacks"}, {"name": "飲料", "url": "drinks"}, {"name": "レトルト食品", "url": "retort_foods"}]
    }

    all_subcategories = []
    for category, sub_list in categories_data.items():
        for sub in sub_list:
            all_subcategories.append({'category': category, 'name': sub['name'], 'url': sub['url']})

    for i in range(1, 101): # 100個のダミー商品
        product_name = f"商品 {i}"
        
        # カテゴリーとサブカテゴリーをランダムに割り当て
        random_sub = random.choice(all_subcategories)
        category = random_sub['category']
        subcategory = random_sub['name']
        
        # 過去の価格履歴をシミュレーション
        price_history = {}
        base_price = random.randint(15000, 100000)
        for d in range(60, 0, -1):
            price_history[(date.today() - timedelta(days=d)).isoformat()] = max(10000, base_price + random.randint(-5000, 5000))
        current_price = list(price_history.values())[-1]
        
        # お買い得と新作のフラグをランダムに設定
        is_on_sale = random.choice([True, False])
        is_new = random.choice([True, False])

        page_url = f"products/product_{i}.html"
        
        # キャッシュを利用してAI分析を生成
        ai_headline, ai_detail = generate_ai_analysis(product_name, current_price, price_history, ai_cache)
        
        products_data.append({
            'name': product_name,
            'price': current_price,
            'price_history': price_history,
            'description': f"これは、{product_name}に関する詳細な商品説明です。画期的な機能と優れたデザインを備えています。",
            'url': f"https://example.com/buy/{i}",
            'image': f"https://placehold.co/400x400/2180A0/ffffff?text=Product+{i}",
            'page_url': page_url,
            'category': category,
            'subcategory': subcategory,
            'is_on_sale': is_on_sale,
            'is_new': is_new,
            'ai_headline': ai_headline,
            'ai_details': ai_detail
        })

    # AI分析キャッシュを保存
    save_ai_cache(ai_cache)
    
    print("ウェブサイトのファイル生成を開始します。")
    
    create_sitemap(products_data, output_dir)
    generate_static_pages(output_dir, categories_data)
    generate_index_page(products_data, categories_data, output_dir)
    
    # サブカテゴリーごとのページを生成
    products_by_subcategory = defaultdict(list)
    for product in products_data:
        products_by_subcategory[product['subcategory']].append(product)
        
    for subcategory, products in products_by_subcategory.items():
        # URL名をcategories_dataから取得
        url_name = next((item['url'] for category_data in categories_data.values() for item in category_data if item['name'] == subcategory), None)
        if url_name:
            generate_subcategory_page(subcategory, products, categories_data, output_dir)
        
    for product in products_data:
        generate_product_page(product, product['ai_headline'], product['ai_details'], output_dir, categories_data)
    
    print("サイトのファイル生成が完了しました。")

if __name__ == "__main__":
    generate_website()
