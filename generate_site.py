import json
import math
import os
import shutil
import time
from datetime import date
import requests
import random

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 24
# 楽天APIから読み込む商品数を定義 (最大10個)
RAKUTEN_FETCH_LIMIT = 10

# APIキーは実行環境が自動的に供給するため、ここでは空の文字列とします。
# OpenAI APIの設定
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") # 環境変数からAPIキーを取得
MODEL_NAME = "gpt-4o-mini"
AI_ANALYSIS_CACHE_FILE = "ai_analysis_cache.json"
SUBCATEGORY_CACHE_FILE = "subcategory_cache.json"
RAKUTEN_API_FILE = "data/rakuten_api_response.json"

def load_cache(cache_file):
    """キャッシュファイルからデータを読み込む"""
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except json.JSONDecodeError:
        print(f"警告: {cache_file} ファイルの読み込み中にエラーが発生しました。新しいキャッシュを作成します。")
    return {}

def save_cache(cache, cache_file):
    """キャッシュファイルにデータを保存する"""
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

def fetch_products_from_rakuten():
    """
    楽天APIから商品を読み込むダミー関数。
    今回は固定のダミーJSONを読み込みますが、将来的にAPI呼び出しを想定しています。
    """
    if os.path.exists(RAKUTEN_API_FILE):
        with open(RAKUTEN_API_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 楽天から読み込む商品数をRAKUTEN_FETCH_LIMITに制限
            print(f"楽天から商品を{RAKUTEN_FETCH_LIMIT}個読み込みます。")
            return data[:RAKUTEN_FETCH_LIMIT]
    
    print("警告: 楽天APIのダミーファイルが見つかりません。")
    return []

def generate_ai_analysis(product, cache):
    """
    OpenAI APIを使用して、商品の価格分析テキストを生成する。
    応答は一言アピールと詳細分析の2つの部分から構成される。
    """
    cache_key = f"{product['product_id']}_{product['price']}"

    # キャッシュから読み込みを試みる
    if cache_key in cache:
        print(f"商品 '{product['product_name']}' のAI分析をキャッシュから読み込みました。")
        return cache[cache_key]['headline'], cache[cache_key]['details']

    if not OPENAI_API_KEY:
        print("警告: OpenAI APIキーが設定されていません。AI分析はスキップされます。")
        return "AI分析準備中", "詳細なAI分析は現在準備中です。"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }

    # 価格履歴データをプロンプトに追加
    price_history = product.get('price_history', [])
    history_text = f"過去の価格履歴は以下の通りです:\n{price_history}" if price_history else "価格履歴はありません。"
    
    messages = [
        {"role": "system", "content": "あなたは、価格比較の専門家として、消費者に商品の買い時をアドバイスします。回答は必ずJSON形式で提供してください。JSONは「headline」と「details」の2つのキーを持ちます。「headline」は15文字以内の簡潔な一言アピール、「details」は200文字以内の詳細な分析です。"},
        {"role": "user", "content": f"商品名: {product['product_name']}\n現在価格: {product['price']}円\n{history_text}\nこの商品の現在の価格と価格履歴に基づいて、買い時かどうかを分析し、アドバイスを日本語で提供してください。"}
    ]

    payload = {
        'model': MODEL_NAME,
        'messages': messages,
        'response_format': { "type": "json_object" },
        'temperature': 0.7
    }

    try:
        print(f"商品 '{product['product_name']}' のAI分析を生成するため、APIを呼び出しています...")
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status() # HTTPエラーが発生した場合に例外を発生させる
        
        analysis_data = response.json()['choices'][0]['message']['content']
        analysis = json.loads(analysis_data)
        
        headline = analysis.get('headline', 'AI分析準備中')
        details = analysis.get('details', '詳細なAI分析は現在準備中です。')

        # 結果をキャッシュに保存
        cache[cache_key] = {'headline': headline, 'details': details}

        return headline, details
    except requests.exceptions.RequestException as e:
        print(f"API呼び出し中にエラーが発生しました: {e}")
        return "AI分析準備中", "API呼び出しに失敗しました。"
    except json.JSONDecodeError:
        print("APIからの応答が不正なJSON形式です。")
        return "AI分析準備中", "APIからの応答が不正です。"
    except KeyError:
        print("APIからの応答に必要なキーが含まれていません。")
        return "AI分析準備中", "APIからの応答が不完全です。"
        
def generate_subcategory_with_ai(product, cache):
    """
    AIを使用して商品名と説明からサブカテゴリーを生成し、キャッシュに保存する。
    """
    cache_key = f"subcategory_{product['product_id']}"
    
    # 厳格なキャッシュルール: 一度キャッシュに保存されたものは再利用する
    if cache_key in cache:
        print(f"商品 '{product['product_name']}' のサブカテゴリーをキャッシュから読み込みました。")
        return cache[cache_key]

    if not OPENAI_API_KEY:
        print("警告: OpenAI APIキーが設定されていません。サブカテゴリーは生成されません。")
        return "その他"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }
    
    messages = [
        {"role": "system", "content": "あなたはEコマースの専門家です。与えられた商品情報から最も適切なサブカテゴリーを一つだけ選んでください。回答は必ずJSON形式で、`subcategory`というキーに分類名を入れてください。分類名は「おもちゃ」「家電」「日用品」「食品」「本」「ファッション」など、一般的な日本語の単語にしてください。"},
        {"role": "user", "content": f"商品名: {product['product_name']}\n説明: {product['description']}\n\nこの商品を分類してください。"}
    ]
    
    payload = {
        'model': MODEL_NAME,
        'messages': messages,
        'response_format': { "type": "json_object" },
        'temperature': 0.7
    }

    try:
        print(f"商品 '{product['product_name']}' のサブカテゴリーをAIで生成しています...")
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        subcategory_data = response.json()['choices'][0]['message']['content']
        subcategory = json.loads(subcategory_data).get('subcategory', 'その他')
        
        # 新しく生成したサブカテゴリーをキャッシュに保存
        cache[cache_key] = subcategory
        
        return subcategory
    except requests.exceptions.RequestException as e:
        print(f"API呼び出し中にエラーが発生しました: {e}")
        return "その他"
    except json.JSONDecodeError:
        print("APIからの応答が不正なJSON形式です。")
        return "その他"
    except KeyError:
        print("APIからの応答に必要なキーが含まれていません。")
        return "その他"

def create_product_pages(products):
    """
    各商品ページを生成する。
    """
    base_template = ""
    with open('templates/base.html', 'r', encoding='utf-8') as f:
        base_template = f.read()

    for product in products:
        # 商品ごとにAI分析を生成
        ai_analysis_headline = product.get('ai_analysis_headline', 'AI分析準備中')
        ai_analysis_details = product.get('ai_analysis_details', '詳細なAI分析は現在準備中です。')

        html_content = f"""
        <div class="container mx-auto p-4 md:p-8">
            <div class="bg-white rounded-xl shadow-lg overflow-hidden md:flex">
                <div class="md:flex-shrink-0">
                    <img src="{product['image_url']}" alt="{product['product_name']}" class="w-full h-64 object-cover object-center md:w-64 lg:w-80 rounded-t-xl md:rounded-l-xl md:rounded-t-none">
                </div>
                <div class="p-6 flex flex-col justify-between w-full">
                    <div class="mb-4">
                        <h1 class="text-3xl md:text-4xl font-extrabold text-gray-900 mb-2">{product['product_name']}</h1>
                        <p class="text-xl md:text-2xl font-bold text-gray-700 mb-4">{product['price']}円</p>
                        
                        <!-- AI分析セクション -->
                        <div class="bg-gray-100 p-4 rounded-lg">
                            <h3 class="text-lg font-bold text-gray-800 mb-2">AI価格分析：<span class="text-red-600">{ai_analysis_headline}</span></h3>
                            <p class="text-gray-600 text-sm">{ai_analysis_details}</p>
                        </div>
                        
                        <div class="mt-4 text-gray-600">
                            <h3 class="text-lg font-bold text-gray-800 mb-2">商品概要</h3>
                            <p>{product['description']}</p>
                        </div>
                    </div>
                    <a href="#" class="bg-blue-600 text-white text-center py-3 px-6 rounded-lg hover:bg-blue-700 transition duration-300 transform hover:scale-105 font-bold">購入はこちら</a>
                </div>
            </div>
            
            <!-- 価格履歴グラフ -->
            <div class="mt-8 bg-white p-6 rounded-xl shadow-lg">
                <h3 class="text-2xl font-bold text-gray-800 mb-4">価格履歴</h3>
                <canvas id="priceChart" class="w-full h-64"></canvas>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const ctx = document.getElementById('priceChart').getContext('2d');
                const priceHistory = {{"price_history": {json.dumps(product['price_history'])}}};
                const dates = priceHistory.price_history.map(item => item.date);
                const prices = priceHistory.price_history.map(item => item.price);

                new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: dates,
                        datasets: [{{
                            label: '価格 (円)',
                            data: prices,
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{
                                position: 'top',
                            }},
                            title: {{
                                display: true,
                                text: '価格履歴'
                            }}
                        }}
                    }}
                }});
            }});
        </script>
        """

        final_html = base_template.replace('<!-- CONTENT_BLOCK -->', html_content).replace('{{ page_title }}', product['product_name'])
        
        os.makedirs(os.path.dirname(product['page_url']), exist_ok=True)
        with open(product['page_url'], 'w', encoding='utf-8') as f:
            f.write(final_html)

def create_product_list_pages(all_products):
    """
    商品一覧ページとサブカテゴリーページを生成する。
    """
    base_template = ""
    with open('templates/base.html', 'r', encoding='utf-8') as f:
        base_template = f.read()

    # 商品一覧ページを生成
    num_products = len(all_products)
    num_pages = math.ceil(num_products / PRODUCTS_PER_PAGE)
    
    for page_num in range(num_pages):
        start_index = page_num * PRODUCTS_PER_PAGE
        end_index = start_index + PRODUCTS_PER_PAGE
        products_on_page = all_products[start_index:end_index]

        product_cards = ""
        for product in products_on_page:
            product_cards += f"""
            <div class="bg-white rounded-xl shadow-lg overflow-hidden transform transition duration-300 hover:scale-105">
                <a href="{product['page_url']}" class="block">
                    <img src="{product['image_url']}" alt="{product['product_name']}" class="w-full h-48 object-cover object-center">
                    <div class="p-4">
                        <h3 class="text-lg font-bold text-gray-800 truncate">{product['product_name']}</h3>
                        <p class="text-xl font-bold text-gray-700 mt-1">{product['price']}円</p>
                        <p class="text-sm text-gray-500 mt-2 truncate">{product['description']}</p>
                    </div>
                </a>
            </div>
            """

        pagination = ""
        if num_pages > 1:
            pagination = '<div class="flex justify-center mt-8 space-x-2">'
            for i in range(num_pages):
                page_link = f'products/page-{i+1}.html' if i > 0 else 'products/index.html'
                active_class = 'bg-blue-600 text-white' if i == page_num else 'bg-gray-200 text-gray-800'
                pagination += f'<a href="{page_link}" class="px-4 py-2 rounded-full {active_class}">{i+1}</a>'
            pagination += '</div>'

        list_content = f"""
        <div class="container mx-auto p-4">
            <h2 class="text-2xl font-bold text-gray-800 mb-6">商品一覧</h2>
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {product_cards}
            </div>
            {pagination}
        </div>
        """
        
        page_title = f"商品一覧 (ページ {page_num+1})"
        final_html = base_template.replace('<!-- CONTENT_BLOCK -->', list_content).replace('{{ page_title }}', page_title)
        
        page_filename = f'products/page-{page_num+1}.html' if page_num > 0 else 'products/index.html'
        with open(page_filename, 'w', encoding='utf-8') as f:
            f.write(final_html)
            
        print(f"商品一覧ページ '{page_filename}' が生成されました。")

    # サブカテゴリーページを生成
    subcategories = sorted(list(set(p['subcategory'] for p in all_products)))
    for subcategory in subcategories:
        subcategory_products = [p for p in all_products if p['subcategory'] == subcategory]
        product_cards = ""
        for product in subcategory_products:
            product_cards += f"""
            <div class="bg-white rounded-xl shadow-lg overflow-hidden transform transition duration-300 hover:scale-105">
                <a href="{product['page_url']}" class="block">
                    <img src="{product['image_url']}" alt="{product['product_name']}" class="w-full h-48 object-cover object-center">
                    <div class="p-4">
                        <h3 class="text-lg font-bold text-gray-800 truncate">{product['product_name']}</h3>
                        <p class="text-xl font-bold text-gray-700 mt-1">{product['price']}円</p>
                        <p class="text-sm text-gray-500 mt-2 truncate">{product['description']}</p>
                    </div>
                </a>
            </div>
            """
        
        list_content = f"""
        <div class="container mx-auto p-4">
            <h2 class="text-2xl font-bold text-gray-800 mb-6">カテゴリー: {subcategory}</h2>
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {product_cards}
            </div>
        </div>
        """
        
        page_title = f"カテゴリー: {subcategory}"
        final_html = base_template.replace('<!-- CONTENT_BLOCK -->', list_content).replace('{{ page_title }}', page_title)
        
        page_filename = f'products/category-{subcategory.lower().replace(" ", "-")}.html'
        with open(page_filename, 'w', encoding='utf-8') as f:
            f.write(final_html)
            
        print(f"サブカテゴリーページ '{subcategory}' が生成されました。")

def create_static_pages():
    """
    静的ページ（トップページ、プライバシーポリシー、免責事項、お問い合わせ）を生成する。
    """
    # templatesフォルダが存在しない場合は何もしない
    if not os.path.exists('templates'):
        print("エラー: 'templates' フォルダが見つかりません。")
        return

    base_template = ""
    with open('templates/base.html', 'r', encoding='utf-8') as f:
        base_template = f.read()

    # トップページ
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        index_content = f.read()
    final_index = base_template.replace('<!-- CONTENT_BLOCK -->', index_content).replace('{{ page_title }}', 'トップページ')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_index)

    # 静的ページ
    static_pages = {
        'privacy.html': 'プライバシーポリシー',
        'disclaimer.html': '免責事項',
        'contact.html': 'お問い合わせ'
    }
    for filename, title in static_pages.items():
        with open(f'templates/{filename}', 'r', encoding='utf-8') as f:
            content = f.read()
        final_page = base_template.replace('<!-- CONTENT_BLOCK -->', content).replace('{{ page_title }}', title)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(final_page)
    
    print("静的ページが生成されました。")
    
def create_sitemap(products, base_url="http://localhost:8000/"):
    """
    sitemap.xmlを生成する。
    """
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap_content += '  <url>\n'
    sitemap_content += f'    <loc>{base_url}</loc>\n'
    sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
    sitemap_content += '    <changefreq>daily</changefreq>\n'
    sitemap_content += '    <priority>1.0</priority>\n'
    sitemap_content += '  </url>\n'
    
    sitemap_content += '  <url>\n'
    sitemap_content += f'    <loc>{base_url}products/index.html</loc>\n'
    sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
    sitemap_content += '    <changefreq>daily</changefreq>\n'
    sitemap_content += '    <priority>0.8</priority>\n'
    sitemap_content += '  </url>\n'

    subcategories = sorted(list(set(p['subcategory'] for p in products)))
    for subcategory in subcategories:
        page_link = f'products/category-{subcategory.lower().replace(" ", "-")}.html'
        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>{base_url}{page_link}</loc>\n'
        sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
        sitemap_content += '    <changefreq>weekly</changefreq>\n'
        sitemap_content += '    <priority>0.7</priority>\n'
        sitemap_content += '  </url>\n'

    # ページネーション用のURLを追加
    num_products = len(products)
    num_pages = math.ceil(num_products / PRODUCTS_PER_PAGE)
    for i in range(1, num_pages):
        page_link = f'products/page-{i+1}.html'
        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>{base_url}{page_link}</loc>\n'
        sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
        sitemap_content += '    <changefreq>weekly</changefreq>\n'
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

def generate_site():
    """
    ウェブサイト全体を生成するメイン関数。
    """
    # templatesフォルダとdataフォルダが存在することを確認
    if not os.path.exists('templates'):
        print("エラー: 'templates' フォルダが見つかりません。")
        return
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.exists('data/products.json'):
        print("エラー: 'data/products.json' ファイルが見つかりません。")
        return

    # 出力ディレクトリをクリーンアップ
    if os.path.exists('products'):
        shutil.rmtree('products')
    
    # productsディレクトリを作成
    os.makedirs('products')

    # ダミーの商品データを読み込み
    with open('data/products.json', 'r', encoding='utf-8') as f:
        all_products_data = json.load(f)

    # 楽天から読み込む商品を10個に制限
    products_for_site = all_products_data[:RAKUTEN_FETCH_LIMIT]

    # AI分析結果とサブカテゴリーのキャッシュを読み込み
    ai_analysis_cache = load_cache(AI_ANALYSIS_CACHE_FILE)
    subcategory_cache = load_cache(SUBCATEGORY_CACHE_FILE)

    # AI分析とサブカテゴリー生成を実行
    for product in products_for_site:
        product['page_url'] = f"products/{product['product_id']}.html"
        
        # AIでサブカテゴリーを生成
        # product_idをキーとしてキャッシュを確認し、存在しない場合のみAIを呼び出す
        if f"subcategory_{product['product_id']}" not in subcategory_cache:
            product['subcategory'] = generate_subcategory_with_ai(product, subcategory_cache)
        else:
            print(f"商品 '{product['product_name']}' のサブカテゴリーをキャッシュから読み込みました。")
            product['subcategory'] = subcategory_cache[f"subcategory_{product['product_id']}"]
        
        # AI価格分析を生成
        headline, details = generate_ai_analysis(
            product, 
            ai_analysis_cache
        )
        product['ai_analysis_headline'] = headline
        product['ai_analysis_details'] = details

    # キャッシュを保存
    save_cache(ai_analysis_cache, AI_ANALYSIS_CACHE_FILE)
    save_cache(subcategory_cache, SUBCATEGORY_CACHE_FILE)

    print("ウェブサイトのファイル生成を開始します。")

    # 静的ページを生成
    create_static_pages()

    # 商品ページを生成
    create_product_pages(products_for_site)

    # 商品一覧ページとサブカテゴリーページを生成
    create_product_list_pages(products_for_site)

    # sitemap.xmlを生成
    create_sitemap(products_for_site)

    print("サイトのファイル生成が完了しました。")

if __name__ == '__main__':
    generate_site()
