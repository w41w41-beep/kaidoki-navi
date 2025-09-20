import json
import math
import os
import shutil
import time
from datetime import date
import requests
import re
import random

# 1ページあたりの商品数を定義
PRODUCTS_PER_PAGE = 24

# APIキーは実行環境が自動的に供給するため、ここでは空の文字列とします。
# OpenAI APIの設定
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") # 環境変数からAPIキーを取得
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
    history_text = f"過去の価格履歴は以下の通りです:\\n{price_history}" if price_history else "価格履歴はありません。"
    
    # === 精度を高めるための新しいプロンプト ===
    messages = [
        {
            "role": "system",
            "content": """
            あなたは、価格比較サイトのAI専門家として、消費者が商品の購入を判断するための、具体的で役立つアドバイスを提供します。
            
            以下の点を厳守して回答を生成してください。
            1.  **分析の構成:** 必ず以下の2つの要素を含むJSON形式で回答してください。
                -   `headline`: 商品の価格状況を一言で要約する、キャッチーで簡潔な見出し（20文字以内）。
                -   `detail`: 過去の価格履歴に基づいた詳細な分析。
            2.  **詳細分析の要件:**
                -   現在の価格が過去の価格と比較してどうであるかを明確に述べる。
                -   「現在の価格は過去の最低価格を更新しました」「過去の価格帯と比較して平均的な水準です」といった具体的な表現を使用する。
                -   価格動向を読み解き、「今が買い時」または「もうしばらく様子を見るべき」といった具体的な行動提案を行う。
                -   将来の価格変動について、可能性のある要因（季節的なセール、新モデルの発表など）に言及する。
                -   感情的ではなく、データに基づいた客観的なトーンで記述する。
                -   文章の長さは、読みやすさを考慮し、最大でも200文字程度に収める。
            3.  **JSON形式の厳守:**
                -   回答は常にJSONオブジェクト `{ "headline": "...", "detail": "..." }` の形式であること。
                -   JSON内に余分なテキストやマークダウンを含めないこと。
            """
        },
        {
            "role": "user",
            "content": f"""
            以下の商品の価格について分析してください。
            商品名: {product_name}
            現在の価格: {product_price}円
            価格履歴: {history_text}
            
            この情報から、消費者に役立つ購入アドバイスを提供してください。
            """
        }
    ]

    try:
        response = requests.post(
            OPENAI_API_URL,
            headers=headers,
            json={"model": MODEL_NAME, "messages": messages, "response_format": {"type": "json_object"}}
        )
        response.raise_for_status() # HTTPエラーが発生した場合に例外を発生させる
        
        # レスポンスからJSONを抽出
        raw_content = response.json()["choices"][0]["message"]["content"]
        
        # JSONをパース
        analysis_data = json.loads(raw_content)
        headline = analysis_data.get("headline", "分析不可")
        detail = analysis_data.get("detail", "詳細なAI分析は現在準備中です。")

        return headline, detail

    except requests.exceptions.RequestException as e:
        print(f"APIリクエストエラーが発生しました: {e}")
        return "AI分析失敗", "APIリクエスト中にエラーが発生しました。時間を置いて再度お試しください。"
    except json.JSONDecodeError:
        print(f"APIからの応答が有効なJSONではありません: {raw_content}")
        return "分析エラー", "AIからの応答形式が不正です。再試行してください。"
    except KeyError:
        print(f"APIからの応答に必要なキーが見つかりません: {raw_content}")
        return "分析エラー", "AIからの応答データが不完全です。再試行してください。"
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        return "AI分析失敗", "予期せぬエラーが発生しました。"

def generate_html_file(title, content, filepath, is_product_page=False, product_data=None):
    """
    指定されたタイトルとコンテンツでHTMLファイルを生成する。
    """
    # Tailwind CSS CDNとInterフォントを読み込む
    head = f"""
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            body {{
                font-family: 'Inter', sans-serif;
            }}
            .card {{
                transition: transform 0.2s;
            }}
            .card:hover {{
                transform: translateY(-5px);
            }}
        </style>
    </head>
    """

    # ヘッダーとフッター
    header = """
    <header class="bg-blue-600 text-white p-4 shadow-md sticky top-0 z-50">
        <div class="container mx-auto flex justify-between items-center">
            <a href="index.html" class="text-2xl font-bold rounded-lg px-3 py-1 hover:bg-blue-700 transition">PriceScope</a>
            <nav>
                <a href="index.html" class="mx-2 hover:underline">ホーム</a>
                <a href="about.html" class="mx-2 hover:underline">このサイトについて</a>
            </nav>
        </div>
    </header>
    """

    footer = """
    <footer class="bg-gray-800 text-white p-6 mt-12">
        <div class="container mx-auto text-center">
            <p>&copy; 2024 PriceScope. All rights reserved.</p>
            <div class="mt-4">
                <a href="privacy.html" class="mx-2 hover:underline">プライバシーポリシー</a> | 
                <a href="disclaimer.html" class="mx-2 hover:underline">免責事項</a> | 
                <a href="contact.html" class="mx-2 hover:underline">お問い合わせ</a>
            </div>
        </div>
    </footer>
    """

    # スクリプトとボタンのコンテナ
    script_and_button_container = ""
    if is_product_page:
        script_and_button_container = f"""
        <!-- 商品ページ専用のスクリプトとボタンコンテナ -->
        <div class="fixed bottom-0 left-0 right-0 bg-white p-4 shadow-lg flex justify-center items-center">
            <button id="buyButton" class="bg-green-500 hover:bg-green-600 text-white font-bold py-3 px-8 rounded-full shadow-lg transition transform hover:scale-105">
                購入ページへ進む
            </button>
        </div>
        <script>
            document.getElementById('buyButton').addEventListener('click', () => {{
                window.location.href = "{product_data['buy_url']}";
            }});
        </script>
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
        {script_and_button_container}
    </body>
    </html>
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

def create_index_page(products, output_dir):
    """
    商品一覧ページ（index.html）を生成する。
    """
    total_products = len(products)
    total_pages = math.ceil(total_products / PRODUCTS_PER_PAGE)
    
    # ページごとに商品データを分割
    for page_num in range(1, total_pages + 1):
        start_index = (page_num - 1) * PRODUCTS_PER_PAGE
        end_index = start_index + PRODUCTS_PER_PAGE
        page_products = products[start_index:end_index]
        
        # 商品カードを生成
        products_html = ""
        for product in page_products:
            products_html += f"""
            <div class="bg-white rounded-xl shadow-lg p-6 flex flex-col items-center text-center card">
                <a href="{product['page_url']}">
                    <img src="{product['image_url']}" alt="{product['product_name']}" class="w-48 h-48 object-contain rounded-lg mb-4">
                    <h2 class="text-xl font-semibold text-gray-800 mb-2">{product['product_name']}</h2>
                    <p class="text-3xl font-bold text-red-600 mb-2">¥{product['product_price']:,}</p>
                    <div class="text-sm text-gray-500">
                        <span class="font-bold text-green-600">{product['ai_headline']}</span>
                    </div>
                </a>
            </div>
            """
        
        # ページネーションリンクを生成
        pagination_html = ""
        if total_pages > 1:
            pagination_html = '<div class="flex justify-center mt-8 space-x-2">'
            for i in range(1, total_pages + 1):
                page_file = f'index.html' if i == 1 else f'index_{i}.html'
                is_current_page = 'bg-blue-600 text-white' if i == page_num else 'bg-white text-blue-600 hover:bg-gray-200'
                pagination_html += f"""
                <a href="{page_file}" class="px-4 py-2 border rounded-lg {is_current_page}">{i}</a>
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
        generate_html_file('PriceScope - 商品一覧', content, filepath)
        
    print("商品一覧ページが生成されました。")

def create_product_pages(products, output_dir):
    """
    各商品の詳細ページを生成する。
    """
    for product in products:
        product_html = f"""
        <div class="bg-white rounded-xl shadow-lg overflow-hidden p-8 flex flex-col md:flex-row items-center md:items-start space-y-6 md:space-y-0 md:space-x-12">
            <div class="flex-shrink-0 w-64 h-64 flex items-center justify-center">
                <img src="{product['image_url']}" alt="{product['product_name']}" class="max-w-full max-h-full object-contain rounded-lg">
            </div>
            <div class="flex-grow text-center md:text-left">
                <h1 class="text-4xl font-bold text-gray-800 mb-4">{product['product_name']}</h1>
                <p class="text-5xl font-extrabold text-red-600 mb-6">¥{product['product_price']:,}</p>
                
                <!-- 価格分析AIブロック -->
                <div class="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-8">
                    <h3 class="text-2xl font-bold text-blue-800 mb-2">AI価格分析</h3>
                    <p class="text-xl font-bold text-blue-600 mb-2">「{product['ai_headline']}」</p>
                    <p class="text-gray-700 leading-relaxed">{product['ai_detail']}</p>
                </div>
                
                <!-- 商品説明 -->
                <div class="mb-8">
                    <h3 class="text-2xl font-bold text-gray-800 mb-2">商品概要</h3>
                    <p class="text-gray-600">{product['description']}</p>
                </div>

                <!-- 価格履歴グラフを埋め込む場所 (今回はテキストで代替) -->
                <div>
                    <h3 class="text-2xl font-bold text-gray-800 mb-2">価格履歴</h3>
                    <div class="bg-gray-100 rounded-lg p-4">
                        <p class="text-gray-600">{product['price_history']}</p>
                    </div>
                </div>
            </div>
        </div>
        """
        generate_html_file(
            f'PriceScope - {product["product_name"]}',
            product_html,
            os.path.join(output_dir, product['page_url']),
            is_product_page=True,
            product_data=product
        )
    print("商品詳細ページが生成されました。")

def create_static_pages(output_dir):
    """
    静的ページ（プライバシー、免責事項など）を生成する。
    """
    pages = {
        'privacy.html': {
            'title': 'プライバシーポリシー',
            'content': """
            <h1 class="text-4xl font-bold text-gray-800 mb-8">プライバシーポリシー</h1>
            <p class="text-gray-600">このサイトは、ユーザーのプライバシー保護を最優先に考えています。個人情報の収集や利用は行いません。</p>
            <p class="text-gray-600 mt-4">当サイトは、商品情報の比較と分析のみを目的としており、外部サービスへのリンクを除き、ユーザーの追跡やデータの保存は行いません。安心してご利用ください。</p>
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
            <p class="text-gray-600 mt-4 font-bold">contact@example.com</p>
            """
        },
        'about.html': {
            'title': 'このサイトについて',
            'content': """
            <h1 class="text-4xl font-bold text-gray-800 mb-8">このサイトについて</h1>
            <p class="text-gray-600">PriceScopeは、最新のAI技術を活用して、様々な商品の価格動向を分析し、ユーザーにとって最適な「買い時」を提案する価格比較サイトです。</p>
            <p class="text-gray-600 mt-4">膨大なデータをAIが解析することで、市場のトレンドや価格の変動パターンを予測。これにより、ユーザーはより賢く、よりお得に商品を購入することができます。私たちは、消費者が情報過多の時代に正しい選択ができるよう、信頼性の高い情報提供を目指しています。</p>
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
    base_url = "https://your-website.com/" # サイトのベースURLを設定
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""
    
    # メインページと静的ページ
    static_pages = ["index.html", "about.html", "privacy.html", "disclaimer.html", "contact.html"]
    for page in static_pages:
        sitemap_content += f"""  <url>
    <loc>{base_url}{page}</loc>
    <lastmod>{date.today().isoformat()}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
"""

    # ページネーションページ
    total_products = len(products)
    total_pages = math.ceil(total_products / PRODUCTS_PER_PAGE)
    for i in range(2, total_pages + 1):
        sitemap_content += f"""  <url>
    <loc>{base_url}index_{i}.html</loc>
    <lastmod>{date.today().isoformat()}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.7</priority>
  </url>
"""

    # 商品詳細ページ
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
    
    print("ダミー商品データを準備中...")
    # ダミーの商品データを作成
    products_data = []
    # 価格履歴生成用のヘルパー関数
    def generate_price_history():
        base_price = random.randint(15000, 100000)
        history = {}
        for i in range(5, 0, -1):
            date_str = (date.today() - timedelta(days=i*30)).isoformat()
            price_change = random.randint(-5000, 5000)
            history[date_str] = max(10000, base_price + price_change)
        history[(date.today() - timedelta(days=1)).isoformat()] = random.randint(base_price - 3000, base_price + 3000)
        return history

    from datetime import timedelta
    for i in range(1, 101): # 100個のダミー商品
        product_name = f"最新ガジェット {i}"
        price_history = generate_price_history()
        current_price = list(price_history.values())[-1]
        
        # AI分析を生成
        ai_headline, ai_detail = generate_ai_analysis(product_name, current_price, json.dumps(price_history, indent=2))
        
        # URLをクリーンアップ
        page_url = f"products/product_{i}.html"
        
        products_data.append({
            'product_name': product_name,
            'product_price': current_price,
            'price_history': json.dumps(price_history, indent=2),
            'description': f"これは、{product_name}に関する詳細な商品説明です。画期的な機能と優れたデザインを備えています。",
            'buy_url': f"https://example.com/buy/{i}",
            'image_url': f"https://placehold.co/400x400/2180A0/ffffff?text=Product+{i}",
            'page_url': page_url,
            'ai_headline': ai_headline,
            'ai_detail': ai_detail
        })
        print(f"商品 {i}/{len(products_data)} のAI分析を生成しました。")
        time.sleep(1) # API呼び出しのレート制限を考慮して間隔を空ける

    # 商品詳細ページのディレクトリを作成
    os.makedirs(os.path.join(output_dir, 'products'), exist_ok=True)
    
    print("ウェブサイトのファイル生成を開始します。")
    create_index_page(products_data, output_dir)
    create_product_pages(products_data, output_dir)
    create_static_pages(output_dir)
    create_sitemap(products_data, output_dir)
    print("サイトのファイル生成が完了しました。")

if __name__ == "__main__":
    generate_website()
