document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------
    // 検索機能
    // ----------------------------------------
    const searchInput = document.querySelector('.search-bar input');
    const searchButton = document.querySelector('.search-button');
    const productGrid = document.querySelector('.product-grid');

    if (searchInput && searchButton && productGrid) {
        const productCards = Array.from(productGrid.querySelectorAll('.product-card'));

        const filterProducts = () => {
            const query = searchInput.value.toLowerCase().trim()
                .replace(/[ァ-ヶ]/g, (match) => String.fromCharCode(match.charCodeAt(0) - 0x3000 + 0x20))
                .replace(/[Ａ-Ｚａ-ｚ０-９]/g, (match) => String.fromCharCode(match.charCodeAt(0) - 0xFEE0))
                .replace(/　/g, ' ');

            productCards.forEach(card => {
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

        const performSearchAndHideKeyboard = () => {
            filterProducts();
            searchInput.blur();
        };

        searchButton.addEventListener('click', (e) => {
            e.preventDefault();
            performSearchAndHideKeyboard();
        });

        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                performSearchAndHideKeyboard();
            }
        });

        searchInput.addEventListener('input', () => {
            filterProducts();
        });
    }

    // ----------------------------------------
    // 個別ページ機能
    // ----------------------------------------

    // PC版の画像切り替え機能
    const mainImage = document.querySelector('.main-image img');
    const thumbnails = document.querySelectorAll('.thumbnail-image');

    if (mainImage && thumbnails.length > 0) {
        thumbnails.forEach(thumbnail => {
            thumbnail.addEventListener('click', () => {
                mainImage.src = thumbnail.src;
                thumbnails.forEach(t => t.classList.remove('active'));
                thumbnail.classList.add('active');
            });
        });
    }

    // スマホ版のSwiperスライダーの初期化
    if (window.innerWidth < 768) {
        const swiperCss = document.createElement('link');
        swiperCss.rel = 'stylesheet';
        swiperCss.href = 'https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css';
        document.head.appendChild(swiperCss);

        const swiperJs = document.createElement('script');
        swiperJs.src = 'https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js';
        swiperJs.onload = () => {
            const swiperElements = document.querySelectorAll('.swiper');
            swiperElements.forEach(el => {
                new Swiper(el, {
                    pagination: {
                        el: ".swiper-pagination",
                        clickable: true,
                    },
                });
            });
        };
        document.body.appendChild(swiperJs);
    }
});
