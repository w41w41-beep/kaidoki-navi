document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('.search-bar input');
    const searchButton = document.querySelector('.search-button');
    const productGrid = document.querySelector('.product-grid');

    if (!searchInput || !searchButton || !productGrid) {
        return;
    }

    const productCards = Array.from(productGrid.querySelectorAll('.product-card'));

    // 検索を実行する関数
    const filterProducts = () => {
        // キーワードを小文字に変換し、全角のカタカナ・英数字・スペースを半角に統一
        const query = searchInput.value.toLowerCase().trim()
            .replace(/[ァ-ヶ]/g, (match) => String.fromCharCode(match.charCodeAt(0) - 0x3000 + 0x20))
            .replace(/[Ａ-Ｚａ-ｚ０-９]/g, (match) => String.fromCharCode(match.charCodeAt(0) - 0xFEE0))
            .replace(/　/g, ' ');

        productCards.forEach(card => {
            // 商品名も同様に正規化
            const productName = card.querySelector('.product-name').textContent.toLowerCase()
                .replace(/[ァ-ヶ]/g, (match) => String.fromCharCode(match.charCodeAt(0) - 0x3000 + 0x20))
                .replace(/[Ａ-Ｚａ-ｚ０-９]/g, (match) => String.fromCharCode(match.charCodeAt(0) - 0xFEE0))
                .replace(/　/g, ' ');

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

    // リアルタイム検索
    searchInput.addEventListener('input', () => {
        filterProducts();
    });
});
