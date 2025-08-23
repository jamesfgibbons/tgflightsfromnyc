"""
Caribbean ETL Pipeline - Process Google keyword CSV data for Kokomo theme
Transforms raw search data into sonification-ready visibility metrics
"""
import csv
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pathlib import Path

from ..storage import UnifiedStorage


class CaribbeanETL:
    """ETL pipeline for Caribbean keyword data and visibility metrics."""
    
    def __init__(self, storage_bucket: str = None):
        self.storage = UnifiedStorage(storage_bucket or os.getenv("STORAGE_BUCKET", "serpradio-artifacts"))
        
        # Caribbean destination mapping
        self.caribbean_destinations = {
            "SJU": {"name": "Puerto Rico", "region": "Caribbean", "search_volume": 5490},
            "AUA": {"name": "Aruba", "region": "Caribbean", "search_volume": 3610},
            "SDQ": {"name": "Dominican Republic", "region": "Caribbean", "search_volume": 3580},
            "MBJ": {"name": "Jamaica", "region": "Caribbean", "search_volume": 3560},
            "CUN": {"name": "Cancún", "region": "Caribbean", "search_volume": 3040},
            "CUR": {"name": "Curaçao", "region": "Caribbean", "search_volume": 860},
            "NAS": {"name": "Nassau", "region": "Caribbean", "search_volume": 1240}
        }
        
        # NYC origin airports
        self.nyc_origins = ["JFK", "LGA", "EWR"]
        
    def load_google_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """Load Google keyword CSV data."""
        data = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Clean and normalize data
                    cleaned_row = {}
                    for key, value in row.items():
                        cleaned_key = key.strip().lower().replace(' ', '_')
                        cleaned_row[cleaned_key] = value.strip() if isinstance(value, str) else value
                    data.append(cleaned_row)
                    
        except Exception as e:
            print(f"❌ Failed to load CSV {csv_path}: {e}")
            return []
            
        return data
        
    def extract_caribbean_keywords(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract Caribbean-related keywords from raw data."""
        caribbean_keywords = []
        
        caribbean_terms = [
            'caribbean', 'aruba', 'jamaica', 'puerto rico', 'dominican republic',
            'curacao', 'bahamas', 'nassau', 'cancun', 'montego bay', 'san juan',
            'santo domingo', 'punta cana', 'island', 'tropical', 'beach'
        ]
        
        nyc_terms = ['nyc', 'new york', 'jfk', 'laguardia', 'newark', 'lga', 'ewr']
        
        for row in raw_data:
            keyword = row.get('keyword', '').lower()
            
            # Check if keyword contains Caribbean and NYC terms
            has_caribbean = any(term in keyword for term in caribbean_terms)
            has_nyc = any(term in keyword for term in nyc_terms)
            
            if has_caribbean and has_nyc:
                # Extract destination code if possible
                destination_code = self._extract_destination_code(keyword)
                origin_code = self._extract_origin_code(keyword)
                
                processed_row = {
                    'keyword': row.get('keyword', ''),
                    'impressions': self._safe_int(row.get('impressions', 0)),
                    'clicks': self._safe_int(row.get('clicks', 0)),
                    'avg_position': self._safe_float(row.get('avg_position', 0)),
                    'ctr': self._safe_float(row.get('ctr', 0)),
                    'origin_code': origin_code,
                    'destination_code': destination_code,
                    'destination_name': self.caribbean_destinations.get(destination_code, {}).get('name', 'Unknown'),
                    'search_volume': self._estimate_search_volume(keyword, destination_code),
                    'avg_price_usd': self._estimate_price(destination_code),
                    'price_volatility': self._estimate_volatility(destination_code),
                    'theme': 'flights_from_nyc',
                    'sub_theme': 'caribbean_kokomo',
                    'sound_pack_hint': 'Tropical Pop',
                    'region': 'Caribbean'
                }
                
                caribbean_keywords.append(processed_row)
        
        return caribbean_keywords
    
    def _extract_destination_code(self, keyword: str) -> Optional[str]:
        """Extract destination airport code from keyword."""
        keyword_lower = keyword.lower()
        
        # Direct code matches
        for code in self.caribbean_destinations.keys():
            if code.lower() in keyword_lower:
                return code
                
        # Destination name matches
        destination_map = {
            'puerto rico': 'SJU',
            'san juan': 'SJU',
            'aruba': 'AUA',
            'jamaica': 'MBJ',
            'montego bay': 'MBJ',
            'dominican republic': 'SDQ',
            'santo domingo': 'SDQ',
            'punta cana': 'SDQ',
            'cancun': 'CUN',
            'curacao': 'CUR',
            'nassau': 'NAS',
            'bahamas': 'NAS'
        }
        
        for name, code in destination_map.items():
            if name in keyword_lower:
                return code
                
        return None
    
    def _extract_origin_code(self, keyword: str) -> str:
        """Extract origin airport code from keyword."""
        keyword_lower = keyword.lower()
        
        if 'jfk' in keyword_lower:
            return 'JFK'
        elif 'laguardia' in keyword_lower or 'lga' in keyword_lower:
            return 'LGA'
        elif 'newark' in keyword_lower or 'ewr' in keyword_lower:
            return 'EWR'
        elif 'nyc' in keyword_lower or 'new york' in keyword_lower:
            return 'JFK'  # Default to JFK for generic NYC
        else:
            return 'JFK'  # Default fallback
    
    def _safe_int(self, value: Any) -> int:
        """Safely convert value to integer."""
        try:
            if isinstance(value, str):
                # Remove commas and other formatting
                value = value.replace(',', '').replace('$', '')
            return int(float(value))
        except (ValueError, TypeError):
            return 0
    
    def _safe_float(self, value: Any) -> float:
        """Safely convert value to float."""
        try:
            if isinstance(value, str):
                value = value.replace(',', '').replace('$', '').replace('%', '')
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _estimate_search_volume(self, keyword: str, destination_code: Optional[str]) -> int:
        """Estimate search volume based on keyword and destination."""
        if destination_code and destination_code in self.caribbean_destinations:
            base_volume = self.caribbean_destinations[destination_code]["search_volume"]
            
            # Adjust based on keyword specificity
            if 'cheap' in keyword.lower():
                return int(base_volume * 0.7)
            elif 'luxury' in keyword.lower() or 'premium' in keyword.lower():
                return int(base_volume * 0.3)
            elif 'direct' in keyword.lower() or 'nonstop' in keyword.lower():
                return int(base_volume * 0.5)
            else:
                return base_volume
        
        # Default estimate for unknown destinations
        return 1500
    
    def _estimate_price(self, destination_code: Optional[str]) -> float:
        """Estimate average price for destination."""
        price_map = {
            'SJU': 289.50,  # Puerto Rico
            'AUA': 485.90,  # Aruba
            'SDQ': 325.80,  # Dominican Republic
            'MBJ': 415.60,  # Jamaica
            'CUN': 345.75,  # Cancún
            'CUR': 625.40,  # Curaçao
            'NAS': 285.90   # Nassau
        }
        
        return price_map.get(destination_code, 400.0)
    
    def _estimate_volatility(self, destination_code: Optional[str]) -> float:
        """Estimate price volatility for destination."""
        volatility_map = {
            'SJU': 0.15,  # Puerto Rico - stable
            'AUA': 0.22,  # Aruba - moderate
            'SDQ': 0.28,  # Dominican Republic - higher
            'MBJ': 0.20,  # Jamaica - moderate
            'CUN': 0.19,  # Cancún - moderate
            'CUR': 0.35,  # Curaçao - high (limited flights)
            'NAS': 0.21   # Nassau - moderate
        }
        
        return volatility_map.get(destination_code, 0.25)
    
    def transform_to_visibility_records(self, caribbean_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Caribbean keyword data to flight_visibility records."""
        records = []
        
        for item in caribbean_data:
            record = {
                'region': item['region'],
                'origin_code': item['origin_code'],
                'destination_code': item['destination_code'],
                'destination_name': item['destination_name'],
                'keyword': item['keyword'],
                'impressions': item['impressions'],
                'clicks': item['clicks'],
                'avg_position': item['avg_position'],
                'ctr': item['ctr'],
                'search_volume': item['search_volume'],
                'avg_price_usd': item['avg_price_usd'],
                'price_volatility': item['price_volatility'],
                'theme': item['theme'],
                'sub_theme': item['sub_theme'],
                'sound_pack_hint': item['sound_pack_hint'],
                'data_date': date.today().isoformat()
            }
            records.append(record)
        
        return records
    
    def generate_caribbean_summary(self, visibility_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for Caribbean data."""
        if not visibility_records:
            return {}
        
        # Aggregate by destination
        destination_stats = {}
        total_impressions = 0
        total_clicks = 0
        total_search_volume = 0
        
        for record in visibility_records:
            dest = record['destination_code']
            if dest not in destination_stats:
                destination_stats[dest] = {
                    'destination_name': record['destination_name'],
                    'impressions': 0,
                    'clicks': 0,
                    'search_volume': 0,
                    'avg_price': record['avg_price_usd'],
                    'volatility': record['price_volatility'],
                    'keyword_count': 0
                }
            
            destination_stats[dest]['impressions'] += record['impressions']
            destination_stats[dest]['clicks'] += record['clicks']
            destination_stats[dest]['search_volume'] += record['search_volume']
            destination_stats[dest]['keyword_count'] += 1
            
            total_impressions += record['impressions']
            total_clicks += record['clicks']
            total_search_volume += record['search_volume']
        
        # Calculate averages
        for dest_data in destination_stats.values():
            if dest_data['keyword_count'] > 0:
                dest_data['avg_impressions_per_keyword'] = dest_data['impressions'] / dest_data['keyword_count']
                dest_data['ctr'] = dest_data['clicks'] / max(dest_data['impressions'], 1)
        
        summary = {
            'theme': 'flights_from_nyc',
            'sub_theme': 'caribbean_kokomo',
            'sound_pack': 'Tropical Pop',
            'total_keywords': len(visibility_records),
            'total_impressions': total_impressions,
            'total_clicks': total_clicks,
            'total_search_volume': total_search_volume,
            'overall_ctr': total_clicks / max(total_impressions, 1),
            'destinations': destination_stats,
            'top_destinations_by_volume': sorted(
                [(k, v['search_volume']) for k, v in destination_stats.items()],
                key=lambda x: x[1], reverse=True
            )[:5],
            'generated_at': datetime.utcnow().isoformat(),
            'data_quality': 'high' if len(visibility_records) > 10 else 'medium'
        }
        
        return summary
    
    async def run_caribbean_etl(self, csv_path: str = None, output_prefix: str = "caribbean_kokomo") -> Dict[str, Any]:
        """Run complete Caribbean ETL pipeline."""
        print("🏝️ Starting Caribbean Kokomo ETL Pipeline")
        
        # Step 1: Load raw data
        if csv_path and os.path.exists(csv_path):
            print(f"📊 Loading CSV data from {csv_path}")
            raw_data = self.load_google_csv(csv_path)
        else:
            print("📊 Using generated sample data (no CSV provided)")
            raw_data = self._generate_sample_data()
        
        print(f"📈 Loaded {len(raw_data)} raw records")
        
        # Step 2: Extract Caribbean keywords
        caribbean_data = self.extract_caribbean_keywords(raw_data)
        print(f"🔍 Extracted {len(caribbean_data)} Caribbean keywords")
        
        # Step 3: Transform to visibility records
        visibility_records = self.transform_to_visibility_records(caribbean_data)
        print(f"🔄 Transformed {len(visibility_records)} visibility records")
        
        # Step 4: Generate summary
        summary = self.generate_caribbean_summary(visibility_records)
        print(f"📋 Generated summary for {len(summary.get('destinations', {}))} destinations")
        
        # Step 5: Store results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Store raw Caribbean data
        caribbean_path = f"etl/{output_prefix}/raw_caribbean_{timestamp}.json"
        await self.storage.upload_json(caribbean_data, caribbean_path)
        
        # Store visibility records
        visibility_path = f"etl/{output_prefix}/visibility_records_{timestamp}.json"
        await self.storage.upload_json(visibility_records, visibility_path)
        
        # Store summary
        summary_path = f"etl/{output_prefix}/summary_{timestamp}.json"
        await self.storage.upload_json(summary, summary_path)
        
        # Store latest summary (for easy access)
        latest_path = f"catalog/travel/flights_from_nyc/caribbean_kokomo/latest_summary.json"
        await self.storage.upload_json(summary, latest_path)
        
        result = {
            'etl_completed': True,
            'records_processed': len(raw_data),
            'caribbean_keywords_extracted': len(caribbean_data),
            'visibility_records_created': len(visibility_records),
            'destinations_covered': len(summary.get('destinations', {})),
            'total_search_volume': summary.get('total_search_volume', 0),
            'top_destinations': summary.get('top_destinations_by_volume', []),
            'files_created': {
                'caribbean_data': caribbean_path,
                'visibility_records': visibility_path,
                'summary': summary_path,
                'latest_summary': latest_path
            },
            'next_steps': [
                'Import visibility records to Supabase',
                'Run OpenAI cache builder',
                'Generate audio with Tropical Pop sound pack'
            ],
            'processed_at': datetime.utcnow().isoformat()
        }
        
        print(f"\n🎵 Caribbean ETL Complete!")
        print(f"🏝️ {result['destinations_covered']} destinations covered")
        print(f"📊 {result['total_search_volume']:,} total search volume")
        print(f"📁 Files stored in storage bucket")
        
        return result
    
    def _generate_sample_data(self) -> List[Dict[str, Any]]:
        """Generate sample Google keyword data for testing."""
        sample_data = [
            {'keyword': 'cheap flights nyc to puerto rico', 'impressions': '8540', 'clicks': '183', 'avg_position': '3.2', 'ctr': '0.0214'},
            {'keyword': 'jfk to aruba nonstop', 'impressions': '5120', 'clicks': '142', 'avg_position': '2.9', 'ctr': '0.0277'},
            {'keyword': 'laguardia to san juan flights', 'impressions': '4210', 'clicks': '95', 'avg_position': '4.1', 'ctr': '0.0226'},
            {'keyword': 'jfk to santo domingo flights', 'impressions': '4890', 'clicks': '125', 'avg_position': '3.4', 'ctr': '0.0256'},
            {'keyword': 'newark to jamaica flights', 'impressions': '2580', 'clicks': '62', 'avg_position': '4.3', 'ctr': '0.0240'},
            {'keyword': 'jfk to cancun direct flights', 'impressions': '5460', 'clicks': '156', 'avg_position': '2.7', 'ctr': '0.0286'},
            {'keyword': 'jfk to curacao flights', 'impressions': '1450', 'clicks': '38', 'avg_position': '4.6', 'ctr': '0.0262'},
            {'keyword': 'jfk to nassau bahamas', 'impressions': '2180', 'clicks': '58', 'avg_position': '3.5', 'ctr': '0.0266'},
            {'keyword': 'best caribbean islands from nyc', 'impressions': '6890', 'clicks': '189', 'avg_position': '2.8', 'ctr': '0.0274'},
            {'keyword': 'cheap caribbean flights winter', 'impressions': '5240', 'clicks': '142', 'avg_position': '3.2', 'ctr': '0.0271'}
        ]
        
        return sample_data


# CLI for running Caribbean ETL
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Caribbean Kokomo ETL Pipeline")
    parser.add_argument("--csv-path", help="Path to Google keyword CSV file")
    parser.add_argument("--output-prefix", default="caribbean_kokomo", help="Output file prefix")
    
    args = parser.parse_args()
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv("creds.env.txt")
    
    # Run ETL
    etl = CaribbeanETL()
    result = await etl.run_caribbean_etl(
        csv_path=args.csv_path,
        output_prefix=args.output_prefix
    )
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())