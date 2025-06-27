#!/usr/bin/env python3
"""
DOM結構調試腳本
檢查selling頁面的庫存DOM結構
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

async def debug_dom_structure():
    """調試DOM結構"""
    
    # 初始化組件
    settings = Settings()
    browser_manager = BrowserManager(settings)
    database_manager = DatabaseManager(settings)
    page_navigator = PageNavigator(browser_manager, settings)
    login_handler = LoginHandler(browser_manager, page_navigator, settings, database_manager)
    
    try:
        logger.info("🔧 初始化瀏覽器...")
        await browser_manager.initialize()
        await page_navigator.initialize()
        
        logger.info("🔐 執行登錄...")
        login_success = await login_handler.smart_login()
        
        if not login_success:
            logger.error("❌ 登錄失敗")
            return
        
        logger.info("🌐 導航到市場頁面...")
        if not await page_navigator.navigate_to_marketplace():
            logger.error("❌ 無法導航到市場頁面")
            return
        
        page = browser_manager.page
        
        # 切換到selling標籤
        logger.info("🔄 切換到selling標籤...")
        sell_tab = await page.query_selector("#loadSelling")
        if sell_tab:
            is_disabled = await sell_tab.is_disabled()
            if not is_disabled:
                await sell_tab.click()
                await asyncio.sleep(3)
            logger.info("✅ 成功切換到selling標籤")
        
        # 檢查inventory表格結構
        logger.info("🔍 檢查inventory表格結構...")
        
        inventory_table = await page.query_selector("#inventory")
        if inventory_table:
            logger.info("✅ 找到 #inventory 表格")
            
            # 檢查所有td元素
            all_tds = await inventory_table.query_selector_all("td")
            logger.info(f"📊 總共找到 {len(all_tds)} 個 td 元素")
            
            # 檢查.validSlot元素
            valid_slots = await inventory_table.query_selector_all("td.validSlot")
            logger.info(f"📊 找到 {len(valid_slots)} 個 .validSlot 元素")
            
            # 檢查.validSlot.locked元素
            locked_slots = await inventory_table.query_selector_all("td.validSlot.locked")
            logger.info(f"📊 找到 {len(locked_slots)} 個 .validSlot.locked 元素")
            
            # 檢查前幾個有物品的槽位 - 改為檢查所有.validSlot
            logger.info("🔍 檢查前10個槽位的詳細信息:")
            count = 0
            for i, slot in enumerate(valid_slots):
                if count >= 10:
                    break
                    
                try:
                    slot_attr = await slot.get_attribute("data-slot")
                    slot_class = await slot.get_attribute("class")
                    
                    # 查找物品div
                    item_div = await slot.query_selector("div.item")
                    if item_div:
                        data_type = await item_div.get_attribute("data-type")
                        data_quantity = await item_div.get_attribute("data-quantity")
                        data_itemtype = await item_div.get_attribute("data-itemtype")
                        
                        logger.info(f"   槽位 {i+1}: data-slot='{slot_attr}', class='{slot_class}'")
                        logger.info(f"            物品: data-type='{data_type}', quantity='{data_quantity}', itemtype='{data_itemtype}'")
                        count += 1
                    else:
                        # 即使沒有物品也顯示槽位信息
                        logger.info(f"   槽位 {i+1}: data-slot='{slot_attr}', class='{slot_class}' (空槽位)")
                        
                except Exception as e:
                    logger.debug(f"檢查槽位 {i+1} 時出錯: {e}")
                    
        else:
            logger.error("❌ 找不到 #inventory 表格")
            
            # 檢查是否有其他庫存相關元素
            logger.info("🔍 檢查其他可能的庫存元素...")
            
            # 檢查所有包含"inventory"的元素
            inventory_elements = await page.query_selector_all("[id*='inventory'], [class*='inventory']")
            logger.info(f"📊 找到 {len(inventory_elements)} 個包含'inventory'的元素")
            
            for i, elem in enumerate(inventory_elements[:5]):
                try:
                    tag_name = await elem.evaluate("element => element.tagName")
                    elem_id = await elem.get_attribute("id")
                    elem_class = await elem.get_attribute("class")
                    logger.info(f"   元素 {i+1}: <{tag_name}> id='{elem_id}' class='{elem_class}'")
                except:
                    pass
        
        logger.info("🎯 DOM結構檢查完成！")
        
    except Exception as e:
        logger.error(f"❌ 調試過程中出錯: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await browser_manager.cleanup()

async def main():
    """主函數"""
    await debug_dom_structure()

if __name__ == "__main__":
    asyncio.run(main()) 