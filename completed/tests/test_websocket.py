"""
Tests for WebSocket live streaming functionality.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

import redis.asyncio as redis
import msgpack
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from src.live_server import app, manager
from src.publisher import SERPPublisher
from src.models import NoteEvent, SERPSnapshot, LiveSession


@pytest.fixture
async def redis_client():
    """Create a test Redis client."""
    client = redis.from_url("redis://localhost:6379", decode_responses=False)
    try:
        await client.ping()
        yield client
    finally:
        await client.close()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = Mock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_bytes = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.receive_bytes = AsyncMock()
    ws.close = AsyncMock()
    return ws


class TestWebSocketConnection:
    """Test WebSocket connection and message handling."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, mock_websocket):
        """Test basic WebSocket connection."""
        session_id = "test-session-123"
        api_key = "test-api-key"
        station = "daily"
        
        await manager.connect(mock_websocket, session_id, api_key, station)
        
        # Check session was created
        assert session_id in manager.sessions
        assert session_id in manager.active_connections
        
        session = manager.sessions[session_id]
        assert session.session_id == session_id
        assert session.api_key == api_key
        assert session.station == station
        
        # Check welcome message was sent
        mock_websocket.send_bytes.assert_called_once()
        
        # Test disconnect
        manager.disconnect(session_id)
        assert session_id not in manager.sessions
        assert session_id not in manager.active_connections
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self, mock_websocket):
        """Test sending messages to specific WebSocket connection."""
        session_id = "test-session-456"
        
        await manager.connect(mock_websocket, session_id, "test-key", "daily")
        
        test_message = {
            "type": "test",
            "data": {"message": "Hello world"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await manager.send_personal_message(session_id, test_message)
        
        # Check message was sent as msgpack
        mock_websocket.send_bytes.assert_called()
        call_args = mock_websocket.send_bytes.call_args[0][0]
        decoded_message = msgpack.unpackb(call_args)
        
        assert decoded_message["type"] == "test"
        assert decoded_message["data"]["message"] == "Hello world"
        
        # Check session stats were updated
        session = manager.sessions[session_id]
        assert session.events_sent > 0
    
    @pytest.mark.asyncio
    async def test_broadcast_to_station(self, mock_websocket):
        """Test broadcasting messages to specific station."""
        # Create multiple sessions on different stations
        sessions = [
            ("session1", "daily"),
            ("session2", "daily"),
            ("session3", "ai-lens")
        ]
        
        for session_id, station in sessions:
            ws = Mock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_bytes = AsyncMock()
            await manager.connect(ws, session_id, "test-key", station)
        
        test_message = {
            "type": "broadcast_test",
            "data": {"station": "daily"}
        }
        
        await manager.broadcast_to_station("daily", test_message)
        
        # Check only daily station sessions received the message
        daily_sessions = [s for s in manager.sessions.values() if s.station == "daily"]
        assert len(daily_sessions) == 2
        
        for session in daily_sessions:
            assert session.events_sent > 0


class TestSERPPublisher:
    """Test SERP data publisher and event generation."""
    
    @pytest.fixture
    def publisher(self):
        """Create a test publisher instance."""
        return SERPPublisher()
    
    @pytest.mark.asyncio
    async def test_publisher_initialization(self, publisher):
        """Test publisher Redis connection."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            await publisher.initialize()
            
            mock_redis.assert_called_once()
            mock_client.ping.assert_called_once()
    
    def test_create_snapshot_from_dataframe(self, publisher):
        """Test converting DataFrame to snapshot dictionary."""
        import pandas as pd
        
        # Create test DataFrame
        test_data = {
            'keyword': ['test keyword', 'another keyword'],
            'domain': ['example.com', 'test.com'],
            'rank_absolute': [1, 5],
            'engine': ['google_web', 'google_ai'],
            'share_pct': [0.8, 0.3],
            'rich_type': ['', 'video'],
            'segment': ['Central', 'West'],
            'ai_overview': [False, True],
            'etv': [1000, 500]
        }
        
        df = pd.DataFrame(test_data)
        snapshot = publisher.create_snapshot_from_dataframe(df)
        
        assert len(snapshot) == 2
        
        # Check first entry
        first_key = 'test keyword:example.com:google_web'
        assert first_key in snapshot
        
        first_snapshot = snapshot[first_key]
        assert first_snapshot.keyword == 'test keyword'
        assert first_snapshot.domain == 'example.com'
        assert first_snapshot.rank_absolute == 1
        assert first_snapshot.engine == 'google_web'
    
    def test_detect_changes(self, publisher):
        """Test change detection between snapshots."""
        # Create initial snapshot
        initial_snapshot = {
            'keyword1:domain1:google_web': SERPSnapshot(
                keyword='keyword1',
                domain='domain1',
                rank_absolute=3,
                engine='google_web',
                share_pct=0.5,
                rich_type='',
                segment='Central',
                ai_overview=False,
                etv=1000
            )
        }
        
        publisher.last_snapshot = initial_snapshot
        
        # Create current snapshot with changes
        current_snapshot = {
            'keyword1:domain1:google_web': SERPSnapshot(
                keyword='keyword1',
                domain='domain1',
                rank_absolute=1,  # Rank improved by 2
                engine='google_web',
                share_pct=0.7,  # Share increased
                rich_type='',
                segment='Central',
                ai_overview=False,
                etv=1000
            ),
            'keyword2:domain2:google_ai': SERPSnapshot(  # New entry
                keyword='keyword2',
                domain='domain2',
                rank_absolute=5,
                engine='google_ai',
                share_pct=0.3,
                rich_type='video',
                segment='East',
                ai_overview=True,
                etv=500
            )
        }
        
        changes = publisher.detect_changes(current_snapshot)
        
        # Should detect rank change and new entry
        assert len(changes) == 2
        
        # Check rank change event
        rank_change_event = next(e for e in changes if e['rank_delta'] == -2)
        assert rank_change_event['keyword'] == 'keyword1'
        assert rank_change_event['domain'] == 'domain1'
        
        # Check new entry event
        new_entry_event = next(e for e in changes if e['is_new'] == True)
        assert new_entry_event['keyword'] == 'keyword2'
        assert new_entry_event['domain'] == 'domain2'
    
    def test_create_note_event(self, publisher):
        """Test creating note events from SERP snapshots."""
        snapshot = SERPSnapshot(
            keyword='test keyword',
            domain='example.com',
            rank_absolute=2,
            engine='google_web',
            share_pct=0.6,
            rich_type='video',
            segment='West',
            ai_overview=False,
            etv=1500
        )
        
        rank_delta = -3  # Improved by 3 positions
        
        note_event = publisher.create_note_event(snapshot, rank_delta)
        
        assert note_event is not None
        assert note_event['keyword'] == 'test keyword'
        assert note_event['domain'] == 'example.com'
        assert note_event['rank_delta'] == -3
        assert note_event['event_type'] == 'note_on'
        
        # Check musical parameters
        assert 0 <= note_event['pitch'] <= 127
        assert 40 <= note_event['velocity'] <= 127
        assert -1.0 <= note_event['pan'] <= 1.0
        assert 0.1 <= note_event['duration'] <= 4.0
        
        # Check anomaly detection
        assert note_event['anomaly'] == False  # rank_delta not >= 5
    
    @pytest.mark.asyncio
    async def test_publish_events(self, publisher):
        """Test publishing events to Redis."""
        mock_client = AsyncMock()
        publisher.redis_client = mock_client
        
        test_events = [
            {
                'event_type': 'note_on',
                'keyword': 'test',
                'domain': 'example.com',
                'rank_delta': -2,
                'pitch': 65,
                'velocity': 80,
                'pan': 0.0,
                'duration': 1.0,
                'instrument': 0,
                'channel': 0,
                'timestamp': datetime.utcnow().isoformat(),
                'anomaly': False,
                'brand_rank': None,
                'is_new': False
            }
        ]
        
        await publisher.publish_events(test_events)
        
        # Check Redis publish was called
        mock_client.publish.assert_called_once()
        
        # Check message was serialized with msgpack
        call_args = mock_client.publish.call_args
        channel, message = call_args[0]
        
        assert channel == "serp_events"
        
        # Deserialize and check message
        decoded_event = msgpack.unpackb(message)
        assert decoded_event['keyword'] == 'test'
        assert decoded_event['rank_delta'] == -2


class TestNoteEventModels:
    """Test Pydantic models for note events."""
    
    def test_note_event_validation(self):
        """Test NoteEvent model validation."""
        # Valid note event
        valid_event = NoteEvent(
            pitch=60,
            velocity=80,
            pan=0.0,
            duration=1.5,
            keyword="test keyword",
            engine="google_web",
            domain="example.com",
            rank_delta=-2
        )
        
        assert valid_event.pitch == 60
        assert valid_event.velocity == 80
        assert valid_event.keyword == "test keyword"
        assert valid_event.anomaly == False  # default
        
        # Test validation errors
        with pytest.raises(ValueError):
            NoteEvent(
                pitch=200,  # Invalid: > 127
                velocity=80,
                pan=0.0,
                duration=1.5,
                keyword="test",
                engine="google_web",
                domain="example.com",
                rank_delta=-2
            )
    
    def test_serp_snapshot_diff_key(self):
        """Test SERPSnapshot diff_key generation."""
        snapshot = SERPSnapshot(
            keyword="test keyword",
            domain="example.com",
            rank_absolute=3,
            engine="google_web",
            share_pct=0.5,
            rich_type="",
            segment="Central",
            ai_overview=False,
            etv=1000
        )
        
        expected_key = "test keyword:example.com:google_web"
        assert snapshot.diff_key() == expected_key


class TestIntegration:
    """Integration tests for the complete live streaming system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_flow(self, redis_client):
        """Test complete flow from SERP data to WebSocket delivery."""
        # This test requires a running Redis instance
        try:
            await redis_client.ping()
        except:
            pytest.skip("Redis not available for integration test")
        
        # Create publisher and publish a test event
        publisher = SERPPublisher()
        await publisher.initialize()
        
        test_events = [{
            'event_type': 'note_on',
            'keyword': 'integration test',
            'domain': 'test.com',
            'rank_delta': -1,
            'pitch': 60,
            'velocity': 80,
            'pan': 0.0,
            'duration': 1.0,
            'instrument': 0,
            'channel': 0,
            'timestamp': datetime.utcnow().isoformat(),
            'anomaly': False,
            'brand_rank': None,
            'is_new': False
        }]
        
        await publisher.publish_events(test_events)
        
        # Brief delay to allow message processing
        await asyncio.sleep(0.1)
        
        # Verify the event was published
        assert publisher.events_published > 0
        
        await publisher.close() 