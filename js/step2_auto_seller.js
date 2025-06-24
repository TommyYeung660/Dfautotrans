// ==UserScript==
// @name         Dead Frontier Auto Trader - Step 2 (Auto Seller)
// @namespace    http://tampermonkey.net/
// @version      3.3000
// @description  Step 2: Automatically sell items when inventory is full
// @author       your_name
// @match        *://*.deadfrontier.com/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    console.log('DF Auto Trader Step 2: Auto Seller Starting...');

    // 配置
    const CONFIG = {
        targetItem: '12.7mm Rifle Bullets',
        sellPrice: 11.66,                   // 單價
        sellAllQuantity: true,               // 出售所有該類商品
        marketplaceUrl: 'https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=35',
        enableInventoryCheck: false,         // 測試期間不檢查使用率
        autoSell: true,                     // 啟用自動銷售
        removeDecimalFromTotal: true,       // 去除總價小數點
        
        // 反檢測配置
        humanBehavior: {
            enabled: true,                  // 啟用人性化行為模擬
            minDelay: 300,                 // 最小延遲 (ms) - 縮短
            maxDelay: 800,                 // 最大延遲 (ms) - 縮短
            typingSpeed: {
                min: 50,                   // 最小打字間隔 (ms) - 縮短
                max: 150                   // 最大打字間隔 (ms) - 縮短
            },
            mouseOffset: 0.3,              // 鼠標點擊偏移範圍 (0-1)
            useEnterKey: true,             // 優先使用Enter鍵確認
            itemDelay: {
                min: 3000,                 // 商品間最小間隔 (ms) - 縮短
                max: 6000                  // 商品間最大間隔 (ms) - 縮短
            },
            // 累積檢測對策 - 調整
            progressiveDelay: {
                enabled: false,            // 暫時禁用累積延遲
                multiplier: 1.2,           // 每次操作後延遲倍數 - 降低
                maxMultiplier: 2.0,        // 最大延遲倍數 - 降低
                resetAfter: 180000         // 3分鐘後重置倍數 (ms)
            },
            // 隨機暫停機制 - 調整
            randomPause: {
                enabled: false,            // 暫時禁用隨機暫停
                probability: 0.15,         // 15%機率暫停 - 降低
                minPause: 3000,            // 最小暫停時間 (ms) - 縮短
                maxPause: 8000             // 最大暫停時間 (ms) - 縮短
            },
            // 模擬用戶行為 - 調整
            simulateUserActivity: {
                enabled: true,             // 啟用用戶行為模擬
                mouseMovements: 2,         // 每次操作前的鼠標移動次數 - 減少
                scrollActions: false,      // 暫時禁用隨機滾動
                tabSwitching: false        // 模擬標籤切換（暫時關閉）
            },
            // 新增：成功後反偵查
            postSuccessAntiDetection: {
                enabled: true,             // 啟用成功後反偵查
                mouseMovements: 8,         // 成功後鼠標移動次數
                movementDuration: 15000,   // 移動持續時間 (ms)
                randomClicks: 3,           // 隨機點擊次數
                pageInteraction: true      // 頁面互動
            }
        }
    };

    // 反檢測初始化
    function initAntiDetection() {
        // 隱藏WebDriver標識
        if (navigator.webdriver) {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        }
        
        // 添加隨機鼠標移動
        let lastMouseMove = Date.now();
        setInterval(() => {
            if (Date.now() - lastMouseMove > 30000) { // 30秒沒有鼠標活動
                const randomX = Math.random() * window.innerWidth;
                const randomY = Math.random() * window.innerHeight;
                
                const mouseMoveEvent = new MouseEvent('mousemove', {
                    clientX: randomX,
                    clientY: randomY,
                    bubbles: true
                });
                document.dispatchEvent(mouseMoveEvent);
                lastMouseMove = Date.now();
            }
        }, 30000 + Math.random() * 10000); // 30-40秒間隔
        
        console.log('🛡️ 反檢測措施已啟動');
    }
    
    // 累積延遲追蹤
    let operationCount = 0;
    let lastOperationTime = 0;
    let currentDelayMultiplier = 1.0;

    // 啟動反檢測
    if (CONFIG.humanBehavior.enabled) {
        initAntiDetection();
    }

    // 全域銷售統計（使用localStorage持久化）
    function getSalesStats() {
        const stats = localStorage.getItem('df_auto_seller_stats');
        if (stats) {
            return JSON.parse(stats);
        }
        return {
            totalSuccess: 0,
            totalFailed: 0,
            totalQuantity: 0,
            totalValue: 0,
            lastSaleTime: 0
        };
    }

    function updateSalesStats(success, quantity = 0, value = 0) {
        const stats = getSalesStats();
        if (success) {
            stats.totalSuccess++;
            stats.totalQuantity += quantity;
            stats.totalValue += value;
        } else {
            stats.totalFailed++;
        }
        stats.lastSaleTime = Date.now();
        localStorage.setItem('df_auto_seller_stats', JSON.stringify(stats));
        return stats;
    }

    function printSalesStats() {
        const stats = getSalesStats();
        console.log(`\n📈 累計銷售統計:`);
        console.log(`   ✅ 成功: ${stats.totalSuccess}`);
        console.log(`   ❌ 失敗: ${stats.totalFailed}`);
        console.log(`   📦 總數量: ${stats.totalQuantity}`);
        console.log(`   💰 總收入: $${stats.totalValue}`);
        if (stats.lastSaleTime > 0) {
            const lastSale = new Date(stats.lastSaleTime);
            console.log(`   🕒 最後銷售: ${lastSale.toLocaleString()}`);
        }
    }

    // 工具函數
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // 人性化隨機延遲 - 模擬真實用戶行為
    function humanDelay(baseMs = 1000, variationMs = 500) {
        const randomDelay = baseMs + (Math.random() * variationMs * 2 - variationMs);
        return Math.max(500, Math.floor(randomDelay)); // 最少500ms
    }

    // 人性化隨機等待
    async function humanWait(baseMs = 1000, variationMs = 500) {
        let delay = humanDelay(baseMs, variationMs);
        
        // 應用累積延遲倍數
        if (CONFIG.humanBehavior.progressiveDelay.enabled) {
            delay = Math.floor(delay * currentDelayMultiplier);
        }
        
        await sleep(delay);
    }

    // 簡化的商品間等待
    async function enhancedItemWait() {
        const config = CONFIG.humanBehavior;
        
        // 更新操作計數
        operationCount++;
        
        // 計算基礎延遲
        let baseDelay = config.itemDelay.min + 
                       Math.random() * (config.itemDelay.max - config.itemDelay.min);
        
        await sleep(Math.floor(baseDelay));
        
        lastOperationTime = Date.now();
    }

    // 模擬用戶活動
    async function simulateUserActivity() {
        const config = CONFIG.humanBehavior.simulateUserActivity;
        if (!config.enabled) return;
        
        // 隨機鼠標移動
        for (let i = 0; i < config.mouseMovements; i++) {
            const randomX = Math.random() * window.innerWidth;
            const randomY = Math.random() * window.innerHeight;
            
            const mouseMoveEvent = new MouseEvent('mousemove', {
                bubbles: true,
                cancelable: true,
                clientX: randomX,
                clientY: randomY,
                view: window
            });
            document.dispatchEvent(mouseMoveEvent);
            
            await sleep(100 + Math.random() * 200);
        }
        
        // 隨機滾動
        if (config.scrollActions && Math.random() < 0.5) {
            const scrollDirection = Math.random() < 0.5 ? 1 : -1;
            const scrollAmount = (30 + Math.random() * 50) * scrollDirection;
            
            window.scrollBy(0, scrollAmount);
            await sleep(200 + Math.random() * 300);
        }
    }

    // 成功後反偵查活動
    async function postSuccessAntiDetection() {
        const config = CONFIG.humanBehavior.postSuccessAntiDetection;
        if (!config.enabled) return;
        
        console.log('\n🛡️ 開始成功後反偵查活動...');
        
        const startTime = Date.now();
        const endTime = startTime + config.movementDuration;
        let moveCount = 0;
        
        // 持續隨機鼠標移動
        while (Date.now() < endTime && moveCount < config.mouseMovements) {
            const randomX = Math.random() * window.innerWidth;
            const randomY = Math.random() * window.innerHeight;
            
            // 模擬更自然的鼠標移動軌跡
            const currentX = Math.random() * window.innerWidth;
            const currentY = Math.random() * window.innerHeight;
            
            // 分段移動，模擬真實軌跡
            const steps = 3 + Math.floor(Math.random() * 5);
            for (let step = 0; step <= steps; step++) {
                const progress = step / steps;
                const x = currentX + (randomX - currentX) * progress;
                const y = currentY + (randomY - currentY) * progress;
                
                const mouseMoveEvent = new MouseEvent('mousemove', {
                    bubbles: true,
                    cancelable: true,
                    clientX: x,
                    clientY: y,
                    view: window
                });
                document.dispatchEvent(mouseMoveEvent);
                
                await sleep(50 + Math.random() * 100);
            }
            
            moveCount++;
            
            // 隨機點擊空白區域
            if (moveCount % 3 === 0 && config.randomClicks > 0) {
                const clickEvent = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    clientX: randomX,
                    clientY: randomY,
                    view: window
                });
                
                // 確保點擊的是安全區域（不會觸發其他功能）
                const elementAtPoint = document.elementFromPoint(randomX, randomY);
                if (elementAtPoint && elementAtPoint.tagName === 'BODY') {
                    document.dispatchEvent(clickEvent);
                    console.log(`   🖱️ 隨機點擊空白區域: (${Math.floor(randomX)}, ${Math.floor(randomY)})`);
                }
            }
            
            // 頁面互動
            if (config.pageInteraction && Math.random() < 0.3) {
                // 隨機滾動
                const scrollX = (Math.random() - 0.5) * 100;
                const scrollY = (Math.random() - 0.5) * 200;
                window.scrollBy(scrollX, scrollY);
                
                await sleep(300 + Math.random() * 500);
            }
            
            // 隨機間隔
            await sleep(800 + Math.random() * 1500);
        }
        
        console.log(`✅ 反偵查活動完成，執行了 ${moveCount} 次鼠標移動，持續 ${Math.floor((Date.now() - startTime)/1000)} 秒`);
    }

    // 模擬真實鼠標移動軌跡
    function simulateMouseMovement(element) {
        const rect = element.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        
        // 使用配置的偏移範圍
        const offsetRange = CONFIG.humanBehavior.mouseOffset;
        const offsetX = (Math.random() - 0.5) * rect.width * offsetRange;
        const offsetY = (Math.random() - 0.5) * rect.height * offsetRange;
        
        const targetX = centerX + offsetX;
        const targetY = centerY + offsetY;
        
        // 模擬鼠標移動事件序列
        const mouseMoveEvent = new MouseEvent('mousemove', {
            bubbles: true,
            cancelable: true,
            clientX: targetX,
            clientY: targetY,
            view: window
        });
        
        const mouseOverEvent = new MouseEvent('mouseover', {
            bubbles: true,
            cancelable: true,
            clientX: targetX,
            clientY: targetY,
            view: window
        });
        
        element.dispatchEvent(mouseMoveEvent);
        element.dispatchEvent(mouseOverEvent);
        
        return { x: targetX, y: targetY };
    }

    // 模擬真實的鍵盤輸入
    async function simulateTyping(input, text) {
        input.focus();
        await humanWait(200, 100);
        
        // 完全清空輸入框
        input.select();
        await sleep(100);
        input.value = '';
        
        // 模擬Backspace清空
        const existingText = input.value;
        for (let i = existingText.length; i > 0; i--) {
            const backspaceEvent = new KeyboardEvent('keydown', {
                key: 'Backspace',
                keyCode: 8,
                which: 8,
                bubbles: true
            });
            input.dispatchEvent(backspaceEvent);
            input.value = input.value.slice(0, -1);
            input.dispatchEvent(new Event('input', { bubbles: true }));
            await sleep(50 + Math.random() * 50);
        }
        
        // 確保完全清空並觸發事件
        input.value = '';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        await humanWait(300, 200);
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            
            // 先觸發keydown
            const keyDownEvent = new KeyboardEvent('keydown', {
                key: char,
                keyCode: char.charCodeAt(0),
                which: char.charCodeAt(0),
                bubbles: true
            });
            input.dispatchEvent(keyDownEvent);
            
            // 更新值
            input.value += char;
            
            // 觸發input事件
            input.dispatchEvent(new Event('input', { bubbles: true }));
            
            // 觸發keyup
            const keyUpEvent = new KeyboardEvent('keyup', {
                key: char,
                keyCode: char.charCodeAt(0),
                which: char.charCodeAt(0),
                bubbles: true
            });
            input.dispatchEvent(keyUpEvent);
            
            // 使用配置的打字速度
            const typingDelay = CONFIG.humanBehavior.typingSpeed.min + 
                              Math.random() * (CONFIG.humanBehavior.typingSpeed.max - CONFIG.humanBehavior.typingSpeed.min);
            await sleep(typingDelay);
        }
        
        // 最後觸發change事件
        input.dispatchEvent(new Event('change', { bubbles: true }));
        input.dispatchEvent(new Event('blur', { bubbles: true }));
        await humanWait(300, 200);
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

    // 檢查是否在Dead Frontier網站
    function isOnDeadFrontierSite() {
        return window.location.hostname.includes('deadfrontier.com');
    }

    // 檢查是否在marketplace頁面
    function isOnMarketplacePage() {
        return window.location.href.includes('page=35');
    }

    // 導航到marketplace
    async function navigateToMarketplace() {
        if (!isOnMarketplacePage()) {
            window.location.href = CONFIG.marketplaceUrl;
            return true;
        }
        return false;
    }

    // 檢查是否在銷售標籤頁
    function isSellTabActive() {
        const sellTab = document.getElementById('loadSelling');
        return sellTab && sellTab.disabled;
    }

    // 切換到銷售標籤頁
    async function switchToSellTab() {
        if (!isSellTabActive()) {
            const sellTab = document.getElementById('loadSelling');
            if (sellTab) {
                sellTab.click();
                await sleep(2000);
                return true;
            } else {
                return false;
            }
        }
        return true;
    }

    // 檢查庫存中的目標商品
    function findInventoryItems() {
        try {
            // 只搜索inventory表格中的商品，排除selling window
            const inventoryTable = document.getElementById('inventory');
            if (!inventoryTable) {
                console.log('❌ 找不到inventory表格');
                return [];
            }
            
            console.log('🔍 正在搜索inventory表格中的商品...');
            console.log(`📋 Inventory表格HTML: ${inventoryTable.outerHTML.substring(0, 500)}...`);
            
            // 只在inventory表格中查找目標商品
            const inventoryItems = inventoryTable.querySelectorAll(`[data-type="${CONFIG.targetDataType}"]`);
            console.log(`🔍 找到 ${inventoryItems.length} 個data-type="${CONFIG.targetDataType}"的元素`);
            
            // 調試：列出所有找到的元素
            inventoryItems.forEach((item, index) => {
                console.log(`  商品 ${index + 1}: data-type="${item.getAttribute('data-type')}", data-itemtype="${item.getAttribute('data-itemtype')}", data-quantity="${item.getAttribute('data-quantity')}"`);
            });
            
            const targetItems = [];
            
            inventoryItems.forEach((item, index) => {
                // 檢查是否為12.7mm子彈
                const dataType = item.getAttribute('data-type') || '';
                const dataItemType = item.getAttribute('data-itemtype') || '';
                
                // 12.7mm子彈的特徵：data-type="127rifleammo" 且 data-itemtype="ammo"
                const is127mmAmmo = dataType === '127rifleammo' && dataItemType === 'ammo';
                
                console.log(`🔍 檢查商品 ${index + 1}: dataType="${dataType}", dataItemType="${dataItemType}", is127mmAmmo=${is127mmAmmo}`);
                
                if (is127mmAmmo) {
                    // 獲取數量信息
                    let quantity = 1; // 預設數量
                    
                    // 從data-quantity屬性獲取數量
                    const quantityFromData = item.getAttribute('data-quantity');
                    if (quantityFromData) {
                        quantity = parseInt(quantityFromData);
                    }
                    
                    // 構造商品名稱
                    const itemName = `12.7mm Rifle Bullets (${quantity} rounds)`;
                    
                    targetItems.push({
                        element: item,
                        name: itemName,
                        quantity: quantity,
                        index: index + 1,
                        dataType: dataType,
                        dataItemType: dataItemType
                    });
                    
                    console.log(`✅ 找到庫存商品: ${itemName}`);
                }
            });
            
            console.log(`🔍 在inventory中找到 ${targetItems.length} 個未上架的 ${CONFIG.targetItem}`);
            return targetItems;
            
        } catch (error) {
            console.error('搜索庫存商品失敗:', error);
            return [];
        }
    }

    // 計算銷售價格
    function calculateSellPrice(quantity) {
        let totalPrice = CONFIG.sellPrice * quantity;
        
        if (CONFIG.removeDecimalFromTotal) {
            totalPrice = Math.floor(totalPrice); // 去除小數點
        }
        
        return {
            unitPrice: CONFIG.sellPrice,
            totalPrice: totalPrice,
            quantity: quantity
        };
    }

    // 模擬右鍵點擊並選擇Sell
    async function triggerRightClickSell(sourceElement) {
        try {
            console.log('開始右鍵點擊流程...');
            
            // 1. 先嘗試點擊空白區域清除任何現有菜單
            const gameContent = document.getElementById('gamecontent');
            if (gameContent) {
                gameContent.click();
                await humanWait(200, 100);
            }
            
            // 2. 模擬鼠標移動到元素上
            const mousePos = simulateMouseMovement(sourceElement);
            await humanWait(500, 200);
            
            // 3. 觸發多種右鍵點擊事件
            console.log('觸發右鍵點擊事件...');
            
            // 嘗試mousedown + mouseup序列
            const mouseDownEvent = new MouseEvent('mousedown', {
                bubbles: true,
                cancelable: true,
                clientX: mousePos.x,
                clientY: mousePos.y,
                button: 2,
                buttons: 2,
                view: window
            });
            sourceElement.dispatchEvent(mouseDownEvent);
            await sleep(50);
            
            const mouseUpEvent = new MouseEvent('mouseup', {
                bubbles: true,
                cancelable: true,
                clientX: mousePos.x,
                clientY: mousePos.y,
                button: 2,
                buttons: 2,
                view: window
            });
            sourceElement.dispatchEvent(mouseUpEvent);
            await sleep(50);
            
            // 觸發contextmenu事件
            const rightClickEvent = new MouseEvent('contextmenu', {
                bubbles: true,
                cancelable: true,
                clientX: mousePos.x,
                clientY: mousePos.y,
                button: 2,
                buttons: 2,
                view: window
            });
            sourceElement.dispatchEvent(rightClickEvent);
            
            // 增加等待時間讓右鍵菜單完全載入
            await humanWait(2000, 500);
            
            // 嘗試多種選擇器來找到Sell按鈕
            console.log('尋找Sell按鈕...');
            const sellButtonSelectors = [
                'button:contains("Sell")',
                'button[style*="width: 100%"]',
                'div[style*="position: absolute"] button',
                'div[style*="background-color: black"] button'
            ];
            
            let sellButton = null;
            
            // 方法1: 查找包含"Sell"文本的按鈕
            const allButtons = document.querySelectorAll('button, input[type="button"], div[onclick], a');
            console.log(`找到 ${allButtons.length} 個可點擊元素`);
            
            for (const button of allButtons) {
                const text = button.textContent || button.value || '';
                if (text.trim().toLowerCase() === 'sell') {
                    sellButton = button;
                    console.log('找到Sell按鈕（文本匹配）');
                    break;
                }
            }
            
            // 方法2: 如果沒找到，嘗試查找可能的右鍵菜單
            if (!sellButton) {
                console.log('嘗試查找右鍵菜單...');
                const contextMenus = document.querySelectorAll('div[style*="position: absolute"], div[style*="position: fixed"]');
                console.log(`找到 ${contextMenus.length} 個絕對定位元素`);
                
                for (const menu of contextMenus) {
                    const menuButtons = menu.querySelectorAll('button, div[onclick], a, input[type="button"]');
                    for (const button of menuButtons) {
                        const text = button.textContent || button.value || '';
                        if (text.trim().toLowerCase().includes('sell')) {
                            sellButton = button;
                            console.log('在右鍵菜單中找到Sell按鈕');
                            break;
                        }
                    }
                    if (sellButton) break;
                }
            }
            
            // 方法3: 嘗試其他可能的選擇器
            if (!sellButton) {
                console.log('嘗試其他選擇器...');
                for (const selector of sellButtonSelectors) {
                    if (selector.includes(':contains')) continue;
                    sellButton = document.querySelector(selector);
                    if (sellButton && sellButton.textContent && sellButton.textContent.toLowerCase().includes('sell')) {
                        console.log(`找到Sell按鈕，使用選擇器: ${selector}`);
                        break;
                    }
                    sellButton = null;
                }
            }
            
            if (!sellButton) {
                console.log('❌ 找不到Sell按鈕');
                
                // 調試：列出所有可見的按鈕
                console.log('調試：列出所有可見按鈕:');
                allButtons.forEach((btn, index) => {
                    if (btn.offsetParent !== null && index < 10) { // 只顯示前10個可見按鈕
                        console.log(`  按鈕 ${index + 1}: "${btn.textContent?.trim()}" (${btn.tagName})`);
                    }
                });
                
                // 調試：檢查絕對定位元素的內容
                console.log('調試：檢查絕對定位元素:');
                const contextMenus = document.querySelectorAll('div[style*="position: absolute"], div[style*="position: fixed"]');
                contextMenus.forEach((menu, index) => {
                    if (menu.offsetParent !== null && index < 5) {
                        console.log(`  菜單 ${index + 1}: "${menu.textContent?.trim()}" (可見: ${menu.offsetParent !== null})`);
                        console.log(`    HTML: ${menu.innerHTML.substring(0, 200)}`);
                    }
                });
                
                return false;
            }
            
            // 3. 人性化點擊Sell按鈕
            console.log('點擊Sell按鈕...');
            simulateMouseMovement(sellButton);
            await humanWait(200, 100);
            
            sellButton.click();
            await humanWait(1000, 300);
            
            console.log('✅ 右鍵銷售操作完成');
            return true;
            
        } catch (error) {
            console.error('❌ 右鍵銷售操作失敗:', error);
            return false;
        }
    }

    // 檢查是否已有商品對話框顯示


    // 銷售單個商品
    async function sellItem(item) {
        try {
            const priceInfo = calculateSellPrice(item.quantity);
            
            console.log(`🏷️ 銷售: ${item.name} (數量:${priceInfo.quantity}, 總價:$${priceInfo.totalPrice})`);
            
            // 步驟0: 模擬用戶活動
            await simulateUserActivity();
            
            // 步驟1: 直接右鍵點擊庫存商品（不管是否有現有銷售）
            const rightClickSuccess = await triggerRightClickSell(item.element);
            if (!rightClickSuccess) {
                return false;
            }
            await humanWait(800, 300);
            
            // 步驟3: 等待價格輸入對話框出現
            
            // 嘗試多種選擇器來找到價格輸入欄
            let priceInput = null;
            const inputSelectors = [
                'input[data-type="price"]',
                '.moneyField',
                'input[type="number"]',
                '#gamecontent input',
                'input[max="9999999999"]',
                'input[min="0"]'
            ];
            
            for (const selector of inputSelectors) {
                priceInput = document.querySelector(selector);
                if (priceInput) {
                    break;
                }
            }
            
            if (!priceInput) {
                try {
                    priceInput = await waitForElement(inputSelectors.join(', '), 5000);
                } catch (error) {
                    return false;
                }
            }
            
            // 步驟4: 人性化輸入總價
            await simulateTyping(priceInput, priceInfo.totalPrice.toString());
            
            // 步驟5: 等待並檢查Yes按鈕狀態
            await humanWait(500, 200);
            
            // 多次嘗試啟用Yes按鈕
            let firstYesButton = null;
            let attempts = 0;
            const maxAttempts = 5;
            
            while (attempts < maxAttempts) {
                attempts++;
                firstYesButton = document.querySelector('#gamecontent button:not([disabled])');
                
                if (firstYesButton && firstYesButton.textContent.includes('Yes')) {
                    break;
                }
                
                // 重新觸發輸入事件來啟用按鈕
                priceInput.focus();
                await sleep(200);
                
                // 觸發多種事件
                priceInput.dispatchEvent(new Event('input', { bubbles: true }));
                priceInput.dispatchEvent(new Event('change', { bubbles: true }));
                priceInput.dispatchEvent(new Event('keyup', { bubbles: true }));
                
                // 如果仍然禁用，嘗試重新輸入最後一個字符
                if (attempts === 2) {
                    const currentValue = priceInput.value;
                    const lastChar = currentValue.slice(-1);
                    priceInput.value = currentValue.slice(0, -1);
                    priceInput.dispatchEvent(new Event('input', { bubbles: true }));
                    await sleep(100);
                    priceInput.value = currentValue;
                    priceInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
                
                await humanWait(400, 150);
            }
            
            if (!firstYesButton || !firstYesButton.textContent.includes('Yes')) {
                return false;
            }
            
            // 直接點擊Yes按鈕（移除Enter鍵使用）
            simulateMouseMovement(firstYesButton);
            await humanWait(150, 50);
            firstYesButton.click();
            await humanWait(800, 300);
            
            // 步驟6: 處理最終確認對話框
            await humanWait(500, 200);
            
            const confirmYesButton = document.querySelector('#gamecontent.warning button');
            if (!confirmYesButton || !confirmYesButton.textContent.includes('Yes')) {
                return false;
            }
            
            // 直接點擊最終確認按鈕（移除Enter鍵使用）
            simulateMouseMovement(confirmYesButton);
            await humanWait(150, 50);
            confirmYesButton.click();
            
            await humanWait(800, 300);
            
            console.log('   ✅ 銷售完成！');
            
            return true;
            
        } catch (error) {
            console.error(`   ❌ 銷售商品失敗:`, error);
            return false;
        }
    }

    // 自動銷售單個商品（重新訪問策略）
    async function autoSellSingleItem() {
        console.log(`\n🏷️ 開始單個商品銷售流程...`);
        
        // 1. 重新訪問marketplace確保乾淨狀態
        console.log('🔄 重新訪問marketplace...');
        window.location.href = CONFIG.marketplaceUrl;
        
        // 等待頁面重新載入
        return new Promise((resolve) => {
            // 頁面會重新載入，腳本會重新執行
            setTimeout(() => {
                resolve({ success: 0, failed: 0, needsReload: true });
            }, 1000);
        });
    }



    // 自動銷售所有目標商品（逐個重新訪問）
    async function autoSellItems(items) {
        if (!CONFIG.autoSell || items.length === 0) {
            return { success: 0, failed: 0 };
        }



        console.log(`\n🏷️ 找到 ${items.length} 個 ${CONFIG.targetItem}，開始逐個銷售...`);
        
        // 只銷售第一個商品，然後重新訪問
        if (items.length > 0) {
            const item = items[0];
            console.log(`\n[1/${items.length}] 銷售商品 #${item.index}`);
            
            const success = await sellItem(item);
            if (success) {
                const priceInfo = calculateSellPrice(item.quantity);
                
                // 更新統計
                updateSalesStats(true, item.quantity, priceInfo.totalPrice);
                
                console.log(`✅ 銷售成功！準備重新訪問marketplace...`);
                
                // 顯示累計統計
                printSalesStats();
                
                // 簡短等待後重新訪問
                await sleep(2000);
                
                // 重新訪問marketplace並添加標記
                const reloadUrl = CONFIG.marketplaceUrl + '&auto_sell=continue';
                window.location.href = reloadUrl;
                
                return { 
                    success: 1, 
                    failed: 0,
                    totalQuantity: item.quantity,
                    totalValue: priceInfo.totalPrice,
                    needsReload: true
                };
            } else {
                // 更新失敗統計
                updateSalesStats(false);
                
                console.log(`❌ 銷售失敗！`);
                printSalesStats();
                return { success: 0, failed: 1 };
            }
        }
        
        return { success: 0, failed: 0 };
    }

    // 打印庫存商品信息
    function printInventoryItems(items) {
        console.log('\n' + '='.repeat(60));
        console.log(`🎯 庫存中的 ${CONFIG.targetItem}`);
        console.log(`🏷️ 銷售單價: $${CONFIG.sellPrice}`);
        console.log(`🛒 自動銷售: ${CONFIG.autoSell ? '啟用' : '停用'}`);
        console.log('='.repeat(60));
        
        if (items.length === 0) {
            console.log('❌ 庫存中沒有找到目標商品');
        } else {
            console.log(`✅ 找到 ${items.length} 個目標商品:`);
            console.log('');
            
            let totalQuantity = 0;
            let totalValue = 0;
            
            items.forEach((item, index) => {
                const priceInfo = calculateSellPrice(item.quantity);
                console.log(`📦 商品 #${item.index}:`);
                console.log(`   📝 名稱: ${item.name}`);
                console.log(`   📊 數量: ${priceInfo.quantity}`);
                console.log(`   💲 單價: $${priceInfo.unitPrice}`);
                console.log(`   💰 總價: $${priceInfo.totalPrice}`);
                console.log('   ' + '-'.repeat(30));
                
                totalQuantity += priceInfo.quantity;
                totalValue += priceInfo.totalPrice;
            });
            
            console.log('');
            console.log('📈 總計統計:');
            console.log(`   🔢 總數量: ${totalQuantity}`);
            console.log(`   💰 總價值: $${totalValue}`);
            console.log(`   📊 平均單價: $${CONFIG.sellPrice}`);
        }
        
        console.log('='.repeat(60));
    }

    // 檢查是否為繼續銷售模式
    function isContinueSellMode() {
        return window.location.href.includes('auto_sell=continue');
    }

    // 主要執行函數
    async function executeStep2() {
        try {
            // 檢查是否在Dead Frontier網站
            if (!isOnDeadFrontierSite()) {
                console.log('⚠️ 不在Dead Frontier網站，腳本不執行');
                return;
            }

            const isContinueMode = isContinueSellMode();
            if (isContinueMode) {
                console.log('🔄 繼續銷售模式');
            } else {
                console.log('🚀 自動銷售啟動');
            }
            
            // 1. 檢查並導航到marketplace
            const needsRedirect = await navigateToMarketplace();
            if (needsRedirect) {
                return;
            }
            
            // 2. 等待頁面加載完成
            await sleep(isContinueMode ? 1500 : 2000);
            
            // 3. 切換到銷售標籤頁
            const switchSuccess = await switchToSellTab();
            if (!switchSuccess) {
                console.error('❌ 無法切換到銷售標籤');
                return;
            }
            
            // 4. 搜索庫存中的目標商品
            const inventoryItems = findInventoryItems();
            
            // 5. 打印庫存商品信息（繼續模式下簡化輸出）
            if (isContinueMode) {
                console.log(`🔍 找到 ${inventoryItems.length} 個商品`);
            } else {
                printInventoryItems(inventoryItems);
            }
            
            // 6. 顯示累計統計
            if (!isContinueMode) {
                printSalesStats();
            }
            
            // 7. 自動銷售（如果啟用）
            if (CONFIG.autoSell && inventoryItems.length > 0) {
                const sellResults = await autoSellItems(inventoryItems);
                if (!sellResults.needsReload) {
                    console.log(`\n🎉 自動銷售完成！成功: ${sellResults.success}, 失敗: ${sellResults.failed}, 總收入: $${sellResults.totalValue}`);
                }
            } else if (inventoryItems.length === 0) {
                console.log('🎉 沒有更多商品需要銷售，任務完成！');
                printSalesStats();
            }
            

            
        } catch (error) {
            console.error('❌ 第二步執行失敗:', error);
        }
    }

    // 調試頁面結構的輔助函數
    function debugPageStructure() {
        console.log('\n' + '='.repeat(60));
        console.log('🔍 頁面結構調試信息');
        console.log('='.repeat(60));
        
        // 檢查基本頁面信息
        console.log('📄 基本信息:');
        console.log(`   URL: ${window.location.href}`);
        console.log(`   標題: ${document.title}`);
        
        // 檢查marketplace標籤
        console.log('\n🏪 Marketplace標籤:');
        ['loadBuying', 'loadSelling', 'loadStorage'].forEach(id => {
            const tab = document.getElementById(id);
            console.log(`   ${id}: ${tab ? '存在' : '不存在'} ${tab?.disabled ? '(啟用)' : '(未啟用)'}`);
        });
        
        // 檢查庫存區域
        console.log('\n📦 庫存區域:');
        const invController = document.getElementById('invController');
        console.log(`   invController: ${invController ? '存在' : '不存在'}`);
        if (invController) {
            console.log(`   子元素數量: ${invController.children.length}`);
            console.log(`   HTML長度: ${invController.innerHTML.length}`);
        }
        
        // 檢查所有.item元素
        console.log('\n🎯 所有.item元素:');
        const allItems = document.querySelectorAll('.item');
        console.log(`   找到 ${allItems.length} 個.item元素`);
        
        allItems.forEach((item, index) => {
            if (index < 10) { // 只顯示前10個
                console.log(`   項目 ${index + 1}:`, {
                    title: item.title || '無title',
                    className: item.className,
                    text: (item.textContent || '').substring(0, 50) + '...'
                });
            }
        });
        
        // 搜索包含12.7mm的所有元素
        console.log('\n🎯 包含"12.7mm"的元素:');
        const allElements = document.querySelectorAll('*');
        let found127mm = 0;
        allElements.forEach(el => {
            const text = (el.textContent || '') + (el.title || '') + (el.getAttribute('data-title') || '');
            if (text.includes('12.7mm') && found127mm < 5) {
                found127mm++;
                console.log(`   元素 ${found127mm}:`, {
                    tagName: el.tagName,
                    className: el.className,
                    title: el.title,
                    text: text.substring(0, 100) + '...'
                });
            }
        });
        
        if (found127mm === 0) {
            console.log('   ❌ 沒有找到包含"12.7mm"的元素');
        }
        
        console.log('='.repeat(60));
    }

    // 添加手動觸發按鈕
    function addManualSellButton() {
        const buttonContainer = document.createElement('div');
        buttonContainer.style.cssText = `
            position: fixed;
            top: 60px;
            right: 10px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 5px;
        `;
        
        // 自動銷售按鈕
        const sellButton = document.createElement('button');
        sellButton.innerHTML = '🏷️ 自動銷售';
        sellButton.style.cssText = `
            padding: 10px;
            background: #ff9800;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        `;
        
        // 調試按鈕
        const debugButton = document.createElement('button');
        debugButton.innerHTML = '🔍 調試頁面';
        debugButton.style.cssText = `
            padding: 8px;
            background: #9c27b0;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            font-size: 12px;
        `;

        // 清除統計按鈕
        const clearStatsButton = document.createElement('button');
        clearStatsButton.innerHTML = '🗑️ 清除統計';
        clearStatsButton.style.cssText = `
            padding: 6px;
            background: #f44336;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            font-size: 11px;
        `;
        
        sellButton.onclick = async () => {
            sellButton.disabled = true;
            sellButton.innerHTML = '⏳ 銷售中...';
            
            try {
                // 切換到銷售標籤頁
                const switchSuccess = await switchToSellTab();
                if (!switchSuccess) {
                    console.error('❌ 切換到銷售標籤頁失敗');
                    return;
                }
                
                // 搜索並銷售商品
                const inventoryItems = findInventoryItems();
                printInventoryItems(inventoryItems);
                
                if (CONFIG.autoSell && inventoryItems.length > 0) {
                    const sellResults = await autoSellItems(inventoryItems);
                    console.log(`\n🎉 手動銷售完成！成功: ${sellResults.success}, 失敗: ${sellResults.failed}, 總收入: $${sellResults.totalValue}`);
                }
                
                sellButton.disabled = false;
                sellButton.innerHTML = '🏷️ 自動銷售';
            } catch (error) {
                console.error('手動銷售失敗:', error);
                sellButton.disabled = false;
                sellButton.innerHTML = '🏷️ 自動銷售';
            }
        };
        
        debugButton.onclick = () => {
            debugPageStructure();
        };

        clearStatsButton.onclick = () => {
            if (confirm('確定要清除所有銷售統計嗎？')) {
                localStorage.removeItem('df_auto_seller_stats');
                console.log('🗑️ 銷售統計已清除');
                printSalesStats();
            }
        };
        
        buttonContainer.appendChild(sellButton);
        buttonContainer.appendChild(debugButton);
        buttonContainer.appendChild(clearStatsButton);
        document.body.appendChild(buttonContainer);
    }

    // 啟動腳本
    setTimeout(async () => {
        try {
            await executeStep2();
        } catch (error) {
            console.error('腳本啟動失敗:', error);
        }
    }, 3000);

    // 頁面加載完成後添加手動觸發按鈕（只在marketplace頁面）
    if (isOnMarketplacePage()) {
        setTimeout(addManualSellButton, 4000);
    }

})(); 