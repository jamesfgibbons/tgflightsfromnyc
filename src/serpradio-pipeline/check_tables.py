#!/usr/bin/env python3
"""Check what tables exist in Supabase"""
import os
from supabase import create_client
from src.config import settings

def check_tables():
    settings.assert_minimum()
    sb = create_client(settings.supabase_url, settings.supabase_key)
    
    # Query information schema to get all tables
    try:
        response = sb.rpc('get_tables', {}).execute()
        print("Tables found via RPC:", response.data)
    except:
        # If RPC doesn't exist, try a different approach
        pass
    
    # Try to query known tables to see if they exist
    tables_to_check = [
        'caribbean_offers',
        'flight_offers', 
        'flight_price_data',
        'flight_visibility',
        'visibility_enrichment',
        'momentum_bands',
        'catalogs'
    ]
    
    print("Checking for tables in Supabase:\n")
    print("=" * 50)
    
    for table in tables_to_check:
        try:
            # Try to select from the table with limit 0
            result = sb.table(table).select("*").limit(0).execute()
            print(f"✅ {table:<25} EXISTS")
        except Exception as e:
            error_msg = str(e)
            if 'PGRST205' in error_msg or 'not found' in error_msg.lower():
                print(f"❌ {table:<25} NOT FOUND")
            else:
                print(f"⚠️  {table:<25} ERROR: {error_msg[:50]}...")
    
    print("=" * 50)

if __name__ == "__main__":
    check_tables()