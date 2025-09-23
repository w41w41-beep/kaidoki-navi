import os
import shutil
import json
import math
import csv
from datetime import date
from dotenv import load_dotenv
import requests
import openai
from collections import defaultdict
import time
import re

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数を取得
RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AMAZON_AFFILIATE_LINK = os.getenv("AMAZON_AFFILIATE_LINK")

# OpenAI APIキーを設定
openai.api_key = OPENAI_API_KEY

PRODUCTS_PER_PAGE = 10  # 1ページあたりの商品数
OPENAI_MODEL = "gpt-4o-mini" # 使用するAIモデル

# キャッシュファイルのパス
PRODUCTS_CACHE_FILE = 'products_cache.json'
TAGS_CACHE_FILE = 'tags_cache.json'

# カテゴリデータ
categories = {
    "家電": ["テレビ・レコーダー", "オーディオ", "カメラ", "季節・空調家電", "生活家電", "キッチン家電", "理美容家電", "健康家電"],
    "PC・スマホ": ["パソコン", "タブレットPC", "スマートフォン", "PC周辺機器", "PCパーツ・ソフト"],
}

# 独自のカテゴリ
special_categories = {
    "最安値": sorted(list(set(cat for sub_cats in categories.values() for cat in sub_cats))),
    "セール・限定": ["期間限定", "特別セール"],
}

# 楽天APIから商品を取得
def fetch_rakuten_items(keyword="家電", genre_id="", hits=10):
    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "keyword": keyword,
        "genreId": genre_id,
        "format": "json",
        "hits": hits,
        "sort": "-itemPrice",
        "availability": 0,
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("Items", [])
    except requests.exceptions.RequestException as e:
        print(f"楽天APIリクエストエラー: {e}")
        return []

# キャッシュの読み込みと保存
def load_cache(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"キャッシュファイル {file_path} が破損しています。新しく作成します。")
                return {}
    return {}

def save_cache(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# AI分析を実行する関数
def get_ai_analysis(product_data, existing_data=None):
    if existing_data is None:
        existing_data = {}

    current_price = product_data.get('price', 0)
    name = product_data.get('name', '')
    description = product_data.get('description', '')
    
    # 価格履歴から最新価格と過去価格を取得
    price_history = existing_data.get('price_history', [])
    
    # 既存データがあれば、現在の価格を追加
    if price_history:
        # 重複する日付のデータを避ける
        if price_history[-1]['date'] != date.today().isoformat():
            price_history.append({"date": date.today().isoformat(), "price": current_price})
    else:
        price_history = [{"date": date.today().isoformat(), "price": current_price}]

    # 変更フラグ
    price_changed = False
    if len(price_history) > 1 and price_history[-2]['price'] != current_price:
        price_changed = True

    # 新規商品または価格が変動した場合のみAI分析を再実行
    if not existing_data or price_changed:
        price_analysis = "現在価格は過去と比べて安定しています。"
        if len(price_history) > 1:
            avg_price = sum(item['price'] for item in price_history) / len(price_history)
            max_price = max(item['price'] for item in price_history)
            min_price = min(item['price'] for item in price_history)
            
            if current_price < avg_price * 0.9:
                price_analysis = f"過去の平均価格（約{int(avg_price):,}円）より**大幅に安くなっています！** 今が買い時です！"
            elif current_price < min_price * 1.05:
                price_analysis = f"過去最安値に近い価格です（過去最安値：{int(min_price):,}円）。"
            elif current_price > avg_price * 1.1:
                price_analysis = f"過去の平均価格（約{int(avg_price):,}円）より**高くなっています**。もう少し待つのが賢明かもしれません。"
        
        # GPTに問い合わせるためのプロンプトを構築
        try:
            prompt = (
                f"あなたは商品の購買分析を行うAIアシスタントです。以下の商品の情報をもとに、"
                f"1. 商品の注目ポイント（AI Headline）を15文字程度で簡潔に提示。"
                f"2. 買い時分析（AI Analysis）を50文字から100文字程度で詳細に解説。"
                f"3. 商品の主要な特徴を3つのハイライト（AI Summary）として、それぞれ50文字から100文字程度で箇条書き形式にまとめてください。ハイライトは、商品の説明文から具体的な機能やメリットを抜粋してください。"
                f"4. 3〜5個の関連するタグ（Tags）を、記号なしの単語で抽出してください。例：['軽量', '高機能', '4K']"
                f"5. 適切なサブカテゴリー（Sub Category）を一つだけ日本語で選んでください。例：'キッチン家電'"
                f"\n\n---商品情報---\n商品名: {name}\n価格: {current_price}円\n商品詳細: {description}"
                f"\n価格分析: {price_analysis}\n---"
                f"\n\n回答はJSON形式で、キーを 'ai_headline', 'ai_analysis', 'ai_summary', 'tags', 'sub_category' としてください。"
                f"ai_summaryは箇条書きを改行と合わせて出力してください。"
            )

            completion = openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "あなたはプロのウェブサイト制作者であり、商品の魅力と買い時を的確に伝えるAIです。ユーザーの指示に厳密に従ってください。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            analysis_result = json.loads(completion.choices[0].message.content)

            # AIによる買い時分析に価格分析情報を追加
            analysis_result['ai_analysis'] = f"{analysis_result['ai_analysis']} {price_analysis}"
            
            return {
                'ai_headline': analysis_result.get('ai_headline', 'AI分析準備中'),
                'ai_analysis': analysis_result.get('ai_analysis', '詳細なAI分析は現在準備中です。'),
                'ai_summary': analysis_result.get('ai_summary', 'この商品の詳しい説明は準備中です。'),
                'tags': analysis_result.get('tags', []),
                'sub_category': analysis_result.get('sub_category', 'その他'),
                'price_history': price_history
            }

        except Exception as e:
            print(f"AI分析中にエラーが発生しました: {e}")
            return {
                'ai_headline': 'AI分析に失敗しました',
                'ai_analysis': 'AI分析に失敗しました。',
                'ai_summary': 'AI分析に失敗しました。',
                'tags': [],
                'sub_category': 'その他',
                'price_history': price_history
            }
    else:
        # 価格が変動していない場合は、キャッシュから必要な情報を返す
        return {
            'ai_headline': existing_data.get('ai_headline'),
            'ai_analysis': existing_data.get('ai_analysis'),
            'ai_summary': existing_data.get('ai_summary'),
            'tags': existing_data.get('tags'),
            'sub_category': existing_data.get('sub_category'),
            'price_history': price_history
        }


def update_products_csv(rakuten_products):
    products_cache = load_cache(PRODUCTS_CACHE_FILE)
    
    updated_products = []
    
    for item in rakuten_products:
        item_data = item['Item']
        item_code = item_data['itemCode']
        
        # 既存の商品データがあるか確認
        existing_product = products_cache.get(item_code)
        
        # 新しい価格
        current_price = int(item_data['itemPrice'])
        
        product = {
            'name': item_data['itemName'],
            'price': current_price,
            'url': item_data['itemUrl'],
            'image_url': item_data['mediumImageUrls'][0]['imageUrl'],
            'description': item_data['itemCaption'],
            'page_url': f"products/{item_code.replace(':', '_')}.html", # URLの特殊文字を置き換える
            'rakuten_url': item_data['itemUrl'],
            'item_code': item_code,
            'category': {
                'main': 'その他',
                'sub': 'その他'
            },
            'tags': [],
            'ai_headline': '',
            'ai_analysis': '',
            'ai_summary': '',
            'price_history': []
        }
        
        # AI分析を実行
        ai_data = get_ai_analysis(product, existing_product)
        
        # AI分析結果を商品データに統合
        product.update(ai_data)

        # サブカテゴリーからメインカテゴリーを自動設定
        for main_cat, sub_cats in categories.items():
            if product['category']['sub'] in sub_cats:
                product['category']['main'] = main_cat
                break

        updated_products.append(product)
        
    # 新しいキャッシュデータを作成
    new_products_cache = {p['item_code']: p for p in updated_products}
    save_cache(new_products_cache, PRODUCTS_CACHE_FILE)
    
    return updated_products

# 静的サイト生成
def generate_site(products):
    
    def generate_header_footer(page_path, sub_cat_links=None, page_title="お得な商品の買い時をナビゲート！"):
        main_links_html = """
            <a href="{base_path}index.html">トップ</a><span class="separator">|</span>
            <a href="{base_path}category/家電.html">家電</a><span class="separator">|</span>
            <a href="{base_path}category/PC・スマホ.html">PC・スマホ</a><span class="separator">|</span>
            <a href="{base_path}category/最安値.html">最安値</a><span class="separator">|</span>
            <a href="{base_path}category/セール・限定.html">セール・限定</a><span class="separator">|</span>
            <a href="{base_path}tags/index.html">タグから探す</a>
        """
        
        base_path = os.path.relpath('.', os.path.dirname(page_path)).replace('\\', '/')
        if base_path != '.':
            base_path += '/'
        else:
            base_path = './'
        
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
            <h1><a href="{base_path}index.html">カイドキ-ナビ</a></h1>
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
            {'' if sub_cat_links is None else "".join([f'<a href="{base_path}category/{sub_cat.replace(" ", "")}.html">{sub_cat}</a><span class="separator">|</span>' for sub_cat in sorted(sub_cat_links)])}
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
    
    # 既存のHTMLファイルを削除
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
        page_path = f"category/{main_cat.replace(' ', '')}.html"
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
        print(f"category/{main_cat.replace(' ', '')}.html が生成されました。")
    
    # 独自のカテゴリのページ生成
    for special_cat, sub_cats in special_categories.items():
        page_path = f"category/{special_cat.replace(' ', '')}.html"
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
        print(f"category/{special_cat.replace(' ', '')}.html が生成されました。")
        
        for sub_cat in sub_cats:
            sub_cat_file_name = f"{sub_cat.replace(' ', '')}.html"
            page_path = f"category/{sub_cat_file_name}"
            
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
            print(f"category/{sub_cat_file_name} が生成されました。")

    # トップページとページネーションの生成
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
    
    # 個別商品ページの生成
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
                <p class="item-category">カテゴリ：<a href="{os.path.relpath('category/' + product.get('category', {}).get('main', '').replace(' ', '') + '.html', os.path.dirname(page_path))}">{product.get('category', {}).get('main', '')}</a> &gt; <a href="{os.path.relpath('category/' + product.get('category', {}).get('sub', '').replace(' ', '') + '.html', os.path.dirname(page_path))}">{product.get('category', {}).get('sub', '')}</a></p>
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
                    {"".join([f'<a href="{os.path.relpath("tags/" + tag.replace(" ", "") + ".html", os.path.dirname(page_path))}" class="tag-button">#{tag}</a>' for tag in product.get('tags', [])])}
                </div>
            </div>
        </div>
    </div>
</main>
"""
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(header + item_html_content + footer)
        print(f"{page_path} が生成されました。")
    
    # タグ関連ページの生成
    all_tags = sorted(list(set(tag for product in products for tag in product.get('tags', []))))

    if all_tags:
        os.makedirs('tags', exist_ok=True)
        tag_list_html_content = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">タグから探す</h2>
        <div class="product-tags all-tags-list">
            {"".join([f'<a href="{tag.replace(" ", "")}.html" class="tag-button">#{tag}</a>' for tag in all_tags])}
        </div>
    </div>
</main>
"""
        tag_header, tag_footer = generate_header_footer('tags/index.html', page_title="タグ一覧")
        with open('tags/index.html', 'w', encoding='utf-8') as f:
            f.write(tag_header + tag_list_html_content + tag_footer)
        print("タグ一覧ページ: tags/index.html が生成されました。")

        for tag in all_tags:
            tag_page_path = f'tags/{tag.replace(" ", "")}.html'
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

    # 静的ページ（プライバシーポリシー、免責事項、お問い合わせ）の生成
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

    # サイトマップの生成
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
        
        all_categories = {**categories, **special_categories}
        for main_cat, sub_cats in all_categories.items():
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}category/{main_cat.replace(" ", "")}.html</loc>\n'
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
        
        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>{base_url}tags/index.html</loc>\n'
        sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
        sitemap_content += '    <changefreq>daily</changefreq>\n'
        sitemap_content += '    <priority>0.8</priority>\n'
        sitemap_content += '  </url>\n'
        
        for tag in all_tags:
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{base_url}tags/{tag.replace(" ", "")}.html</loc>\n'
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
