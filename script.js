document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('.search-bar input');
    const searchButton = document.querySelector('.search-button');
    const productGrid = document.querySelector('.product-grid');

    if (!searchInput || !searchButton || !productGrid) {
        return;
    }

    const productCards = Array.from(productGrid.querySelectorAll('.product-card'));

    const filterProducts = () => {
        const query = searchInput.value.toLowerCase().trim();
        productCards.forEach(card => {
            const productName = card.querySelector('.product-name').textContent.toLowerCase();
            if (productName.includes(query)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    };
    
    // 検索を実行し、キーボードを閉じる関数
    const performSearchAndHideKeyboard = () => {
        filterProducts();
        searchInput.blur(); // キーボードを閉じる
    };

    // 検索ボタンがクリックされた時の処理
    searchButton.addEventListener('click', (e) => {
        e.preventDefault();
        performSearchAndHideKeyboard();
    });

    // 入力欄でEnterキーが押された時の処理
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearchAndHideKeyboard();
        }
    });

    // リアルタイム検索（入力するたびに検索）の機能
    searchInput.addEventListener('input', () => {
        filterProducts();
    });
});
