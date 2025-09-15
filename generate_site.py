# generate_site.py

def generate_index_html():
    """トップページを生成する関数"""
    html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>カイドキ-ナビ | お得な買い時を見つけよう！</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>

    <header>
        <div class="container">
            <h1><a href="index.html">カイドキ-ナビ</a></h1>
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
            <a href="#">パソコン</a>
            <span class="separator">|</span>
            <a href="#">家電</a>
        </div>
    </div>

    <main class="container">
        <div class="ai-recommendation-section">
            <h2 class="ai-section-title">AIおすすめ商品</h2>
            <div class="product-grid">
                <a href="item-1.html" class="product-card">
                    <img src="https://via.placeholder.com/300x200?text=Product+1" alt="商品1">
                    <div class="product-info">
                        <h3 class="product-name">商品名1（例：最新ノートPC）</h3>
                        <p class="product-price">¥89,800</p>
                        <p class="product-status">AI分析: 買い時です！</p>
                    </div>
                </a>
                <a href="item-1.html" class="product-card">
                    <img src="https://via.placeholder.com/300x200?text=Product+2" alt="商品2">
                    <div class="product-info">
                        <h3 class="product-name">商品名2（例：高性能ルーター）</h3>
                        <p class="product-price">¥5,500</p>
                        <p class="product-status">AI分析: 様子見</p>
                    </div>
                </a>
                <a href="item-1.html" class="product-card">
                    <img src="https://via.placeholder.com/300x200?text=Product+3" alt="商品3">
                    <div class="product-info">
                        <h3 class="product-name">商品名3（例：人気スマホ）</h3>
                        <p class="product-price">¥125,000</p>
                        <p class="product-status">AI分析: 買い時です！</p>
                    </div>
                </a>
            </div>
        </div>

        <h2 class="section-title">新着商品</h2>
        <div class="product-grid">
            <a href="item-1.html" class="product-card">
                <img src="https://via.placeholder.com/300x200?text=Product+A" alt="商品A">
                <div class="product-info">
                    <h3 class="product-name">商品A（例：最新ゲーム機）</h3>
                    <p class="product-price">¥55,000</p>
                    <p class="product-status">AI分析: 買い時です！</p>
                </div>
            </a>
            <a href="item-1.html" class="product-card">
                <img src="https://via.placeholder.com/300x200?text=Product+B" alt="商品B">
                <div class="product-info">
                    <h3 class="product-name">商品B（例：ロボット掃除機）</h3>
                    <p class="product-price">¥45,000</p>
                    <p class="product-status">AI分析: 買い時です！</p>
                </div>
            </a>
            <a href="item-1.html" class="product-card">
                <img src="https://via.placeholder.com/300x200?text=Product+C" alt="商品C">
                <div class="product-info">
                    <h3 class="product-name">商品C（例：ポータブルスピーカー）</h3>
                    <p class="product-price">¥9,800</p>
                    <p class="product-status">AI分析: 様子見</p>
                </div>
            </a>
        </div>

        <div class="pagination-container">
            <a href="#" class="pagination-link disabled">« 前へ</a>
            <a href="#" class="pagination-link active">1</a>
            <a href="#" class="pagination-link">2</a>
            <a href="#" class="pagination-link">3</a>
            <span class="pagination-ellipsis">...</span>
            <a href="#" class="pagination-link">10</a>
            <a href="#" class="pagination-link">次へ »</a>
        </div>
    </main>

    <footer>
        <p>&copy; 2025 カイドキ-ナビ. All Rights Reserved.</p>
        <div class="footer-links">
            <a href="privacy.html">プライバシーポリシー</a>
            <a href="disclaimer.html">免責事項</a>
            <a href="contact.html">お問い合わせ</a>
        </div>
    </footer>

</body>
</html>
    """
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("index.html が生成されました。")

def generate_item_html():
    """個別ページを生成する関数"""
    html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>【商品名】の買い時情報 | カイドキ-ナビ</title>
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
</head>
<body>

    <header>
        <div class="container">
            <h1><a href="index.html">カイドキ-ナビ</a></h1>
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
            <a href="#">パソコン</a>
            <span class="separator">|</span>
            <a href="#">家電</a>
        </div>
    </div>

    <main class="container">
        <div class="item-detail">
            <div class="item-image">
                <img src="https://via.placeholder.com/600x400?text=Product+Image" alt="商品画像">
            </div>

            <div class="item-info">
                <h1 class="item-name">商品名（例：SONY BRAVIA 4K有機ELテレビ）</h1>
                <p class="item-category">カテゴリ：家電 > テレビ</p>
                <div class="price-section">
                    <p class="current-price">現在の価格：<span>¥125,000</span></p>
                    <p class="price-status">AI分析：**買い時です！**</p>
                </div>

                <div class="affiliate-links">
                    <p class="links-title">最安値ショップをチェック！</p>
                    <a href="#" class="shop-link">Amazonで見る</a>
                    <a href="#" class="shop-link">楽天市場で見る</a>
                </div>

                <div class="item-description">
                    <h2>商品説明</h2>
                    <p>このテレビは、最新のAI技術を駆使した高画質プロセッサーを搭載し、あらゆる映像を驚くほど美しく表現します。また、有機ELならではの引き締まった黒と、豊富な色彩が特徴です。ゲームモードも搭載しており、遅延を気にすることなく快適にプレイできます。</p>
                </div>
            </div>
        </div>
    </main>

    <footer>
        <p>&copy; 2025 カイドキ-ナビ. All Rights Reserved.</p>
        <div class="footer-links">
            <a href="privacy.html">プライバシーポリシー</a>
            <a href="disclaimer.html">免責事項</a>
            <a href="contact.html">お問い合わせ</a>
        </div>
    </footer>
    
</body>
</html>
    """
    with open('item-1.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("item-1.html が生成されました。")

if __name__ == "__main__":
    generate_index_html()
    generate_item_html()
    print("サイトのファイル生成が完了しました！")
