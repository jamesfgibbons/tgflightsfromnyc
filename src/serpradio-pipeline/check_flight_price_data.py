#!/usr/bin/env python3
"""Check the structure of flight_price_data table"""
import os
from supabase import create_client
from src.config import settings

def check_table_columns():
    settings.assert_minimum()
    sb = create_client(settings.supabase_url, settings.supabase_key)
    
    try:
        # Get one row to see structure
        result = sb.table('flight_price_data').select("*").limit(1).execute()
        
        print("flight_price_data table structure:")
        print("=" * 50)
        
        if result.data and len(result.data) > 0:
            print("Columns found:")
            for key, value in result.data[0].items():
                print(f"  - {key}: {type(value).__name__} (example: {value})")
        else:
            # Try to insert a minimal row to see required fields
            try:
                sb.table('flight_price_data').insert({
                    "origin": "JFK",
                    "destination": "MBJ",
                    "price": 299.0
                }).execute()
            except Exception as e:
                print(f"Insert error reveals structure:\n{e}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_table_columns()