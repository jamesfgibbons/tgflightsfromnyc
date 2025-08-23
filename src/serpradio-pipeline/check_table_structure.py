#!/usr/bin/env python3
"""Check the structure of caribbean_offers table"""
import os
from supabase import create_client
from src.config import settings

def check_table_structure():
    settings.assert_minimum()
    sb = create_client(settings.supabase_url, settings.supabase_key)
    
    try:
        # Try to get one row to see the structure
        result = sb.table('caribbean_offers').select("*").limit(1).execute()
        
        print("caribbean_offers table structure:")
        print("=" * 50)
        
        if result.data and len(result.data) > 0:
            print("Columns found:")
            for key in result.data[0].keys():
                print(f"  - {key}")
        else:
            print("Table exists but is empty. Trying different approach...")
            # Try to insert a dummy row to trigger error message that shows columns
            try:
                sb.table('caribbean_offers').insert({}).execute()
            except Exception as e:
                print(f"Insert error reveals structure: {e}")
                
    except Exception as e:
        print(f"Error checking table: {e}")

if __name__ == "__main__":
    check_table_structure()