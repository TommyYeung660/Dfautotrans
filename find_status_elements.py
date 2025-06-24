#!/usr/bin/env python3
"""
Simple script to find inventory and storage status elements
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.dfautotrans.config.settings import Settings
from src.dfautotrans.automation.browser_manager import BrowserManager
from src.dfautotrans.automation.login_handler import LoginHandler
from src.dfautotrans.core.page_navigator import PageNavigator
from src.dfautotrans.data.database import DatabaseManager

async def find_status_elements():
    """查找狀態元素"""
    settings = Settings()
    database_manager = DatabaseManager(settings)
    await database_manager.initialize()
    
    browser_manager = BrowserManager(settings)
    await browser_manager.initialize()
    
    page_navigator = PageNavigator(browser_manager, settings)
    await page_navigator.initialize()
    
    login_handler = LoginHandler(browser_manager, page_navigator, settings, database_manager)
    
    try:
        # 執行智能登錄
        logger.info("執行智能登錄...")
        login_success = await login_handler.smart_login()
        
        if not login_success:
            logger.error("登錄失敗")
            return
        
        # 導航到倉庫頁面
        logger.info("導航到倉庫頁面...")
        await page_navigator.navigate_to_url("https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=50")
        await asyncio.sleep(3)
        
        page = browser_manager.page
        
        # 方法1：直接查找文本模式
        logger.info("查找狀態文本模式...")
        status_elements = await page.evaluate("""
            () => {
                const results = [];
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let node;
                while (node = walker.nextNode()) {
                    const text = node.nodeValue.trim();
                    // 查找 (數字/數字) 模式
                    if (/\\(\\d+\/\\d+\\)/.test(text)) {
                        const parent = node.parentElement;
                        results.push({
                            text: text,
                            parentTagName: parent ? parent.tagName : 'unknown',
                            parentClassName: parent ? parent.className : '',
                            parentId: parent ? parent.id : '',
                            parentHTML: parent ? parent.outerHTML.substring(0, 200) + '...' : ''
                        });
                    }
                }
                return results;
            }
        """)
        
        logger.info(f"找到 {len(status_elements)} 個狀態文本元素:")
        for i, elem in enumerate(status_elements):
            logger.info(f"狀態元素 {i+1}:")
            logger.info(f"  文本: {elem['text']}")
            logger.info(f"  父元素標籤: {elem['parentTagName']}")
            logger.info(f"  父元素類名: {elem['parentClassName']}")
            logger.info(f"  父元素ID: {elem['parentId']}")
            logger.info(f"  父元素HTML: {elem['parentHTML']}")
            logger.info("-" * 40)
        
        # 方法2：查找特定的元素
        logger.info("\\n查找特定ID/Class元素...")
        
        # 查找可能包含狀態的元素
        specific_elements = await page.evaluate("""
            () => {
                const selectors = [
                    '#inventoryholder',
                    '#inventory',
                    '#storage',
                    '.opElem',
                    'input[type="number"]'
                ];
                
                const results = [];
                
                for (let selector of selectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        for (let elem of elements) {
                            const text = (elem.textContent || elem.value || '').trim();
                            if (text) {
                                results.push({
                                    selector: selector,
                                    tagName: elem.tagName,
                                    text: text.substring(0, 100),
                                    className: elem.className,
                                    id: elem.id,
                                    type: elem.type || '',
                                    placeholder: elem.placeholder || '',
                                    value: elem.value || ''
                                });
                            }
                        }
                    } catch (e) {
                        // 忽略無效選擇器
                    }
                }
                
                return results;
            }
        """)
        
        logger.info(f"找到 {len(specific_elements)} 個特定元素:")
        for i, elem in enumerate(specific_elements):
            logger.info(f"特定元素 {i+1}:")
            logger.info(f"  選擇器: {elem['selector']}")
            logger.info(f"  標籤: {elem['tagName']}")
            logger.info(f"  文本: {elem['text']}")
            logger.info(f"  類名: {elem['className']}")
            logger.info(f"  ID: {elem['id']}")
            logger.info(f"  類型: {elem['type']}")
            logger.info(f"  占位符: {elem['placeholder']}")
            logger.info(f"  值: {elem['value']}")
            logger.info("-" * 40)
        
        # 方法3：查找包含數字的輸入框或元素
        logger.info("\\n查找包含數字的元素...")
        numeric_elements = await page.evaluate("""
            () => {
                const results = [];
                
                // 查找所有包含數字的元素
                const allElements = document.querySelectorAll('*');
                
                for (let elem of allElements) {
                    const text = (elem.textContent || elem.value || '').trim();
                    
                    // 查找包含數字並且較短的文本
                    if (/\\d/.test(text) && text.length < 20) {
                        results.push({
                            tagName: elem.tagName,
                            text: text,
                            className: elem.className,
                            id: elem.id,
                            type: elem.type || '',
                            placeholder: elem.placeholder || '',
                            value: elem.value || '',
                            style: elem.getAttribute('style') || ''
                        });
                    }
                }
                
                return results.slice(0, 10); // 只返回前10個
            }
        """)
        
        logger.info(f"找到 {len(numeric_elements)} 個包含數字的元素:")
        for i, elem in enumerate(numeric_elements):
            logger.info(f"數字元素 {i+1}:")
            logger.info(f"  標籤: {elem['tagName']}")
            logger.info(f"  文本: {elem['text']}")
            logger.info(f"  類名: {elem['className']}")
            logger.info(f"  ID: {elem['id']}")
            logger.info(f"  類型: {elem['type']}")
            logger.info(f"  占位符: {elem['placeholder']}")
            logger.info(f"  值: {elem['value']}")
            logger.info(f"  樣式: {elem['style']}")
            logger.info("-" * 40)
        
    except Exception as e:
        logger.error(f"查找過程中出錯: {e}")
    finally:
        await browser_manager.cleanup()
        await database_manager.close()

if __name__ == "__main__":
    asyncio.run(find_status_elements()) 