#!/usr/bin/env python3
"""
調試市場掃描功能 - 檢查DOM結構
"""

import asyncio
import sys
from pathlib import Path

# 添加項目根目錄到Python路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from loguru import logger
from src.dfautotrans.config.settings import Settings
from src.dfautotrans.automation.browser_manager import BrowserManager
from src.dfautotrans.automation.login_handler import LoginHandler
from src.dfautotrans.core.page_navigator import PageNavigator
from src.dfautotrans.data.database import DatabaseManager


async def debug_market_scan():
    """調試市場掃描功能"""
    
    # 初始化組件
    settings = Settings()
    browser_manager = BrowserManager(settings)
    database_manager = DatabaseManager(settings)
    page_navigator = PageNavigator(browser_manager, settings)
    login_handler = LoginHandler(browser_manager, page_navigator, settings, database_manager)
    
    try:
        logger.info("🔍 開始調試市場掃描功能")
        
        # 初始化並登錄
        await browser_manager.initialize()
        await page_navigator.initialize()
        success = await login_handler.smart_login()
        
        if not success:
            logger.error("❌ 登錄失敗")
            return
        
        logger.info("✅ 登錄成功，導航到市場頁面")
        await page_navigator.navigate_to_marketplace()
        
        page = browser_manager.page
        
        # 1. 檢查購買標籤頁狀態
        logger.info("🔍 檢查購買標籤頁狀態...")
        buy_tab = await page.query_selector('#loadBuying')
        if buy_tab:
            is_disabled = await buy_tab.is_disabled()
            logger.info(f"購買標籤頁狀態: disabled={is_disabled} (disabled表示已激活)")
            
            if not is_disabled:
                logger.info("點擊購買標籤頁...")
                await buy_tab.click()
                await asyncio.sleep(3)  # 等待頁面加載
                
                # 重新檢查狀態
                is_disabled = await buy_tab.is_disabled()
                logger.info(f"點擊後購買標籤頁狀態: disabled={is_disabled}")
        else:
            logger.warning("找不到購買標籤頁 #loadBuying")
        
        # 2. 檢查itemDisplay容器
        logger.info("🔍 檢查itemDisplay容器...")
        item_display = await page.query_selector('#itemDisplay')
        if item_display:
            logger.info("✅ 找到 #itemDisplay 容器")
            
            # 檢查容器內容
            children = await item_display.query_selector_all('*')
            logger.info(f"itemDisplay 子元素數量: {len(children)}")
            
            # 檢查容器文本內容
            text_content = await item_display.inner_text()
            logger.info(f"itemDisplay 文本內容長度: {len(text_content)}")
            if len(text_content) > 0:
                logger.info(f"itemDisplay 文本內容預覽: {text_content[:200]}...")
        else:
            logger.warning("❌ 找不到 #itemDisplay 容器")
        
        # 3. 檢查.fakeItem元素
        logger.info("🔍 檢查.fakeItem元素...")
        fake_items = await page.query_selector_all('.fakeItem')
        logger.info(f"找到 {len(fake_items)} 個 .fakeItem 元素")
        
        if len(fake_items) > 0:
            # 檢查第一個fakeItem的結構
            first_item = fake_items[0]
            item_html = await first_item.inner_html()
            logger.info(f"第一個fakeItem的HTML結構:\n{item_html[:500]}...")
            
            # 檢查data屬性
            data_type = await first_item.get_attribute('data-type')
            data_price = await first_item.get_attribute('data-price')
            data_quantity = await first_item.get_attribute('data-quantity')
            logger.info(f"第一個fakeItem屬性: type={data_type}, price={data_price}, quantity={data_quantity}")
        
        # 4. 檢查搜索功能
        logger.info("🔍 測試搜索功能...")
        search_field = await page.query_selector('#searchField')
        search_button = await page.query_selector('#makeSearch')
        
        if search_field and search_button:
            logger.info("✅ 找到搜索輸入框和按鈕")
            
            # 測試搜索
            await search_field.fill("")
            await search_field.type("12.7")
            await asyncio.sleep(0.5)
            
            # 檢查搜索按鈕狀態
            is_disabled = await search_button.is_disabled()
            logger.info(f"搜索按鈕狀態: disabled={is_disabled}")
            
            if not is_disabled:
                logger.info("點擊搜索按鈕...")
                await search_button.click()
                await asyncio.sleep(3)
                
                # 重新檢查物品
                fake_items_after = await page.query_selector_all('.fakeItem')
                logger.info(f"搜索後找到 {len(fake_items_after)} 個 .fakeItem 元素")
            else:
                logger.warning("搜索按鈕被禁用")
        else:
            logger.warning(f"搜索元素狀態: field={search_field is not None}, button={search_button is not None}")
        
        # 5. 檢查頁面源碼中的關鍵詞
        logger.info("🔍 檢查頁面源碼...")
        page_content = await page.content()
        
        keywords = ['fakeItem', 'itemDisplay', 'loadBuying', 'searchField', 'makeSearch']
        for keyword in keywords:
            count = page_content.count(keyword)
            logger.info(f"頁面中 '{keyword}' 出現次數: {count}")
        
        # 6. 嘗試其他可能的物品選擇器
        logger.info("🔍 嘗試其他物品選擇器...")
        alternative_selectors = [
            'table tr',
            'tbody tr', 
            '[data-type]',
            '[data-price]',
            '.item',
            '.marketItem',
            'tr[class]',
            'div[class*="item"]'
        ]
        
        for selector in alternative_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if len(elements) > 0:
                    logger.info(f"選擇器 '{selector}' 找到 {len(elements)} 個元素")
                    
                    # 檢查第一個元素
                    if len(elements) > 0:
                        first_element = elements[0]
                        tag_name = await first_element.evaluate('el => el.tagName')
                        class_name = await first_element.get_attribute('class')
                        logger.info(f"  第一個元素: <{tag_name}> class='{class_name}'")
            except Exception as e:
                logger.debug(f"選擇器 '{selector}' 失敗: {e}")
        
        # 7. 保存頁面截圖和HTML用於調試
        await page.screenshot(path="debug_market_page.png")
        logger.info("📸 已保存頁面截圖: debug_market_page.png")
        
        html_content = await page.content()
        with open("debug_market_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("💾 已保存頁面HTML: debug_market_page.html")
        
        logger.info("🎯 調試完成！")
        
    except Exception as e:
        logger.error(f"❌ 調試過程中出現錯誤: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            await browser_manager.cleanup()
            logger.info("🧹 瀏覽器資源已清理")
        except Exception as e:
            logger.warning(f"清理瀏覽器資源時出錯: {e}")


async def main():
    """主函數"""
    try:
        await debug_market_scan()
        return 0
    except KeyboardInterrupt:
        logger.info("🛑 用戶中斷調試")
        return 0
    except Exception as e:
        logger.error(f"❌ 程序執行錯誤: {e}")
        return 1


if __name__ == "__main__":
    # 配置日誌
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    
    # 運行調試
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 