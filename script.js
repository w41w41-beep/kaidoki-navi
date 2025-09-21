document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('.search-bar input');
    const searchButton = document.querySelector('.search-button');
    const productGrid = document.querySelector('.product-grid');

    if (!searchInput || !searchButton || !productGrid) {
        return;
    }

    const productCards = Array.from(productGrid.querySelectorAll('.product-card'));

    // 正規化用の関数
    const normalizeText = (text) => {
        return text.toLowerCase().trim()
            .replace(/[ァ-ヶ]/g, (match) => String.fromCharCode(match.charCodeAt(0) - 0x3000 + 0x20))
            .replace(/[Ａ-Ｚａ-ｚ０-９]/g, (match) => String.fromCharCode(match.charCodeAt(0) - 0xFEE0))
            .replace(/　/g, ' ');
    };

    // 検索を実行する関数
    const filterProducts = () => {
        const query = normalizeText(searchInput.value);

        productCards.forEach(card => {
            // 商品名を正規化
            const productName = normalizeText(card.querySelector('.product-name').textContent);

            // タグを正規化して1つの文字列に結合
            const tagElements = card.querySelectorAll('.tag');
            const tagText = Array.from(tagElements).map(tag => normalizeText(tag.textContent)).join(' ');

            // 商品名 or タグのいずれかに検索ワードが含まれていれば表示
            if (productName.includes(query) || tagText.includes(query)) {
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
