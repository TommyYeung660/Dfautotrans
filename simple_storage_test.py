#!/usr/bin/env python3
"""
Simple storage test script
直接檢查storage頁面的按鈕狀態
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dfautotrans.automation.browser_manager import BrowserManager
from dfautotrans.automation.login_handler import LoginHandler
from dfautotrans.core.page_navigator import PageNavigator
from dfautotrans.config.settings import Settings
from dfautotrans.utils.logger import get_logger

logger = get_logger(__name__)

async def main():
    """簡單測試storage頁面按鈕"""
    browser_manager = None
    
    try:
        logger.info("=== 簡單Storage按鈕測試 ===")
        
        # 1. 初始化設定
        settings = Settings()
        
        # 2. 啟動瀏覽器
        browser_manager = BrowserManager(settings)
        await browser_manager.start()
        page = browser_manager.page
        
        # 3. 執行登錄
        page_navigator = PageNavigator(page, settings)
        login_handler = LoginHandler(browser_manager, page_navigator, settings)
        if not await login_handler.smart_login():
            logger.error("登錄失敗")
            return False
        
        # 4. 導航到storage頁面
        logger.info("導航到storage頁面...")
        await page.goto("https://fairview.deadfrontier.com/onlinezombiemmo/index.php?page=50")
        await asyncio.sleep(3)
        
        # 5. 檢查頁面元素
        logger.info("檢查storage頁面元素...")
        
        # 檢查兩個按鈕
        storagetoinv_button = await page.query_selector('#storagetoinv')
        invtostorage_button = await page.query_selector('#invtostorage')
        
        if storagetoinv_button:
            is_disabled = await storagetoinv_button.is_disabled()
            logger.info(f"#storagetoinv 按鈕: 存在，{'禁用' if is_disabled else '可用'}")
            
            if not is_disabled:
                logger.info("嘗試點擊 #storagetoinv 按鈕...")
                await storagetoinv_button.click()
                await asyncio.sleep(2)
                logger.info("點擊完成")
        else:
            logger.error("#storagetoinv 按鈕不存在")
        
        if invtostorage_button:
            is_disabled = await invtostorage_button.is_disabled()
            logger.info(f"#invtostorage 按鈕: 存在，{'禁用' if is_disabled else '可用'}")
        else:
            logger.error("#invtostorage 按鈕不存在")
        
        # 6. 檢查頁面上的任何按鈕
        all_buttons = await page.query_selector_all('button')
        logger.info(f"頁面上總共有 {len(all_buttons)} 個按鈕")
        
        for i, button in enumerate(all_buttons[:10]):  # 只檢查前10個
            try:
                text = await button.inner_text()
                is_disabled = await button.is_disabled()
                logger.info(f"按鈕 {i+1}: '{text}' {'(禁用)' if is_disabled else '(可用)'}")
            except Exception as e:
                logger.info(f"按鈕 {i+1}: 無法獲取文本 - {e}")
        
        # 7. 獲取頁面HTML進行分析
        html_content = await page.content()
        with open("storage_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("頁面HTML已保存到 storage_page.html")
        
        return True
        
    except Exception as e:
        logger.error(f"測試過程中發生錯誤: {e}")
        return False
        
    finally:
        if browser_manager:
            await browser_manager.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        logger.info("🎉 測試完成!")
        sys.exit(0)
    else:
        logger.error("❌ 測試失敗!")
        sys.exit(1) 