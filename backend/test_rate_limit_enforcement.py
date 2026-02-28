"""
Test script to verify 1000 API call limit is ABSOLUTELY enforced
Simulates reaching the limit and verifies no API calls are made
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from weather_service import (
    save_api_usage, 
    get_api_usage_stats, 
    increment_api_call,
    can_make_api_call,
    API_USAGE_FILE
)
from datetime import datetime


def test_rate_limit_enforcement():
    """Test that API calls are BLOCKED after 1000"""
    print("=" * 80)
    print("🧪 TESTING RATE LIMIT ENFORCEMENT (1000 calls/day)")
    print("=" * 80)
    
    # Backup existing usage file if it exists
    backup_file = None
    if API_USAGE_FILE.exists():
        backup_file = API_USAGE_FILE.with_suffix('.json.backup')
        import shutil
        shutil.copy(API_USAGE_FILE, backup_file)
        print(f"✅ Backed up existing usage file to: {backup_file}")
    
    try:
        # Test 1: Start fresh
        print("\n📊 Test 1: Starting with 0 calls")
        save_api_usage({
            'date': datetime.now().isoformat(),
            'calls': 0,
            'limit': 1000
        })
        stats = get_api_usage_stats()
        print(f"   Calls: {stats['calls_today']}/{stats['limit']}")
        print(f"   ✅ Can make calls: {can_make_api_call()}")
        assert stats['calls_today'] == 0
        assert can_make_api_call() == True
        
        # Test 2: Approach limit (998 calls)
        print("\n📊 Test 2: Setting to 998 calls (near limit)")
        save_api_usage({
            'date': datetime.now().isoformat(),
            'calls': 998,
            'limit': 1000
        })
        stats = get_api_usage_stats()
        print(f"   Calls: {stats['calls_today']}/{stats['limit']}")
        print(f"   ✅ Can still make calls: {can_make_api_call()}")
        assert stats['calls_today'] == 998
        assert can_make_api_call() == True
        
        # Test 3: Make 2 more calls (should reach 1000)
        print("\n📊 Test 3: Making 2 more calls (will reach 1000)")
        
        result1 = increment_api_call()
        print(f"   Call 999: {'✅ ALLOWED' if result1 else '🚫 BLOCKED'}")
        assert result1 == True  # Should be allowed
        
        result2 = increment_api_call()
        print(f"   Call 1000: {'✅ ALLOWED' if result2 else '🚫 BLOCKED'}")
        assert result2 == True  # Should be allowed (last one)
        
        stats = get_api_usage_stats()
        print(f"   Current: {stats['calls_today']}/{stats['limit']}")
        assert stats['calls_today'] == 1000
        
        # Test 4: CRITICAL - Try to make call 1001 (MUST BE BLOCKED)
        print("\n📊 Test 4: CRITICAL - Attempting call 1001 (MUST BE BLOCKED)")
        print("   🚨 This is the key test - verifying hard limit enforcement")
        
        result3 = increment_api_call()
        print(f"   Call 1001: {'❌ ALLOWED (BUG!)' if result3 else '✅ BLOCKED (CORRECT)'}")
        
        if result3:
            print("\n❌ CRITICAL FAILURE: API call was allowed after reaching 1000!")
            print("   🚨 This is a BUG - the limit is NOT being enforced!")
            return False
        else:
            print("\n✅ SUCCESS: API call was BLOCKED at limit")
        
        # Verify count didn't increase
        stats = get_api_usage_stats()
        print(f"   Verified count: {stats['calls_today']}/{stats['limit']}")
        assert stats['calls_today'] == 1000  # Should NOT have incremented
        
        # Test 5: Try multiple more calls (all should be blocked)
        print("\n📊 Test 5: Attempting multiple calls after limit")
        blocked_count = 0
        for i in range(5):
            result = increment_api_call()
            if not result:
                blocked_count += 1
            print(f"   Attempt {i+1}: {'❌ ALLOWED' if result else '✅ BLOCKED'}")
        
        print(f"\n   Blocked: {blocked_count}/5 attempts")
        assert blocked_count == 5  # ALL should be blocked
        
        # Test 6: Verify can_make_api_call() returns False
        print("\n📊 Test 6: Verify can_make_api_call() returns False")
        can_call = can_make_api_call()
        print(f"   can_make_api_call(): {can_call}")
        print(f"   {'❌ ERROR - returns True!' if can_call else '✅ Correctly returns False'}")
        assert can_call == False
        
        # Final verification
        stats = get_api_usage_stats()
        print("\n📊 Final Stats:")
        print(f"   Calls today: {stats['calls_today']}")
        print(f"   Limit: {stats['limit']}")
        print(f"   Remaining: {stats['remaining']}")
        print(f"   Usage: {stats['percentage_used']:.1f}%")
        
        assert stats['calls_today'] == 1000  # Should still be 1000
        assert stats['remaining'] == 0
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED - RATE LIMIT IS PROPERLY ENFORCED")
        print("=" * 80)
        print("\n🛡️ VERIFICATION SUMMARY:")
        print("   ✅ Calls 1-1000: Allowed")
        print("   ✅ Call 1001+: BLOCKED")
        print("   ✅ Counter doesn't exceed 1000")
        print("   ✅ can_make_api_call() returns False at limit")
        print("   ✅ increment_api_call() returns False at limit")
        print("\n🎉 Your API is FULLY PROTECTED from exceeding 1000 calls/day!")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Restore backup
        if backup_file and backup_file.exists():
            import shutil
            shutil.copy(backup_file, API_USAGE_FILE)
            backup_file.unlink()
            print(f"\n✅ Restored original usage file")
        else:
            # Clean up test file
            if API_USAGE_FILE.exists():
                API_USAGE_FILE.unlink()
                print(f"\n✅ Cleaned up test usage file")


if __name__ == "__main__":
    print("\n" + "🔬" * 40)
    print("RATE LIMIT ENFORCEMENT TEST")
    print("Verifying 1000 calls/day limit is ABSOLUTELY enforced")
    print("🔬" * 40 + "\n")
    
    success = test_rate_limit_enforcement()
    
    if success:
        print("\n✅ RATE LIMIT PROTECTION VERIFIED")
        print("   Your OpenWeatherMap API will NEVER exceed 1000 calls/day")
        sys.exit(0)
    else:
        print("\n❌ RATE LIMIT PROTECTION FAILED")
        print("   Please check the implementation")
        sys.exit(1)
