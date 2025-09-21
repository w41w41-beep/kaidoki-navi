document.addEventListener('DOMContentLoaded', () => {
    const productGrid = document.querySelector('.product-grid');
    const searchInput = document.querySelector('.search-bar input');
    const paginationContainer = document.querySelector('.pagination');
    let allProducts = [];
    const PRODUCTS_PER_PAGE = 12;

    // JSONファイルから商品データを取得する
    const fetchProducts = async () => {
        try {
            const response = await fetch('./products.json');
            if (!response.ok) {
                throw new Error('商品データを取得できませんでした。');
            }
            allProducts = await response.json();
            displayProducts(allProducts);
        } catch (error) {
            console.error('商品データの取得中にエラーが発生しました:', error);
            if (productGrid) {
                productGrid.innerHTML = '<p class="text-center text-red-500">商品データの読み込みに失敗しました。</p>';
            }
        }
    };

    // 商品をHTMLとして表示する
    const displayProducts = (productsToDisplay, page = 1) => {
        if (!productGrid) return;
        productGrid.innerHTML = '';
        const startIndex = (page - 1) * PRODUCTS_PER_PAGE;
        const endIndex = startIndex + PRODUCTS_PER_PAGE;
        const paginatedProducts = productsToDisplay.slice(startIndex, endIndex);

        if (paginatedProducts.length === 0) {
            productGrid.innerHTML = '<p class="text-center text-gray-500 col-span-full">該当する商品はありません。</p>';
            if (paginationContainer) {
                paginationContainer.innerHTML = '';
            }
            return;
        }

        paginatedProducts.forEach(product => {
            const productCard = `
                <a href="/${product.page_url}" class="block product-card bg-white rounded-xl shadow-lg p-6 flex flex-col items-center text-center">
                    <img src="${product.image}" alt="${product.name}" class="w-48 h-48 object-contain rounded-lg mb-4">
                    <h2 class="product-name text-xl font-semibold text-gray-800 mb-2 truncate w-full">${product.name}</h2>
                    <p class="text-3xl font-bold text-indigo-600 mb-2">${product.price}円</p>
                    <div class="text-sm text-gray-500">
                        <span class="font-bold text-green-600">${product.ai_headline}</span>
                    </div>
                </a>
            `;
            productGrid.innerHTML += productCard;
        });

        if (paginationContainer) {
            updatePagination(productsToDisplay.length, page, productsToDisplay);
        }
    };

    // ページネーションのUIを更新する
    const updatePagination = (totalProducts, currentPage, productsToDisplay) => {
        paginationContainer.innerHTML = '';
        const totalPages = Math.ceil(totalProducts / PRODUCTS_PER_PAGE);

        if (totalPages <= 1) return;

        for (let i = 1; i <= totalPages; i++) {
            const button = document.createElement('a');
            button.href = '#';
            button.textContent = i;
            button.className = `px-4 py-2 border rounded-lg ${i === currentPage ? 'bg-indigo-600 text-white' : 'bg-white text-indigo-600 hover:bg-gray-200'}`;
            button.addEventListener('click', (e) => {
                e.preventDefault();
                displayProducts(productsToDisplay, i);
            });
            paginationContainer.appendChild(button);
        }
    };

    // 検索機能を処理する（商品名と商品説明を検索対象に追加）
    const handleSearch = () => {
        const query = searchInput.value.toLowerCase().trim();
        const filteredProducts = allProducts.filter(product => {
            // 商品名と商品説明のテキストを結合して検索対象とする
            const searchTarget = `${product.name} ${product.description}`.toLowerCase();
            return searchTarget.includes(query);
        });
        displayProducts(filteredProducts);
    };

    // イベントリスナーの設定
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
    
    // ページロード時に商品を読み込む
    fetchProducts();
});
