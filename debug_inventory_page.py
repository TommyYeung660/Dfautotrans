#!/usr/bin/env python3
"""
Debug script to analyze inventory page structure
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

async def analyze_inventory_page():
    """分析庫存頁面結構"""
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
        
        # 分析頁面結構
        logger.info("分析頁面結構...")
        
        # 獲取所有可能的庫存/倉庫狀態元素
        page = browser_manager.page
        
        # 查找包含數字的元素
        elements_with_numbers = await page.evaluate("""
            () => {
                const elements = [];
                const allElements = document.querySelectorAll('*');
                
                for (let element of allElements) {
                    const text = element.textContent || element.innerText || '';
                    const trimmedText = text.trim();
                    
                    // 查找包含數字格式的元素，如 "1/1", "50/50", "0/1000" 等
                    if (/\\d+\\/\\d+/.test(trimmedText)) {
                        elements.push({
                            tagName: element.tagName,
                            className: element.className,
                            id: element.id,
                            text: trimmedText,
                            outerHTML: element.outerHTML.substring(0, 200) + '...'
                        });
                    }
                }
                
                return elements;
            }
        """)
        
        logger.info(f"找到 {len(elements_with_numbers)} 個包含數字格式的元素:")
        for i, elem in enumerate(elements_with_numbers):
            logger.info(f"元素 {i+1}:")
            logger.info(f"  標籤: {elem['tagName']}")
            logger.info(f"  類名: {elem['className']}")
            logger.info(f"  ID: {elem['id']}")
            logger.info(f"  文本: {elem['text']}")
            logger.info(f"  HTML: {elem['outerHTML']}")
            logger.info("-" * 40)
        
        # 查找可能的倉庫和庫存容器
        logger.info("\\n查找可能的倉庫和庫存容器...")
        
        storage_elements = await page.evaluate("""
            () => {
                const elements = [];
                const selectors = [
                    'div:has-text("Storage")',
                    'div:has-text("Inventory")',
                    'td:has-text("Storage")',
                    'td:has-text("Inventory")',
                    '[class*="storage"]',
                    '[class*="inventory"]',
                    '[id*="storage"]',
                    '[id*="inventory"]'
                ];
                
                for (let selector of selectors) {
                    try {
                        const found = document.querySelectorAll(selector);
                        for (let element of found) {
                            elements.push({
                                selector: selector,
                                tagName: element.tagName,
                                className: element.className,
                                id: element.id,
                                text: (element.textContent || '').trim().substring(0, 100),
                                outerHTML: element.outerHTML.substring(0, 300) + '...'
                            });
                        }
                    } catch (e) {
                        // 忽略無效的選擇器
                    }
                }
                
                return elements;
            }
        """)
        
        logger.info(f"找到 {len(storage_elements)} 個可能的倉庫/庫存元素:")
        for i, elem in enumerate(storage_elements):
            logger.info(f"元素 {i+1}:")
            logger.info(f"  選擇器: {elem['selector']}")
            logger.info(f"  標籤: {elem['tagName']}")
            logger.info(f"  類名: {elem['className']}")
            logger.info(f"  ID: {elem['id']}")
            logger.info(f"  文本: {elem['text']}")
            logger.info(f"  HTML: {elem['outerHTML']}")
            logger.info("-" * 40)
        
        # 獲取整個頁面的 HTML 並保存到文件
        logger.info("保存頁面 HTML 到文件...")
        html_content = await page.content()
        
        with open("debug_storage_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info("頁面 HTML 已保存到 debug_storage_page.html")
        
    except Exception as e:
        logger.error(f"分析過程中出錯: {e}")
    finally:
        await browser_manager.cleanup()
        await database_manager.close()

if __name__ == "__main__":
    asyncio.run(analyze_inventory_page()) 