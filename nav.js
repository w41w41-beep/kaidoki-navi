
// ナビゲーションデータと要素を定義
const navDataElement = document.getElementById('nav-data');
const mainCategoryNav = document.getElementById('main-category-nav');
const subcategoryContainer = document.getElementById('subcategory-container');

let PRODUCT_CATEGORIES = {};

try {
    // HTMLに埋め込まれたJSONデータを解析
    if (navDataElement && navDataElement.textContent) {
        PRODUCT_CATEGORIES = JSON.parse(navDataElement.textContent);
    }
} catch (error) {
    console.error("Failed to parse navigation data:", error);
}

// 現在のページのベースパス（ルートディレクトリへの相対パス）を計算
function getBasePath() {
    // 例: pages/product.html -> ../
    // 例: index.html -> ./
    const currentPath = window.location.pathname;
    // ページ名を除去
    const pathSegments = currentPath.split('/').filter(segment => segment.length > 0);
    // 最後のセグメント（ファイル名）を除去
    pathSegments.pop(); 

    // 現在のディレクトリからルートへの相対パスを計算
    let depth = pathSegments.length;
    if (depth === 0) return './'; 
    return '../'.repeat(depth); 
}

// サブカテゴリーのリンク先のファイル名を安全にエンコードする
function safeEncodeFileName(name) {
    return name.replace(/ /g, '').replace(/\/g, '_').replace(/\/g, '_');
}

// 1. メインカテゴリーリンクの生成
function renderMainCategories(basePath) {
    mainCategoryNav.innerHTML = '';
    const categories = Object.keys(PRODUCT_CATEGORIES);

    // 常に「その他」カテゴリーを最後に追加
    if (categories.indexOf('その他') === -1) {
        categories.push('その他');
    }

    categories.forEach(category => {
        const categoryPath = `${basePath}category/${category}/index.html`;
        const link = document.createElement('a');
        link.href = categoryPath;
        link.textContent = category;
        link.classList.add('main-category-link');
        
        // ホバー/クリックイベントを追加
        link.addEventListener('mouseenter', () => renderSubCategories(category, basePath));
        link.addEventListener('click', (e) => {
            // モバイルでのクリック時にサブメニューを表示
            if (window.innerWidth < 768) {
                e.preventDefault();
                renderSubCategories(category, basePath);
            }
        });
        
        mainCategoryNav.appendChild(link);
        mainCategoryNav.appendChild(createSeparator());
    });
}

function createSeparator() {
    const span = document.createElement('span');
    span.classList.add('separator');
    span.textContent = '|';
    return span;
}

// 2. サブカテゴリーリンクの生成と表示
function renderSubCategories(mainCategory, basePath) {
    subcategoryContainer.innerHTML = '';
    
    // サブカテゴリーヘッダー
    const header = document.createElement('div');
    header.className = 'subcategory-header';
    header.innerHTML = `<a href="${basePath}category/${mainCategory}/index.html" class="main-cat-title">${mainCategory}</a> のカテゴリー`;
    subcategoryContainer.appendChild(header);

    const subcategoryLinks = document.createElement('div');
    subcategoryLinks.className = 'subcategory-links';

    let subCategories = [];
    if (mainCategory === 'その他') {
        // その他カテゴリーの場合は固定の「その他」サブカテゴリー
        subCategories = ['その他'];
    } else {
        // 定義済みカテゴリーの場合はリストを使用
        subCategories = PRODUCT_CATEGORIES[mainCategory] || [];
    }

    // 特別カテゴリーのリンクをサブカテゴリーに追加
    if (mainCategory === '特別') {
        subCategories = ['最安値', '期間限定セール'];
    }

    subCategories.forEach(subCategory => {
        const safeSubCatName = safeEncodeFileName(subCategory);
        let linkPath;

        if (subCategory === '最安値' || subCategory === '期間限定セール') {
             // 特別カテゴリーのパスは 'category/最安値/index.html' の形式
             linkPath = `${basePath}category/${subCategory}/index.html`;
        } else if (mainCategory === 'その他' && subCategory === 'その他') {
             // その他カテゴリーのその他サブカテゴリー
             linkPath = `${basePath}category/${mainCategory}/${safeSubCatName}.html`;
        } else {
            // 標準のサブカテゴリーパス
            linkPath = `${basePath}category/${mainCategory}/${safeSubCatName}.html`;
        }

        const link = document.createElement('a');
        link.href = linkPath;
        link.textContent = subCategory;
        link.classList.add('sub-category-link');
        subcategoryLinks.appendChild(link);
    });

    subcategoryContainer.appendChild(subcategoryLinks);

    // サブカテゴリーコンテナを表示
    subcategoryContainer.style.display = 'flex';
}

// 3. 初期化とイベント設定
document.addEventListener('DOMContentLoaded', () => {
    const basePath = getBasePath();

    // メインカテゴリーをレンダリング
    renderMainCategories(basePath);

    // サブカテゴリーコンテナからマウスが離れたら非表示
    subcategoryContainer.addEventListener('mouseleave', () => {
        // モバイルでは閉じないようにする
        if (window.innerWidth >= 768) {
            subcategoryContainer.style.display = 'none';
        }
    });

    // メインナビゲーションエリアからマウスが離れたらサブカテゴリーも非表示
    mainCategoryNav.addEventListener('mouseleave', (event) => {
        // マウスがサブカテゴリコンテナに入った場合は閉じない
        if (!subcategoryContainer.contains(event.relatedTarget) && window.innerWidth >= 768) {
             // 短い遅延を設けることで、メインカテゴリとサブカテゴリの間を移動する際にちらつきを防ぐ
             setTimeout(() => {
                if (!subcategoryContainer.matches(':hover')) {
                     subcategoryContainer.style.display = 'none';
                }
             }, 100);
        }
    });
});
