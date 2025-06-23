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
        maxPricePerUnit: 11.6,
        maxRows: 10, // 只檢查前10行
        marketplaceUrl: 'https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=35',
        autoBuy: false, // 暫停自動購買
        checkInventory: true // 啟用庫存檢查
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

    // 檢查庫存狀態
    function checkInventoryStatus() {
        try {
            // 尋找庫存相關元素
            const inventoryItems = document.querySelectorAll('#invController .item, .inventoryItem, [class*="inventory"] .item');
            
            // 嘗試不同的選擇器來找到庫存容量信息
            let totalSlots = 0;
            let usedSlots = 0;
            let availableSlots = 0;
            
            // 方法1: 尋找明確的庫存信息
            const inventoryInfo = document.querySelector('#inventoryInfo, .inventoryInfo, [class*="inventory-info"]');
            if (inventoryInfo) {
                const infoText = inventoryInfo.textContent || inventoryInfo.innerText;
                console.log('庫存信息文本:', infoText);
                
                // 嘗試解析庫存信息 (例如: "25/40" 或 "25 / 40")
                const match = infoText.match(/(\d+)\s*\/\s*(\d+)/);
                if (match) {
                    usedSlots = parseInt(match[1]);
                    totalSlots = parseInt(match[2]);
                    availableSlots = totalSlots - usedSlots;
                }
            }
            
            // 方法2: 計算庫存項目數量
            if (totalSlots === 0 && inventoryItems.length > 0) {
                usedSlots = inventoryItems.length;
                // 嘗試找到總槽位數（通常在40-100之間）
                totalSlots = 40; // 預設值，可能需要調整
            }
            
            // 方法3: 檢查庫存控制器
            const invController = document.getElementById('invController');
            if (invController) {
                // 尋找可能包含庫存信息的文本
                const allText = invController.textContent || invController.innerText;
                const slotMatch = allText.match(/(\d+)\s*\/\s*(\d+)/);
                if (slotMatch && totalSlots === 0) {
                    usedSlots = parseInt(slotMatch[1]);
                    totalSlots = parseInt(slotMatch[2]);
                    availableSlots = totalSlots - usedSlots;
                }
            }
            
            // 如果還是找不到，使用項目計數
            if (totalSlots === 0) {
                usedSlots = inventoryItems.length;
                totalSlots = 40; // 預設總槽位
                availableSlots = totalSlots - usedSlots;
            } else {
                availableSlots = totalSlots - usedSlots;
            }
            
            const inventoryStatus = {
                totalSlots: totalSlots,
                usedSlots: usedSlots,
                availableSlots: availableSlots,
                usagePercentage: totalSlots > 0 ? ((usedSlots / totalSlots) * 100).toFixed(1) : 0,
                isFull: availableSlots <= 0,
                isNearFull: availableSlots <= 3
            };
            
            return inventoryStatus;
            
        } catch (error) {
            console.error('檢查庫存狀態失敗:', error);
            return {
                totalSlots: 0,
                usedSlots: 0,
                availableSlots: 0,
                usagePercentage: 0,
                isFull: false,
                isNearFull: false,
                error: true
            };
        }
    }

    // 打印庫存狀態
    function printInventoryStatus(inventoryStatus) {
        console.log('\n' + '='.repeat(50));
        console.log('📦 庫存狀態檢查');
        console.log('='.repeat(50));
        
        if (inventoryStatus.error) {
            console.log('❌ 無法獲取庫存信息');
            console.log('⚠️ 請確保：');
            console.log('   1. 已登錄遊戲');
            console.log('   2. 在正確的遊戲頁面');
            console.log('   3. 庫存界面可見');
        } else {
            console.log(`📊 總槽位: ${inventoryStatus.totalSlots}`);
            console.log(`📦 已使用: ${inventoryStatus.usedSlots}`);
            console.log(`🔓 可用槽位: ${inventoryStatus.availableSlots}`);
            console.log(`📈 使用率: ${inventoryStatus.usagePercentage}%`);
            
            if (inventoryStatus.isFull) {
                console.log('🚨 庫存已滿！無法購買新商品');
            } else if (inventoryStatus.isNearFull) {
                console.log('⚠️ 庫存接近滿載！請注意空間');
            } else {
                console.log('✅ 庫存空間充足');
            }
        }
        
        console.log('='.repeat(50));
        return inventoryStatus;
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
        
        // 只檢查前10行商品（由於價格是由低至高排列）
        const itemsToCheck = Math.min(items.length, CONFIG.maxRows);
        console.log(`檢查前 ${itemsToCheck} 個商品（價格由低至高排列）`);
        
        for (let index = 0; index < itemsToCheck; index++) {
            const item = items[index];
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
                    element: item,
                    actualPrice: price,
                    actualPricePerUnit: pricePerUnit
                });
            } else {
                // 由於價格是由低至高排列，如果當前商品超過價格，後面的都會超過，可以停止檢查
                console.log(`商品 ${index + 1} 單價 $${pricePerUnit.toFixed(2)} 超過限制 $${CONFIG.maxPricePerUnit}，停止檢查`);
                break;
            }
        }
        
        return { items: goodDeals, count: goodDeals.length };
    }

    // 購買商品
    async function buyItem(item) {
        try {
            console.log(`🛒 嘗試購買商品 #${item.index}: 總價=$${item.actualPrice}, 數量=${item.quantity}, 單價=$${item.actualPricePerUnit.toFixed(2)}`);
            
            // 點擊商品元素
            if (item.element && typeof item.element.click === 'function') {
                item.element.click();
                await sleep(1000);
                
                // 尋找並點擊購買按鈕
                const buyButton = document.querySelector('[data-action="buyItem"]');
                if (buyButton) {
                    buyButton.click();
                    console.log('   🔄 已點擊購買按鈕，等待確認對話框...');
                    await sleep(1500);
                    
                    // 處理確認對話框
                    await handleConfirmDialog();
                    
                    return true;
                } else {
                    console.log('   ❌ 找不到購買按鈕');
                    return false;
                }
            } else {
                console.log('   ❌ 商品元素無效');
                return false;
            }
        } catch (error) {
            console.error(`   ❌ 購買商品 #${item.index} 失敗:`, error);
            return false;
        }
    }

    // 處理確認對話框
    async function handleConfirmDialog() {
        try {
            // 尋找確認對話框中的"Yes"按鈕
            const yesButton = document.querySelector('#gamecontent button, #gamecontent input[value="Yes"]');
            if (yesButton && yesButton.innerHTML && yesButton.innerHTML.includes('Yes')) {
                yesButton.click();
                console.log('   ✅ 已確認購買');
                await sleep(2000); // 等待購買完成
                return true;
            } else {
                // 如果沒找到Yes按鈕，嘗試其他可能的選擇器
                const confirmButtons = document.querySelectorAll('button, input[type="button"]');
                for (let button of confirmButtons) {
                    if (button.textContent && button.textContent.includes('Yes')) {
                        button.click();
                        console.log('   ✅ 已確認購買');
                        await sleep(2000);
                        return true;
                    }
                }
                console.log('   ⚠️ 找不到確認按鈕');
                return false;
            }
        } catch (error) {
            console.error('   ❌ 處理確認對話框失敗:', error);
            return false;
        }
    }

    // 自動購買所有符合條件的商品
    async function autoBuyItems(results) {
        if (!CONFIG.autoBuy || results.count === 0) {
            return { success: 0, failed: 0 };
        }

        console.log(`\n🛒 開始自動購買 ${results.count} 個符合條件的商品...`);
        
        let successCount = 0;
        let failedCount = 0;
        
        for (let i = 0; i < results.items.length; i++) {
            const item = results.items[i];
            console.log(`\n[${i + 1}/${results.items.length}] 購買商品 #${item.index}`);
            
            const success = await buyItem(item);
            if (success) {
                successCount++;
                console.log(`   ✅ 購買成功！`);
            } else {
                failedCount++;
                console.log(`   ❌ 購買失敗！`);
            }
            
            // 購買之間的延遲
            await sleep(2000);
        }
        
        console.log(`\n📊 購買結果統計:`);
        console.log(`   ✅ 成功: ${successCount}`);
        console.log(`   ❌ 失敗: ${failedCount}`);
        
        return { success: successCount, failed: failedCount };
    }

    // 打印結果到terminal
    function printResults(results) {
        console.log('\n' + '='.repeat(60));
        console.log(`🎯 搜索結果: ${CONFIG.targetItem}`);
        console.log(`💰 篩選條件: 單價 ≤ $${CONFIG.maxPricePerUnit} (前${CONFIG.maxRows}行)`);
        console.log(`🛒 自動購買: ${CONFIG.autoBuy ? '啟用' : '停用'}`);
        console.log('='.repeat(60));
        
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
            const totalValue = results.items.reduce((sum, item) => sum + item.actualPrice, 0);
            
            console.log('');
            console.log('📈 總計統計:');
            console.log(`   🔢 總數量: ${totalQuantity}`);
            console.log(`   💰 總價值: $${totalValue.toFixed(2)}`);
            console.log(`   📊 平均單價: $${(totalValue / totalQuantity).toFixed(2)}`);
        }
        
        console.log('='.repeat(60));
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
            
            // 3. 檢查庫存狀態（如果啟用）
            let inventoryStatus = null;
            if (CONFIG.checkInventory) {
                inventoryStatus = checkInventoryStatus();
                printInventoryStatus(inventoryStatus);
            }
            
            // 4. 切換到購買標籤頁
            await switchToBuyTab();
            
            // 5. 執行搜索
            await searchItem(CONFIG.targetItem);
            
            // 6. 分析結果
            const results = analyzeSearchResults();
            
            // 7. 打印結果
            printResults(results);
            
            // 8. 自動購買（如果啟用且庫存有空間）
            if (CONFIG.autoBuy && results.count > 0) {
                if (inventoryStatus && inventoryStatus.isFull) {
                    console.log('\n🚨 庫存已滿，跳過自動購買！');
                } else if (inventoryStatus && inventoryStatus.isNearFull) {
                    console.log('\n⚠️ 庫存接近滿載，建議謹慎購買！');
                    const buyResults = await autoBuyItems(results);
                    console.log(`\n🎉 自動購買完成！成功: ${buyResults.success}, 失敗: ${buyResults.failed}`);
                } else {
                    const buyResults = await autoBuyItems(results);
                    console.log(`\n🎉 自動購買完成！成功: ${buyResults.success}, 失敗: ${buyResults.failed}`);
                }
            }
            
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
        button.innerHTML = CONFIG.checkInventory ? '📦 檢查庫存並搜索' : (CONFIG.autoBuy ? '🛒 搜索並購買' : '🔍 搜索低價商品');
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
            button.innerHTML = '⏳ 檢查中...';
            
            try {
                // 檢查庫存狀態
                let inventoryStatus = null;
                if (CONFIG.checkInventory) {
                    inventoryStatus = checkInventoryStatus();
                    printInventoryStatus(inventoryStatus);
                }
                
                button.innerHTML = '⏳ 搜索中...';
                await searchItem(CONFIG.targetItem);
                await sleep(2000);
                
                const results = analyzeSearchResults();
                printResults(results);
                
                // 自動購買（如果啟用且庫存有空間）
                if (CONFIG.autoBuy && results.count > 0) {
                    if (inventoryStatus && inventoryStatus.isFull) {
                        console.log('\n🚨 庫存已滿，跳過自動購買！');
                    } else {
                        button.innerHTML = '🛒 購買中...';
                        const buyResults = await autoBuyItems(results);
                        console.log(`\n🎉 手動購買完成！成功: ${buyResults.success}, 失敗: ${buyResults.failed}`);
                    }
                }
                
                button.disabled = false;
                button.innerHTML = CONFIG.checkInventory ? '📦 檢查庫存並搜索' : (CONFIG.autoBuy ? '🛒 搜索並購買' : '🔍 搜索低價商品');
            } catch (error) {
                console.error('手動操作失敗:', error);
                button.disabled = false;
                button.innerHTML = CONFIG.checkInventory ? '📦 檢查庫存並搜索' : (CONFIG.autoBuy ? '🛒 搜索並購買' : '🔍 搜索低價商品');
            }
        };
        
        document.body.appendChild(button);
    }

    // 頁面加載完成後添加手動觸發按鈕（只在marketplace頁面）
    if (isOnMarketplacePage()) {
        setTimeout(addManualTriggerButton, 3000);
    }

})(); 