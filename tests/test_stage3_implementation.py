"""Test Stage 3 Python implementation."""

import asyncio
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dfautotrans.config.settings import Settings
from dfautotrans.automation.browser_manager import BrowserManager
from dfautotrans.utils.logger import setup_logging, get_trading_logger

logger = get_trading_logger()


async def test_stage3_implementation():
    """Test our Stage 3 Python implementation based on MCP findings."""
    
    print("🚀 Dead Frontier Auto Trading System - Stage 3 Implementation Test")
    print("=" * 60)
    
    # Initialize settings
    settings = Settings()
    setup_logging(settings)
    
    logger.info("Starting Stage 3 implementation test")
    
    browser_manager = BrowserManager(settings)
    
    try:
        print("\n📱 Step 1: Starting browser with anti-detection...")
        await browser_manager.start()
        logger.info("Browser started successfully")
        
        print("\n🔐 Step 2: Logging into Dead Frontier...")
        login_success = await browser_manager.login()
        if login_success:
            print("✅ Login successful!")
            logger.info("Login successful")
        else:
            print("❌ Login failed!")
            logger.error("Login failed")
            return False
        
        print("\n🌐 Step 3: Navigating to Dead Frontier marketplace...")
        await browser_manager.navigate_to_marketplace()
        logger.info("Navigated to marketplace")
        
        print("\n🔍 Step 4: Testing search functionality...")
        search_term = "12.7mm Rifle Bullets"
        print(f"Searching for: {search_term}")
        
        search_result = await browser_manager.search_items(search_term)
        
        print(f"✅ Search completed! Found {search_result.total_found} items")
        logger.info(f"Search found {search_result.total_found} items for '{search_term}'")
        
        if search_result.items:
            print("\n📋 Top search results:")
            for i, item in enumerate(search_result.items[:5], 1):
                print(f"{i}. {item.item_name}")
                print(f"   📍 Seller: {item.seller}")
                print(f"   💰 Price: ${item.price} ({item.quantity} units)")
                print(f"   🌍 Zone: {item.trade_zone or 'Unknown'}")
                print(f"   🔗 Location: {item.buy_item_location}, Num: {item.buy_num}")
                print()
        
        print("\n👤 Step 5: Getting user profile information...")
        user_profile = await browser_manager.get_user_profile()
        if user_profile:
            print(f"✅ User Profile Retrieved:")
            print(f"   👤 Username: {user_profile.username}")
            print(f"   💵 Cash: ${user_profile.cash:,}")
            print(f"   📊 Level: {user_profile.level}")
            logger.info(f"User profile: {user_profile.username}, Cash: ${user_profile.cash}, Level: {user_profile.level}")
        else:
            print("⚠️ Could not retrieve user profile")
        
        print("\n🛒 Step 6: Testing selling tab functionality...")
        await browser_manager.switch_to_selling_tab()
        print("✅ Successfully switched to selling tab")
        
        print("\n🖼️ Step 7: Taking screenshot for verification...")
        screenshot_path = await browser_manager.take_screenshot("stage3_test_result.png")
        print(f"✅ Screenshot saved: {screenshot_path}")
        
        print("\n🧪 Step 8: Testing purchase simulation (dry run)...")
        if search_result.items:
            test_item = search_result.items[0]
            print(f"Testing purchase attempt for: {test_item.item_name}")
            
            # This would attempt a purchase in real scenario
            # For testing, we just validate the process
            if test_item.buy_item_location and test_item.buy_num:
                print(f"✅ Purchase data valid - Location: {test_item.buy_item_location}, Num: {test_item.buy_num}")
                logger.info(f"Purchase simulation successful for {test_item.item_name}")
            else:
                print("⚠️ Purchase data incomplete")
        
        print("\n✅ Stage 3 Implementation Test COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("🎯 Key Achievements:")
        print("   ✓ Browser automation with anti-detection")
        print("   ✓ Automatic login with credentials")
        print("   ✓ Marketplace navigation")
        print("   ✓ Search functionality")
        print("   ✓ Item data extraction")
        print("   ✓ User profile retrieval")
        print("   ✓ Tab switching")
        print("   ✓ Screenshot capability")
        print("   ✓ Purchase preparation")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during Stage 3 test: {e}")
        logger.error(f"Stage 3 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        print("\n🧹 Cleaning up browser resources...")
        await browser_manager.cleanup()
        logger.info("Browser cleanup completed")


async def main():
    """Main test runner."""
    success = await test_stage3_implementation()
    
    if success:
        print("\n🎉 Stage 3 Python Implementation: READY FOR STAGE 4!")
        print("Next: Integration testing and verification with MCP comparison")
    else:
        print("\n💥 Stage 3 Implementation needs fixes before proceeding")
    
    return success


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(main())
    sys.exit(0 if result else 1) 