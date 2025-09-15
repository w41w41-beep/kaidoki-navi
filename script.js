document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('.search-bar input');
    const searchButton = document.querySelector('.search-button');
    const productGrid = document.querySelector('.product-grid');

    if (!searchInput || !productGrid) {
        // トップページ以外では処理をスキップ
        return;
    }

    const productCards = Array.from(productGrid.querySelectorAll('.product-card'));

    // 検索関数を定義
    const filterProducts = () => {
        const query = searchInput.value.toLowerCase();
        productCards.forEach(card => {
            const productName = card.querySelector('.product-name').textContent.toLowerCase();
            if (productName.includes(query)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    };

    // 検索ボタンがクリックされた時の処理
    if (searchButton) {
        searchButton.addEventListener('click', filterProducts);
    }
    
    // 入力欄でEnterキーが押された時の処理
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault(); // フォームの送信を防ぐ
            filterProducts();
        }
    });

    // リアルタイム検索（入力するたびに実行）
    searchInput.addEventListener('input', filterProducts);
});
