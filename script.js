/**
 * サイト内検索機能を実現するためのスクリプト
 */
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.querySelector('.search-container input[type="text"]');
    const searchButton = document.querySelector('.search-container .search-button');

    // 検索ボタンのクリックイベント
    if (searchButton) {
        searchButton.addEventListener('click', () => {
            performSearch();
        });
    }

    // Enterキーが押された時のイベント
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }

    // 検索実行関数
    function performSearch() {
        const query = searchInput.value.trim();
        if (query) {
            // 検索結果ページへリダイレクト
            window.location.href = `search_results.html?q=${encodeURIComponent(query)}`;
        }
    }

    // 検索結果ページでの処理
    if (window.location.pathname.endsWith('search_results.html')) {
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('q');
        const resultsContainer = document.getElementById('search-results-container');
        const loadingMessage = document.getElementById('loading-message');

        if (query && resultsContainer) {
            if (loadingMessage) loadingMessage.textContent = `「${query}」を検索中...`;
            fetchSearchIndex(query, resultsContainer, loadingMessage);
        } else if (resultsContainer) {
            resultsContainer.innerHTML = '<p class="col-span-full text-center text-gray-500 py-8 border border-dashed rounded-lg">検索キーワードを入力してください。</p>';
        }
    }
});

/**
 * 検索インデックスを読み込み、検索を実行する
 * @param {string} query - 検索キーワード
 * @param {HTMLElement} container - 結果を表示するDOM要素
 * @param {HTMLElement} loadingElement - ローディングメッセージを表示するDOM要素
 */
function fetchSearchIndex(query, container, loadingElement) {
    const rootPath = document.querySelector('link[rel="stylesheet"]').getAttribute('href').replace('style.css', '');
    const searchIndexUrl = `${rootPath}search_index.json`;
    const lowerQuery = query.toLowerCase();
    
    fetch(searchIndexUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error('Search index file not found.');
            }
            return response.json();
        })
        .then(products => {
            const filteredProducts = products.filter(product => {
                // searchable_textにクエリが含まれているかチェック
                return product.searchable_text.includes(lowerQuery);
            });

            renderSearchResults(filteredProducts, container, lowerQuery);
        })
        .catch(error => {
            console.error('Error loading search index:', error);
            if (loadingElement) loadingElement.textContent = '検索インデックスの読み込みに失敗しました。';
            container.innerHTML = `<p class="col-span-full text-center text-red-500 py-8 border border-dashed rounded-lg">検索処理中にエラーが発生しました。</p>`;
        });
}

/**
 * 検索結果をDOMにレンダリングする
 * @param {Array<Object>} results - 検索結果の商品配列
 * @param {HTMLElement} container - 結果を表示するDOM要素
 * @param {string} originalQuery - 元の検索クエリ
 */
function renderSearchResults(results, container, originalQuery) {
    container.innerHTML = '';
    const resultsTitle = document.querySelector('.ai-section-title');
    if (resultsTitle) {
        resultsTitle.textContent = `「${originalQuery}」の検索結果 (${results.length}件)`;
    }

    if (results.length === 0) {
        container.innerHTML = `
            <p class="col-span-full text-center text-gray-500 py-8 border border-dashed rounded-lg">
                「${originalQuery}」に一致する商品は見つかりませんでした。
            </p>
        `;
        return;
    }

    const productCardsHtml = results.map(product => {
        // 現在のページからの相対パスを計算
        const linkPath = product.page_url.startsWith('pages/') ? `../${product.page_url}` : product.page_url;

        return `
            <a href="${linkPath}" class="product-card">
                <img src="${product.image_url || ''}" alt="${product.name || '商品画像'}">
                <div class="product-info">
                    <h3 class="product-name">${product.name.length > 20 ? product.name.substring(0, 20) + '...' : product.name}</h3>
                    <p class="product-price">${parseInt(product.price).toLocaleString()}円</p>
                    <div class="price-status-title">💡注目ポイント</div>
                    <div class="price-status-content ai-analysis">${product.ai_headline || 'AI分析準備中'}</div>
                </div>
            </a>
        `;
    }).join('');

    container.innerHTML = productCardsHtml;
}
