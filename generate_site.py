import json
import math
import os
import shutil
from datetime import date
import requests
from openai import OpenAI

# 定数定義
PRODUCTS_PER_PAGE = 24
TAGS_PER_PAGE = 50
BASE_URL = "https://w41w41-beep.github.io/kaidoki-navi/"

# 楽天のジャンルIDとサイトのカテゴリーのマッピングを定義
RAKUTEN_GENRE_MAP = {
    # 家電
    "掃除機": {
        "main": "家電",
        "sub": "掃除機",
        "ids": ["212871", "562768"] # 掃除機・クリーナー、ロボット掃除機
    },
    "空気清浄機": {
        "main": "家電",
        "sub": "空気清浄機",
        "ids": ["210214"] # 空気清浄機
    },
    "エアコン": {
        "main": "家電",
        "sub": "エアコン",
        "ids": ["100032"] # エアコン
    },
    "冷蔵庫": {
        "main": "家電",
        "sub": "冷蔵庫",
        "ids": ["100259"] # 冷蔵庫
    },
    "電子レンジ": {
        "main": "家電",
        "sub": "電子レンジ",
        "ids": ["100262"] # 電子レンジ・オーブンレンジ
    },
    
    # パソコン・周辺機器
    "ノートPC": {
        "main": "パソコン",
        "sub": "ノートPC",
        "ids": ["562629"] # ノートPC
    },
    "デスクトップPC": {
        "main": "パソコン",
        "sub": "デスクトップPC",
        "ids": ["562630"] # デスクトップPC
    },
    "モニター": {
        "main": "パソコン",
        "sub": "モニター",
        "ids": ["200109"] # ディスプレイ
    },
    "プリンター": {
        "main": "パソコン",
        "sub": "プリンター",
        "ids": ["100277"] # プリンタ
    },
    "周辺機器": {
        "main": "パソコン",
        "sub": "周辺機器",
        "ids": ["200100", "200101", "200102"] # パソコン周辺機器、マウス・キーボード
    }
}

# ヤフーショッピングのカテゴリーIDとサイトのカテゴリーのマッピングを定義
YAHOO_CATEGORY_MAP = {
    # 家電
    "掃除機": {
        "main": "家電",
        "sub": "掃除機",
        "ids": ["12999"]
    },
    "空気清浄機": {
        "main": "家電",
        "sub": "空気清浄機",
        "ids": ["12479"]
    },
    "エアコン": {
        "main": "家電",
        "sub": "エアコン",
        "ids": ["2513"]
    },
    "冷蔵庫": {
        "main": "家電",
        "sub": "冷蔵庫",
        "ids": ["12995"]
    },
    "電子レンジ": {
        "main": "家電",
        "sub": "電子レンジ",
        "ids": ["12996"]
    },
    
    # パソコン・周辺機器
    "ノートPC": {
        "main": "パソコン",
        "sub": "ノートPC",
        "ids": ["2502"]
    },
    "デスクトップPC": {
        "main": "パソコン",
        "sub": "デスクトップPC",
        "ids": ["2502"]
    },
    "モニター": {
        "main": "パソコン",
        "sub": "モニター",
        "ids": ["2505"]
    },
    "プリンター": {
        "main": "パソコン",
        "sub": "プリンター",
        "ids": ["2508"]
    },
    "周辺機器": {
        "main": "パソコン",
        "sub": "周辺機器",
        "ids": ["2507", "12984"] # マウス、キーボード
    }
}

# OpenAIクライアントの初期化
client = OpenAI(
    api_key=os.environ.get('OPENAI_API_KEY')
)

def generate_ai_info(item_name, item_description, item_category):
    """AIを使って製品スペックとタグを生成する関数"""
    prompt = f"""
以下の商品の情報から、主な製品仕様（スペック）を箇条書きで分かりやすく簡潔にまとめてください。
また、ユーザーが検索しそうなキーワードを3〜5個、単語で抽出して「タグ」として生成してください。

商品名: {item_name}
商品説明: {item_description}
カテゴリ: {item_category['main']} > {item_category['sub']}

---
出力形式：
スペック：
- [スペック1]
- [スペック2]
- ...
タグ：
[タグ1], [タグ2], [タグ3], ...
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        content = response.choices[0].message.content.strip()
        
        # 出力形式を解析
        specs_start = content.find("スペック：")
        tags_start = content.find("タグ：")
        
        specs_text = content[specs_start + len("スペック："):tags_start].strip()
        tags_text = content[tags_start + len("タグ："):].strip()
        
        specs_list = [line.lstrip('- ').strip() for line in specs_text.split('\n') if line.lstrip('- ').strip()]
        tags_list = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
        
        return {
            "specs": "\n".join([f"・{spec}" for spec in specs_list]),
            "tags": tags_list
        }

    except Exception as e:
        print(f"AI情報生成中にエラーが発生しました: {e}")
        return {
            "specs": "AIによる製品仕様の生成に失敗しました。",
            "tags": []
        }

def fetch_rakuten_items():
    """楽天APIから複数のカテゴリで商品データを取得する関数"""
    app_id = os.environ.get('RAKUTEN_API_KEY')
    if not app_id:
        print("RAKUTEN_API_KEYが設定されていません。")
        return []

    all_products = []
    
    for cat_info in RAKUTEN_GENRE_MAP.values():
        main_cat = cat_info["main"]
        sub_cat = cat_info.get("sub", "")
        genre_ids = cat_info["ids"]
        
        for genre_id in genre_ids:
            url = f"https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706?applicationId={app_id}&genreId={genre_id}&format=json&sort=-reviewCount&hits=10"
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                items = data.get('Items', [])
                
                for item in items:
                    item_data = item['Item']
                    
                    all_products.append({
                        "id": item_data['itemCode'],
                        "name": item_data['itemName'],
                        "price": f"{int(item_data['itemPrice']):,}",
                        "image_url": item_data['mediumImageUrls'][0]['imageUrl'],
                        "rakuten_url": item_data['itemUrl'],
                        "yahoo_url": "https://shopping.yahoo.co.jp/", 
                        "amazon_url": "https://www.amazon.co.jp/ref=as_li_ss_il?ie=UTF8&linkCode=ilc&tag=soc07-22&linkId=db3c1808e6f1f516353d266e76811a7c&language=ja_JP",
                        "page_url": f"pages/{item_data['itemCode']}.html",
                        "category": {
                            "main": main_cat,
                            "sub": sub_cat
                        },
                        "ai_analysis": "AIによる価格分析は近日公開！",
                        "description": item_data.get('itemCaption', '商品説明は現在準備中です。'),
                        "date": date.today().isoformat(),
                        "main_ec_site": "楽天"
                    })
            except requests.exceptions.RequestException as e:
                print(f"楽天APIへのリクエスト中にエラーが発生しました: {e}")

    return all_products

def fetch_yahoo_items():
    """Yahoo!ショッピングAPIから商品データを取得する関数"""
    app_id = os.environ.get('YAHOO_API_KEY')
    if not app_id:
        print("YAHOO_API_KEYが設定されていません。")
        return []

    all_products = []
    
    for cat_info in YAHOO_CATEGORY_MAP.values():
        main_cat = cat_info["main"]
        sub_cat = cat_info.get("sub", "")
        category_ids = cat_info["ids"]
        
        for category_id in category_ids:
            url = f"https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch?appid={app_id}&category_id={category_id}&sort=-review_count&hits=5"
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                items = data.get('hits', [])
                
                for item in items:
                    all_products.append({
                        "id": item['jan_code'],
                        "name": item['name'],
                        "price": f"{int(item['price']):,}",
                        "image_url": item['image']['medium'],
                        "rakuten_url": "https://www.rakuten.co.jp/",
                        "yahoo_url": item['url'],
                        "amazon_url": "https://www.amazon.co.jp/ref=as_li_ss_il?ie=UTF8&linkCode=ilc&tag=soc07-22&linkId=db3c1808e6f1f516353d266e76811a7c&language=ja_JP",
                        "page_url": f"pages/{item['jan_code']}.html",
                        "category": {
                            "main": main_cat,
                            "sub": sub_cat
                        },
                        "ai_analysis": "AIによる価格分析は近日公開！",
                        "description": item.get('description', '商品説明は現在準備中です。'),
                        "date": date.today().isoformat(),
                        "main_ec_site": "Yahoo!"
                    })
            except requests.exceptions.RequestException as e:
                print(f"Yahoo! APIへのリクエスト中にエラーが発生しました: {e}")
            
    return all_products

def update_products_json(new_products):
    """新しい商品データを既存のproducts.jsonに統合・更新する関数"""
    try:
        if os.path.exists('products.json'):
            with open('products.json', 'r', encoding='utf-8') as f:
                existing_products = json.load(f)
        else:
            existing_products = []
    except json.JSONDecodeError:
        print("products.jsonが破損しているため、新規作成します。")
        existing_products = []

    updated_products = {p['id']: p for p in existing_products}
    
    # 新しい商品情報をAIで生成して追加
    for new_product in new_products:
        ai_info = generate_ai_info(
            item_name=new_product['name'],
            item_description=new_product['description'],
            item_category=new_product['category']
        )
        new_product['specs'] = ai_info['specs']
        new_product['tags'] = ai_info['tags']
        updated_products[new_product['id']] = new_product
    
    final_products = list(updated_products.values())
    
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(final_products, f, ensure_ascii=False, indent=4)
    
    print(f"products.jsonが更新されました。現在 {len(final_products)} 個の商品を追跡中です。")
    return final_products

def generate_site(products):
    """products.jsonを読み込み、HTMLファイルを生成する関数"""
    today = date.today().isoformat()
    for product in products:
        if 'date' not in product:
            product['date'] = today
    products.sort(key=lambda p: p['date'], reverse=True)
    
    categories = {}
    for product in products:
        main_cat = product['category']['main']
        sub_cat = product['category']['sub']
        if main_cat not in categories:
            categories[main_cat] = set()
        if sub_cat:
            categories[main_cat].add(sub_cat)

    sorted_main_cats = sorted(categories.keys())

    # サイトのディレクトリをクリーンアップ
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.html') and not file in ['privacy.html', 'disclaimer.html', 'contact.html']:
                os.remove(os.path.join(root, file))
    if os.path.exists('category'):
        shutil.rmtree('category')
    if os.path.exists('pages'):
        shutil.rmtree('pages')
    if os.path.exists('tags'):
        shutil.rmtree('tags')

    def _get_base_path(current_path):
        """現在のページのパスから相対パスを計算するヘルパー関数"""
        depth = current_path.count('/')
        return "../" * depth if depth > 0 else "."

    def _generate_header_footer(current_path, sub_cat_links=None, page_title="お得な買い時を見つけよう！"):
        """ヘッダーとフッターのHTMLを生成するヘルパー関数"""
        base_path = _get_base_path(current_path)
        main_links_html = f'<a href="{base_path}/tags/index.html">タグから探す</a><span class="separator">|</span>'
        for mc_link in sorted_main_cats:
            main_links_html += f'<a href="{base_path}/category/{mc_link}/index.html">{mc_link}</a><span class="separator">|</span>'
        header_html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>カイドキ-ナビ | {page_title}</title>
    <link rel="stylesheet" href="{base_path}/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <meta name="google-site-verification" content="OmUuOjcxi7HXBKe47sd0WPbzCfbCOFbPj_iueHBk2qo" />
</head>
<body>
    <header>
        <div class="container">
            <h1><a href="{base_path}/index.html">カイドキ-ナビ</a></h1>
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
            {main_links_html}
        </div>
    </div>
"""
        sub_cat_links_html = ""
        if sub_cat_links:
            sub_cat_links_html += '<div class="genre-links sub-genre-links">'
            for sub_cat_link in sorted(list(sub_cat_links)):
                sub_cat_links_html += f'<a href="{sub_cat_link.replace(" ", "")}.html">{sub_cat_link}</a><span class="separator">|</span>'
            sub_cat_links_html += '</div>'
            header_html += f"""
    <div class="sub-genre-links-container">
        {sub_cat_links_html}
    </div>
"""
        footer_html = f"""
    </main>
    <footer>
        <p>&copy; 2025 カイドキ-ナビ. All Rights Reserved.</p>
        <div class="footer-links">
            <a href="{base_path}/privacy.html">プライバシーポリシー</a>
            <a href="{base_path}/disclaimer.html">免責事項</a>
            <a href="{base_path}/contact.html">お問い合わせ</a>
        </div>
    </footer>
    <script src="{base_path}/script.js"></script>
</body>
</html>
        """
        return header_html, footer_html

    def _generate_product_card_html(product, current_path):
        """商品カードのHTMLを生成するヘルパー関数"""
        link_path = os.path.relpath(product['page_url'], os.path.dirname(current_path))
        return f"""
<a href="{link_path}" class="product-card">
    <img src="{product['image_url']}" alt="{product['name']}">
    <div class="product-info">
        <h3 class="product-name">{product['name'][:20] + '...' if len(product['name']) > 20 else product['name']}</h3>
        <p class="product-price">{product['price']}円</p>
        <div class="price-status-title">💡注目ポイント</div>
        <div class="price-status-content ai-analysis">{product['ai_analysis']}</div>
    </div>
</a>
"""

    def _generate_index_pages(products):
        """トップページとページネーションを生成する関数"""
        total_pages = math.ceil(len(products) / PRODUCTS_PER_PAGE)
        for i in range(total_pages):
            start_index = i * PRODUCTS_PER_PAGE
            end_index = start_index + PRODUCTS_PER_PAGE
            paginated_products = products[start_index:end_index]
            page_num = i + 1
            page_path = 'index.html' if page_num == 1 else f'pages/page{page_num}.html'
            if page_num > 1:
                os.makedirs(os.path.dirname(page_path), exist_ok=True)
            
            header, footer = _generate_header_footer(page_path)
            
            products_html = "".join([_generate_product_card_html(p, page_path) for p in paginated_products])
            
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
    
    def _generate_category_pages(products, categories):
        """カテゴリーページを生成する関数"""
        for main_cat, sub_cats in categories.items():
            main_cat_products = [p for p in products if p['category']['main'] == main_cat]
            page_path = f"category/{main_cat}/index.html"
            os.makedirs(os.path.dirname(page_path), exist_ok=True)
            header, footer = _generate_header_footer(page_path, sub_cat_links=sub_cats, page_title=f"{main_cat}の商品一覧")
            main_content_html = f"""
    <main class="container">
        <div class="ai-recommendation-section">
            <h2 class="ai-section-title">{main_cat}の商品一覧</h2>
            <div class="product-grid">
            """
            products_html = "".join([_generate_product_card_html(p, page_path) for p in main_cat_products])
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(header + main_content_html + products_html + "</div></div>" + footer)
            print(f"category/{main_cat}/index.html が生成されました。")
            
            for sub_cat in sub_cats:
                sub_cat_products = [p for p in products if p['category']['sub'] == sub_cat]
                sub_cat_file_name = f"{sub_cat.replace(' ', '')}.html"
                page_path = f"category/{main_cat}/{sub_cat_file_name}"
                header, footer = _generate_header_footer(page_path, page_title=f"{sub_cat}の商品一覧")
                main_content_html = f"""
    <main class="container">
        <div class="ai-recommendation-section">
            <h2 class="ai-section-title">{sub_cat}の商品一覧</h2>
            <div class="product-grid">
            """
                products_html = "".join([_generate_product_card_html(p, page_path) for p in sub_cat_products])
                with open(page_path, 'w', encoding='utf-8') as f:
                    f.write(header + main_content_html + products_html + "</div></div>" + footer)
                print(f"{page_path} が生成されました。")

    def _generate_product_detail_pages(products):
        """個別商品ページを生成する関数"""
        for product in products:
            page_path = product['page_url']
            dir_name = os.path.dirname(page_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            
            header, footer = _generate_header_footer(page_path, page_title=f"{product['name']}の買い時情報")
            
            ai_analysis_block_html = """
            <div class="ai-analysis-block">
                <div class="ai-analysis-text">
                    <h2>AIによる買い時分析</h2>
                    <p>価格推移グラフとAIによる詳細分析を近日公開！乞うご期待！</p>
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
            
            purchase_button_html = ""
            main_ec_site = product.get("main_ec_site")
            if main_ec_site == "Amazon":
                purchase_button_html = f'<a href="{product["amazon_url"]}" class="purchase-button" target="_blank">Amazonで購入する</a>'
            elif main_ec_site == "楽天":
                purchase_button_html = f'<a href="{product["rakuten_url"]}" class="purchase-button" target="_blank">楽天市場で購入する</a>'
            elif main_ec_site == "Yahoo!":
                purchase_button_html = f'<a href="{product["yahoo_url"]}" class="purchase-button" target="_blank">Yahoo!ショッピングで購入する</a>'
            
            affiliate_links_html = f"""
            <div class="lowest-price-section">
                <p class="lowest-price-label">最安値ショップをチェック！</p>
                <div class="lowest-price-buttons">
                    <a href="{product.get("amazon_url", "https://www.amazon.co.jp/")}" class="btn shop-link" target="_blank">Amazonで見る</a>
                    <a href="{product.get("rakuten_url", "https://www.rakuten.co.jp/")}" class="btn shop-link" target="_blank">楽天市場で見る</a>
                    <a href="{product.get("yahoo_url", "https://shopping.yahoo.co.jp/")}" class="btn shop-link" target="_blank">Yahoo!ショッピングで見る</a>
                </div>
            </div>
            """
            item_html_content = f"""
<main class="container">
    <div class="product-detail">
        <div class="item-detail">
            <div class="item-image">
                <img src="{product['image_url']}" alt="{product['name']}" class="main-product-image">
            </div>
            <div class="item-info">
                <h1 class="item-name">{product['name']}</h1>
                <p class="item-category">カテゴリ：<a href="{os.path.relpath('category/' + product['category']['main'] + '/index.html', os.path.dirname(page_path))}">{product['category']['main']}</a> &gt;
                <a href="{os.path.relpath('category/' + product['category']['main'] + '/' + product['category']['sub'].replace(' ', '') + '.html', os.path.dirname(page_path))}">{product['category']['sub']}</a></p>
                <div class="price-section">
                    <p class="current-price">現在の価格：<span>{product['price']}円</span></p>
                </div>
                <div class="ai-recommendation-section">
                    <div class="price-status-title">💡注目ポイント</div>
                    <div class="price-status-content ai-analysis">{product['ai_analysis']}</div>
                    {purchase_button_html}
                </div>
                {ai_analysis_block_html}
                {affiliate_links_html}
                <div class="item-description">
                    <h2>商品説明</h2>
                    <p>{product.get('description', '商品説明は現在準備中です。')}</p>
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
    
    def _generate_tag_pages(products):
        """タグページを生成する関数"""
        all_tags = sorted(list(set(tag for product in products for tag in product.get('tags', []))))
        total_tag_pages = math.ceil(len(all_tags) / TAGS_PER_PAGE)
        os.makedirs('tags', exist_ok=True)
        
        # タグ一覧ページを生成
        for i in range(total_tag_pages):
            start_index = i * TAGS_PER_PAGE
            end_index = start_index + TAGS_PER_PAGE
            paginated_tags = all_tags[start_index:end_index]
            page_num = i + 1
            page_path = 'tags/index.html' if page_num == 1 else f'tags/page{page_num}.html'
            tag_list_html_content = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">タグから探す</h2>
        <div class="product-tags all-tags-list">
            {"".join([f'<a href="{tag.replace(" ", "")}.html" class="tag-button">#{tag}</a>' for tag in paginated_tags])}
        </div>
    </div>
</main>
"""
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
            tag_header, tag_footer = _generate_header_footer(page_path, page_title="タグ一覧")
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(tag_header + tag_list_html_content + pagination_html + tag_footer)
            print(f"タグページ: {page_path} が生成されました。")
            
        # 個別タグページを生成
        for tag in all_tags:
            tag_page_path = f'tags/{tag.replace(" ", "")}.html'
            tag_products = [product for product in products if tag in product.get('tags', [])]
            tag_page_content = f"""
<main class="container">
    <div class="ai-recommendation-section">
        <h2 class="ai-section-title">#{tag} の商品一覧</h2>
        <div class="product-grid">
            {"".join([_generate_product_card_html(p, tag_page_path) for p in tag_products])}
        </div>
    </div>
</main>
"""
            tag_header, tag_footer = _generate_header_footer(tag_page_path, page_title=f"#{tag} の商品一覧")
            with open(tag_page_path, 'w', encoding='utf-8') as f:
                f.write(tag_header + tag_page_content + tag_footer)
            print(f"タグページ: {tag_page_path} が生成されました。")
    
    def _generate_static_pages():
        """静的ページを生成する関数"""
        def generate_static_page(file_name, title, content_html):
            page_path = file_name
            header, footer = _generate_header_footer(page_path, page_title=title)
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(header + content_html + footer)
            print(f"{page_path} が生成されました。")
        
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
            <p>当サイトは、Amazon.co.jpを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定されたアフィリエイトプログラムである、Amazonアソシエイト・プログラムの参加者です。</p>
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
    
    def _create_sitemap(products, categories):
        """sitemap.xmlを生成する関数"""
        sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>{BASE_URL}</loc>\n'
        sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
        sitemap_content += '    <changefreq>daily</changefreq>\n'
        sitemap_content += '    <priority>1.0</priority>\n'
        sitemap_content += '  </url>\n'
        
        for main_cat, sub_cats in categories.items():
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{BASE_URL}category/{main_cat}/index.html</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>daily</changefreq>\n'
            sitemap_content += '    <priority>0.8</priority>\n'
            sitemap_content += '  </url>\n'
            for sub_cat in sub_cats:
                sitemap_content += '  <url>\n'
                sitemap_content += f'    <loc>{BASE_URL}category/{main_cat}/{sub_cat.replace(" ", "")}.html</loc>\n'
                sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
                sitemap_content += '    <changefreq>daily</changefreq>\n'
                sitemap_content += '    <priority>0.7</priority>\n'
                sitemap_content += '  </url>\n'
        
        for product in products:
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{BASE_URL}{product["page_url"]}</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>daily</changefreq>\n'
            sitemap_content += '    <priority>0.6</priority>\n'
            sitemap_content += '  </url>\n'
            
        static_pages = ["privacy.html", "disclaimer.html", "contact.html"]
        for page in static_pages:
            sitemap_content += '  <url>\n'
            sitemap_content += f'    <loc>{BASE_URL}{page}</loc>\n'
            sitemap_content += f'    <lastmod>{date.today().isoformat()}</lastmod>\n'
            sitemap_content += '    <changefreq>monthly</changefreq>\n'
            sitemap_content += '    <priority>0.5</priority>\n'
            sitemap_content += '  </url>\n'
        sitemap_content += '</urlset>'
        with open('sitemap.xml', 'w', encoding='utf-8') as f:
            f.write(sitemap_content)
        print("sitemap.xml が生成されました。")

    # メインの実行フロー
    _generate_index_pages(products)
    _generate_category_pages(products, categories)
    _generate_product_detail_pages(products)
    _generate_tag_pages(products)
    _generate_static_pages()
    _create_sitemap(products, categories)
    print("サイトのファイル生成が完了しました！")

if __name__ == "__main__":
    rakuten_products = fetch_rakuten_items()
    yahoo_products = fetch_yahoo_items()
    
    new_products = rakuten_products + yahoo_products
    
    products = update_products_json(new_products)
    generate_site(products)
