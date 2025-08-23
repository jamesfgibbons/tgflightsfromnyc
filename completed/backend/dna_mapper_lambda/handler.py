import json
import os
import boto3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import snowflake.connector

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for DNA mapping from Snowflake data to audio parameters.
    """
    try:
        logger.info(f"DNA Mapper Lambda triggered")
        
        # Extract user_id from event
        user_id = extract_user_id(event)
        if not user_id:
            return create_error_response(400, "User ID is required")
        
        # For demo purposes, generate sample data if Snowflake not available
        try:
            snowflake_conn = get_snowflake_connection()
            ranking_data = fetch_ranking_data(snowflake_conn, user_id)
            if snowflake_conn:
                snowflake_conn.close()
        except Exception as e:
            logger.warning(f"Snowflake connection failed, using demo data: {str(e)}")
            ranking_data = generate_demo_data(user_id)
        
        if not ranking_data:
            ranking_data = generate_demo_data(user_id)
        
        # Process data and generate payload
        enhanced_data = process_ranking_data(ranking_data)
        audio_payload = generate_audio_payload(enhanced_data, user_id)
        payload_key = store_payload_s3(audio_payload, user_id)
        
        return create_success_response({
            "user_id": user_id,
            "payload_key": payload_key,
            "data_points": len(enhanced_data),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"DNA Mapper error: {str(e)}", exc_info=True)
        return create_error_response(500, f"Internal server error: {str(e)}")

def extract_user_id(event: Dict[str, Any]) -> Optional[str]:
    """Extract user ID from API Gateway event."""
    if 'requestContext' in event:
        query_params = event.get('queryStringParameters') or {}
        user_id = query_params.get('user_id')
        
        if not user_id and 'body' in event:
            try:
                body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
                user_id = body.get('user_id')
            except (json.JSONDecodeError, TypeError):
                pass
    else:
        user_id = event.get('user_id')
    
    return user_id or 'demo_user'

def get_snowflake_connection():
    """Establish connection to Snowflake."""
    try:
        conn = snowflake.connector.connect(
            user=os.environ.get('SNOWFLAKE_USERNAME'),
            password=os.environ.get('SNOWFLAKE_PASSWORD'),
            account=os.environ.get('SNOWFLAKE_ACCOUNT'),
            warehouse='COMPUTE_WH',
            database='SERP_RADIO',
            schema='MARKET_SHARE'
        )
        return conn
    except Exception as e:
        logger.error(f"Snowflake connection failed: {str(e)}")
        return None

def fetch_ranking_data(conn, user_id: str) -> List[Dict[str, Any]]:
    """Fetch ranking data from Snowflake."""
    if not conn:
        return []
    
    cursor = conn.cursor()
    query = """
    SELECT QUERY_ID, KEYWORD, DOMAIN, CURRENT_RANK, PREVIOUS_RANK, 
           RANK_DELTA, MARKET_SHARE_PCT, SEARCH_VOLUME, COMPETITION_SCORE,
           DATE_CAPTURED, LOOP_DNA, RANK_TIER
    FROM MARKET_SHARE_RANK 
    WHERE DATE_CAPTURED >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    ORDER BY DATE_CAPTURED DESC, ABS(RANK_DELTA) DESC
    LIMIT 50
    """
    
    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            record = dict(zip(columns, row))
            if record.get('LOOP_DNA'):
                try:
                    record['LOOP_DNA'] = json.loads(record['LOOP_DNA'])
                except:
                    record['LOOP_DNA'] = {}
            else:
                record['LOOP_DNA'] = {}
            result.append(record)
        
        return result
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        return []
    finally:
        cursor.close()

def generate_demo_data(user_id: str) -> List[Dict[str, Any]]:
    """Generate demo ranking data for testing."""
    demo_data = [
        {
            'QUERY_ID': f'{user_id}_001',
            'KEYWORD': 'sustainable fashion',
            'DOMAIN': 'example.com',
            'CURRENT_RANK': 3,
            'PREVIOUS_RANK': 8,
            'RANK_DELTA': -5,
            'MARKET_SHARE_PCT': 15.2,
            'SEARCH_VOLUME': 5000,
            'COMPETITION_SCORE': 0.8,
            'DATE_CAPTURED': datetime.now().isoformat(),
            'LOOP_DNA': {'tempo': 130, 'instrument': 'synth_lead'},
            'RANK_TIER': 'TOP_3'
        },
        {
            'QUERY_ID': f'{user_id}_002',
            'KEYWORD': 'eco friendly products',
            'DOMAIN': 'example.com',
            'CURRENT_RANK': 12,
            'PREVIOUS_RANK': 15,
            'RANK_DELTA': -3,
            'MARKET_SHARE_PCT': 8.7,
            'SEARCH_VOLUME': 3200,
            'COMPETITION_SCORE': 0.6,
            'DATE_CAPTURED': datetime.now().isoformat(),
            'LOOP_DNA': {'tempo': 120, 'instrument': 'electric_piano'},
            'RANK_TIER': 'TOP_50'
        }
    ]
    return demo_data

def process_ranking_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process and enhance ranking data."""
    for record in data:
        current_rank = record.get('CURRENT_RANK', 999)
        if current_rank <= 3:
            record['COMPUTED_TIER'] = 'TOP_3'
        elif current_rank <= 10:
            record['COMPUTED_TIER'] = 'TOP_10'
        elif current_rank <= 50:
            record['COMPUTED_TIER'] = 'TOP_50'
        else:
            record['COMPUTED_TIER'] = 'BEYOND_50'
        
        rank_delta = record.get('RANK_DELTA', 0)
        market_share = record.get('MARKET_SHARE_PCT', 0)
        
        enhanced_dna = {
            **record.get('LOOP_DNA', {}),
            'urgency_factor': min(1.0, abs(rank_delta) / 20.0),
            'market_dominance': market_share / 100.0,
            'emotional_intensity': abs(rank_delta) / 30.0,
            'narrative_weight': 1.0 if abs(rank_delta) >= 10 else 0.5
        }
        
        record['ENHANCED_DNA'] = enhanced_dna
    
    return data

def generate_audio_payload(data: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
    """Generate audio payload for renderer."""
    payload = {
        'user_id': user_id,
        'timestamp': datetime.now().isoformat(),
        'composition_layers': {
            'lead_melody': process_layer([r for r in data if abs(r.get('RANK_DELTA', 0)) >= 10], 'lead'),
            'harmony': process_layer([r for r in data if r.get('MARKET_SHARE_PCT', 0) > 25], 'harmony'),
            'rhythm': process_layer([r for r in data if abs(r.get('RANK_DELTA', 0)) < 5], 'rhythm'),
            'bass': process_layer(data[-5:], 'bass')
        },
        'global_parameters': {
            'overall_tempo': calculate_global_tempo(data),
            'key_signature': 'C_major',
            'time_signature': '4/4',
            'total_duration': 60,
            'fade_in': 2,
            'fade_out': 3
        },
        'narrative_events': generate_narrative_events(data)
    }
    return payload

def process_layer(records: List[Dict[str, Any]], layer_type: str) -> Dict[str, Any]:
    """Process records for composition layer."""
    if not records:
        return {'active': False}
    
    layer_config = {
        'lead': {'instrument': 'synth_lead', 'volume': 0.8},
        'harmony': {'instrument': 'electric_piano', 'volume': 0.6},
        'rhythm': {'instrument': 'acoustic_guitar', 'volume': 0.7},
        'bass': {'instrument': 'bass_synth', 'volume': 0.9}
    }.get(layer_type, {'instrument': 'synth_pad', 'volume': 0.5})
    
    return {
        'active': True,
        'tempo': sum(r.get('ENHANCED_DNA', {}).get('tempo', 120) for r in records) / len(records),
        'intensity': sum(r.get('ENHANCED_DNA', {}).get('emotional_intensity', 0.5) for r in records) / len(records),
        **layer_config,
        'records': records[:8]
    }

def calculate_global_tempo(data: List[Dict[str, Any]]) -> float:
    """Calculate global tempo based on activity."""
    if not data:
        return 120.0
    
    avg_delta = sum(abs(r.get('RANK_DELTA', 0)) for r in data) / len(data)
    return 120 + min(60, avg_delta * 2)

def generate_narrative_events(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate TTS narrative events."""
    events = []
    significant_changes = sorted([r for r in data if abs(r.get('RANK_DELTA', 0)) >= 10], 
                                key=lambda x: abs(x.get('RANK_DELTA', 0)), reverse=True)
    
    for i, record in enumerate(significant_changes[:3]):
        events.append({
            'timestamp': i * 20 + 10,
            'type': 'ranking_change',
            'keyword': record.get('KEYWORD', ''),
            'rank_delta': record.get('RANK_DELTA', 0),
            'current_rank': record.get('CURRENT_RANK', 0),
            'tts_priority': 'high' if abs(record.get('RANK_DELTA', 0)) >= 20 else 'medium'
        })
    
    return events

def store_payload_s3(payload: Dict[str, Any], user_id: str) -> str:
    """Store payload in S3."""
    bucket = os.environ.get('S3_BUCKET_PAYLOADS', 'serp-radio-dev-payloads')
    timestamp = int(datetime.now().timestamp())
    key = f"payloads/{user_id}/{timestamp}.json"
    
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(payload, indent=2, default=str),
            ContentType='application/json'
        )
        logger.info(f"Stored payload at s3://{bucket}/{key}")
        return key
    except Exception as e:
        logger.error(f"Failed to store payload: {str(e)}")
        raise

def create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create successful response."""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(data)
    }

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create error response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message})
    } 