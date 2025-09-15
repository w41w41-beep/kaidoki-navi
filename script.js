document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('.search-bar input');
    const productGrid = document.querySelector('.product-grid');

    if (!searchInput || !productGrid) {
        // トップページ以外では処理をスキップ
        return;
    }

    const productCards = Array.from(productGrid.querySelectorAll('.product-card'));

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();

        productCards.forEach(card => {
            const productName = card.querySelector('.product-name').textContent.toLowerCase();
            if (productName.includes(query)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    });
});
