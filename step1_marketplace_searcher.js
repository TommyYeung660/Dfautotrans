// ==UserScript==
// @name         Dead Frontier Auto Trader - Step 1
// @namespace    http://tampermonkey.net/
// @version      1.0100
// @description  Step 1: Navigate to marketplace and search for specific items
// @author       your_name
// @match        *://*.deadfrontier.com/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    console.log('DF Auto Trader Step 1: Starting...');

    // 配置
    const CONFIG = {
        targetItem: '12.7mm Rifle Bullets',
        maxPricePerUnit: 11,
        marketplaceUrl: 'https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=35'
    };

    // 工具函數
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // 等待元素出現
    function waitForElement(selector, timeout = 10000) {
        return new Promise((resolve, reject) => {
            const element = document.querySelector(selector);
            if (element) {
                resolve(element);
                return;
            }
            
            const observer = new MutationObserver(() => {
                const element = document.querySelector(selector);
                if (element) {
                    observer.disconnect();
                    resolve(element);
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            setTimeout(() => {
                observer.disconnect();
                reject(new Error('元素未找到: ' + selector));
            }, timeout);
        });
    }

    // 檢查是否在marketplace頁面
    function isOnMarketplacePage() {
        return window.location.href.includes('page=35');
    }

    // 檢查是否在Dead Frontier域名
    function isOnDeadFrontierSite() {
        return window.location.hostname.includes('deadfrontier.com');
    }

    // 導航到marketplace
    async function navigateToMarketplace() {
        if (!isOnMarketplacePage()) {
            console.log('檢測到Dead Frontier網站，自動導航到marketplace...');
            window.location.href = CONFIG.marketplaceUrl;
            return true; // 表示需要跳轉
        }
        console.log('已在marketplace頁面');
        return false; // 表示不需要跳轉
    }

    // 檢查是否在購買標籤頁
    function isBuyTabActive() {
        const buyingTab = document.getElementById('loadBuying');
        return buyingTab && buyingTab.disabled;
    }

    // 切換到購買標籤頁
    async function switchToBuyTab() {
        if (!isBuyTabActive()) {
            const buyTab = document.getElementById('loadBuying');
            if (buyTab) {
                console.log('切換到購買標籤頁...');
                buyTab.click();
                await sleep(2000);
            }
        }
    }

    // 執行搜索
    async function searchItem(itemName) {
        try {
            console.log(`開始搜索商品: ${itemName}`);
            
            // 等待搜索欄出現
            const searchField = await waitForElement('#searchField', 5000);
            const searchButton = await waitForElement('#makeSearch', 5000);
            
            // 清空搜索欄並輸入商品名稱
            searchField.value = '';
            searchField.value = itemName;
            
            // 啟用搜索按鈕並點擊
            searchButton.disabled = false;
            searchButton.click();
            
            console.log('搜索請求已發送，等待結果...');
            await sleep(3000); // 等待搜索結果加載
            
        } catch (error) {
            console.error('搜索失敗:', error);
            throw error;
        }
    }

    // 分析搜索結果
    function analyzeSearchResults() {
        const itemDisplay = document.getElementById('itemDisplay');
        
        if (!itemDisplay || itemDisplay.childNodes.length <= 0) {
            console.log('沒有找到搜索結果');
            return { items: [], count: 0 };
        }

        const items = document.querySelectorAll('.fakeItem');
        const goodDeals = [];
        
        console.log(`找到 ${items.length} 個商品`);
        
        items.forEach((item, index) => {
            const price = parseFloat(item.dataset.price) || 0;
            const quantity = parseInt(item.dataset.quantity) || 1;
            const pricePerUnit = price / quantity;
            
            console.log(`商品 ${index + 1}: 價格=$${price}, 數量=${quantity}, 單價=$${pricePerUnit.toFixed(2)}`);
            
            if (pricePerUnit <= CONFIG.maxPricePerUnit) {
                goodDeals.push({
                    index: index + 1,
                    price: price,
                    quantity: quantity,
                    pricePerUnit: pricePerUnit.toFixed(2),
                    element: item
                });
            }
        });
        
        return { items: goodDeals, count: goodDeals.length };
    }

    // 打印結果到terminal
    function printResults(results) {
        console.log('\n' + '='.repeat(50));
        console.log(`🎯 搜索結果: ${CONFIG.targetItem}`);
        console.log(`💰 篩選條件: 單價 ≤ $${CONFIG.maxPricePerUnit}`);
        console.log('='.repeat(50));
        
        if (results.count === 0) {
            console.log('❌ 沒有找到符合條件的商品');
        } else {
            console.log(`✅ 找到 ${results.count} 個符合條件的商品:`);
            console.log('');
            
            results.items.forEach((item, index) => {
                console.log(`📦 商品 #${item.index}:`);
                console.log(`   💵 總價: $${item.price}`);
                console.log(`   📊 數量: ${item.quantity}`);
                console.log(`   💲 單價: $${item.pricePerUnit}`);
                console.log('   ' + '-'.repeat(30));
            });
            
            const totalQuantity = results.items.reduce((sum, item) => sum + item.quantity, 0);
            const totalValue = results.items.reduce((sum, item) => sum + item.price, 0);
            
            console.log('');
            console.log('📈 總計統計:');
            console.log(`   🔢 總數量: ${totalQuantity}`);
            console.log(`   💰 總價值: $${totalValue.toFixed(2)}`);
            console.log(`   📊 平均單價: $${(totalValue / totalQuantity).toFixed(2)}`);
        }
        
        console.log('='.repeat(50));
    }

    // 主要執行函數
    async function executeStep1() {
        try {
            // 檢查是否在Dead Frontier網站
            if (!isOnDeadFrontierSite()) {
                console.log('⚠️ 不在Dead Frontier網站，腳本不執行');
                return;
            }

            console.log('🚀 檢測到Dead Frontier網站，執行第一步：marketplace搜索');
            
            // 1. 檢查並導航到marketplace
            const needsRedirect = await navigateToMarketplace();
            if (needsRedirect) {
                return; // 頁面會重新加載，腳本會重新運行
            }
            
            // 2. 等待頁面加載完成
            await sleep(2000);
            
            // 3. 切換到購買標籤頁
            await switchToBuyTab();
            
            // 4. 執行搜索
            await searchItem(CONFIG.targetItem);
            
            // 5. 分析結果
            const results = analyzeSearchResults();
            
            // 6. 打印結果
            printResults(results);
            
            console.log('✅ 第一步執行完成！');
            
        } catch (error) {
            console.error('❌ 第一步執行失敗:', error);
        }
    }

    // 設置MutationObserver來監聽頁面變化
    function setupObserver() {
        const observer = new MutationObserver((mutations) => {
            // 檢查是否是搜索結果更新
            mutations.forEach((mutation) => {
                if (mutation.target.id === 'itemDisplay' && mutation.type === 'childList') {
                    if (mutation.target.childNodes.length > 0) {
                        setTimeout(() => {
                            const results = analyzeSearchResults();
                            printResults(results);
                        }, 1000);
                    }
                }
            });
        });

        const itemDisplay = document.getElementById('itemDisplay');
        if (itemDisplay) {
            observer.observe(itemDisplay, {
                childList: true,
                subtree: true
            });
        }
    }

    // 啟動腳本
    setTimeout(async () => {
        try {
            await executeStep1();
            // 只有在marketplace頁面才設置observer
            if (isOnMarketplacePage()) {
                setupObserver();
            }
        } catch (error) {
            console.error('腳本啟動失敗:', error);
        }
    }, 2000);

    // 添加手動觸發按鈕（可選）
    function addManualTriggerButton() {
        const button = document.createElement('button');
        button.innerHTML = '🔍 搜索低價商品';
        button.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 9999;
            padding: 10px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        `;
        
        button.onclick = async () => {
            button.disabled = true;
            button.innerHTML = '⏳ 搜索中...';
            
            try {
                await searchItem(CONFIG.targetItem);
                setTimeout(() => {
                    const results = analyzeSearchResults();
                    printResults(results);
                    button.disabled = false;
                    button.innerHTML = '🔍 搜索低價商品';
                }, 2000);
            } catch (error) {
                console.error('手動搜索失敗:', error);
                button.disabled = false;
                button.innerHTML = '🔍 搜索低價商品';
            }
        };
        
        document.body.appendChild(button);
    }

    // 頁面加載完成後添加手動觸發按鈕（只在marketplace頁面）
    if (isOnMarketplacePage()) {
        setTimeout(addManualTriggerButton, 3000);
    }

})(); 