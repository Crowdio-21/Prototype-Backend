#!/usr/bin/env python3
"""
Quick database clear - no questions asked
"""

import sys
import os
import asyncio
import aiosqlite

# Add parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


async def quick_clear():
    """Quickly clear all database data"""
    print("🗑️ Quick database clear...")
    
    db_path = os.path.join(os.path.dirname(__file__),  'crowdcompute.db')
    async with aiosqlite.connect(db_path) as db:
        # Clear all tables
        await db.execute("DELETE FROM tasks")
        await db.execute("DELETE FROM jobs") 
        await db.execute("DELETE FROM workers")
        
        # Try to clear sqlite_sequence if it exists (for auto-increment tables)
        try:
            await db.execute("DELETE FROM sqlite_sequence")
        except:
            pass  # sqlite_sequence doesn't exist, which is fine
        
        await db.commit()
    
    print("✅ Database cleared!")


if __name__ == "__main__":
    asyncio.run(quick_clear())
