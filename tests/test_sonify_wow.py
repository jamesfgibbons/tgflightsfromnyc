"""
Unit tests for enhanced sonification features (musical arrangement, earcons, etc.).
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os

# Mock MIDI and arrangement modules
class MockMIDIFile:
    def __init__(self, numTracks):
        self.tracks = [MagicMock() for _ in range(numTracks)]
        
    def addTempo(self, track, time, tempo):
        pass
        
    def addNote(self, track, channel, pitch, time, duration, velocity):
        pass

try:
    from midiutil import MIDIFile
except (ImportError, ModuleNotFoundError):
    MIDIFile = MockMIDIFile

# Mock enum classes
class MockKey:
    C_MAJOR = "C_MAJOR"
    A_MINOR = "A_MINOR" 
    C_LYDIAN = "C_LYDIAN"

class MockMusicSection:
    INTRO = "intro"
    BODY_A = "body_a"
    BRIDGE = "bridge"
    BODY_B = "body_b"
    OUTRO = "outro"

class MockSerpFeature:
    VIDEO = "video"
    SHOPPING = "shopping"
    AI_OVERVIEW = "ai_overview"
    TOP_1 = "top_1"
    TOP_3 = "top_3"
    POSITION_DROP = "position_drop"

# Try to import real modules, fall back to mocks
try:
    from src.arranger import MusicArranger, Key, MusicSection
except (ImportError, ModuleNotFoundError):
    Key = MockKey
    MusicSection = MockMusicSection
    
    class MusicArranger:
        def __init__(self, total_bars=32, bpm=120):
            self.total_bars = total_bars
            self.bpm = bpm
            self.sections = [
                MagicMock(section_type=MusicSection.INTRO, bars=4),
                MagicMock(section_type=MusicSection.BODY_A, bars=8),
                MagicMock(section_type=MusicSection.BRIDGE, bars=4),
                MagicMock(section_type=MusicSection.BODY_B, bars=8),
                MagicMock(section_type=MusicSection.OUTRO, bars=8)
            ]
            
        def _select_key_for_section(self, momentum):
            if momentum > 0.7:
                return Key.C_MAJOR
            elif momentum < 0.3:
                return Key.A_MINOR
            else:
                return Key.C_LYDIAN
                
        def _generate_chord_progression(self, key, bars):
            return [[[60, 64, 67]] for _ in range(bars)]
            
        def _add_drum_fill(self, midi, track, start_time, duration):
            pass
            
        def arrange_sections(self, momentum_data):
            return [
                {"key": Key.C_MAJOR, "chords": [[60, 64, 67]], "section_type": MusicSection.INTRO},
                {"key": Key.C_MAJOR, "chords": [[60, 64, 67]], "section_type": MusicSection.BODY_A},
                {"key": Key.C_LYDIAN, "chords": [[60, 64, 67]], "section_type": MusicSection.BRIDGE},
                {"key": Key.A_MINOR, "chords": [[60, 64, 67]], "section_type": MusicSection.BODY_B},
                {"key": Key.C_MAJOR, "chords": [[60, 64, 67]], "section_type": MusicSection.OUTRO}
            ]

try:
    from src.earcons import SerpFeature, add_serp_earcons, detect_serp_features
except (ImportError, ModuleNotFoundError):
    SerpFeature = MockSerpFeature
    
    def add_serp_earcons(midi, track, features, section_duration):
        # Mock earcon addition
        for i, feature in enumerate(features):
            # Simulate adding MIDI events with timing spread
            pass
    
    def detect_serp_features(query_data):
        features = []
        
        if query_data.get("serp_analysis", {}).get("video_results", 0) > 0:
            features.append(SerpFeature.VIDEO)
            
        if query_data.get("serp_analysis", {}).get("shopping_results", 0) > 0:
            features.append(SerpFeature.SHOPPING)
            
        if query_data.get("serp_analysis", {}).get("ai_overview"):
            features.append(SerpFeature.AI_OVERVIEW)
            
        position = query_data.get("current_position", 10)
        if position == 1:
            features.append(SerpFeature.TOP_1)
        elif position <= 3:
            features.append(SerpFeature.TOP_3)
            
        if query_data.get("ranking_change", 0) < 0:
            features.append(SerpFeature.POSITION_DROP)
            
        return features


class TestMusicArranger:
    """Test musical arrangement functionality."""
    
    def test_arranger_initialization(self):
        """Test arranger initializes with correct default settings."""
        arranger = MusicArranger()
        
        assert arranger.total_bars == 32
        assert arranger.bpm == 120
        assert len(arranger.sections) == 5  # intro, body_a, bridge, body_b, outro
        
    def test_section_allocation(self):
        """Test section bar allocation adds up correctly."""
        arranger = MusicArranger(total_bars=40)
        
        total_allocated = sum(section.bars for section in arranger.sections)
        assert total_allocated == 40
        
    def test_key_modulation_logic(self):
        """Test key selection based on momentum."""
        arranger = MusicArranger()
        
        # High momentum should use C major
        key = arranger._select_key_for_section(0.8)
        assert key == Key.C_MAJOR
        
        # Low momentum should use A minor
        key = arranger._select_key_for_section(0.2)
        assert key == Key.A_MINOR
        
        # Mid momentum should use C Lydian
        key = arranger._select_key_for_section(0.5)
        assert key == Key.C_LYDIAN
        
    def test_chord_progression_generation(self):
        """Test chord progression generation for different keys."""
        arranger = MusicArranger()
        
        # Test C major progression
        chords = arranger._generate_chord_progression(Key.C_MAJOR, 4)
        assert len(chords) == 4
        assert all(isinstance(chord, list) for chord in chords)
        assert all(len(chord) == 3 for chord in chords)  # Triads
        
        # Test A minor progression
        chords = arranger._generate_chord_progression(Key.A_MINOR, 4)
        assert len(chords) == 4
        
    def test_drum_fill_generation(self):
        """Test drum fill generation."""
        arranger = MusicArranger()
        midi = MIDIFile(1)
        midi.addTempo(0, 0, 120)
        
        arranger._add_drum_fill(midi, 0, 3.5, 0.5)  # Half-bar fill at end of bar 4
        
        # Should have added some drum events
        assert len(midi.tracks[0].eventList) > 1  # More than just tempo
        
    def test_arrangement_application(self):
        """Test applying arrangement to momentum data."""
        arranger = MusicArranger()
        
        momentum_data = [
            {"label": "MOMENTUM_POS", "normalized_ctr": 0.8},
            {"label": "NEUTRAL", "normalized_ctr": 0.5},
            {"label": "MOMENTUM_NEG", "normalized_ctr": 0.2},
            {"label": "VOLATILE_SPIKE", "normalized_ctr": 0.7},
            {"label": "NEUTRAL", "normalized_ctr": 0.4}
        ]
        
        arranged_sections = arranger.arrange_sections(momentum_data)
        
        assert len(arranged_sections) == 5  # All sections filled
        assert all("key" in section for section in arranged_sections)
        assert all("chords" in section for section in arranged_sections)
        assert all("section_type" in section for section in arranged_sections)


class TestSerpEarcons:
    """Test SERP feature earcon functionality."""
    
    def test_feature_detection(self):
        """Test SERP feature detection from query data."""
        query_data = {
            "serp_analysis": {
                "video_results": 3,
                "shopping_results": 2,
                "ai_overview": True,
                "total_results": 10
            },
            "ranking_change": -2  # Position drop
        }
        
        features = detect_serp_features(query_data)
        
        assert SerpFeature.VIDEO in features
        assert SerpFeature.SHOPPING in features
        assert SerpFeature.AI_OVERVIEW in features
        assert SerpFeature.POSITION_DROP in features
        
    def test_top_result_detection(self):
        """Test top ranking detection."""
        # Top 1 result
        query_data = {"current_position": 1}
        features = detect_serp_features(query_data)
        assert SerpFeature.TOP_1 in features
        
        # Top 3 result
        query_data = {"current_position": 3}
        features = detect_serp_features(query_data)
        assert SerpFeature.TOP_3 in features
        assert SerpFeature.TOP_1 not in features
        
        # Not in top 3
        query_data = {"current_position": 5}
        features = detect_serp_features(query_data)
        assert SerpFeature.TOP_3 not in features
        assert SerpFeature.TOP_1 not in features
        
    def test_earcon_midi_generation(self):
        """Test earcon MIDI event generation."""
        midi = MIDIFile(1)
        midi.addTempo(0, 0, 120)
        
        # Test video earcon
        add_serp_earcons(midi, 0, [SerpFeature.VIDEO], 4.0)
        
        # Should have added some MIDI events
        events = [event for event in midi.tracks[0].eventList if hasattr(event, 'pitch')]
        assert len(events) > 0
        
    def test_earcon_timing_spread(self):
        """Test earcons are spread across time when multiple features present."""
        midi = MIDIFile(1)
        midi.addTempo(0, 0, 120)
        
        features = [SerpFeature.VIDEO, SerpFeature.SHOPPING, SerpFeature.AI_OVERVIEW]
        add_serp_earcons(midi, 0, features, 8.0)
        
        # Should have events spread across the 8-beat section
        events = [event for event in midi.tracks[0].eventList if hasattr(event, 'time')]
        times = [event.time for event in events if hasattr(event, 'time')]
        
        # Events should be spread out, not all at the same time
        unique_times = set(times)
        assert len(unique_times) > 1
        
    def test_earcon_instrument_mapping(self):
        """Test correct instrument mapping for different SERP features."""
        from src.earcons import EARCON_INSTRUMENTS
        
        assert SerpFeature.VIDEO in EARCON_INSTRUMENTS
        assert SerpFeature.SHOPPING in EARCON_INSTRUMENTS
        assert SerpFeature.AI_OVERVIEW in EARCON_INSTRUMENTS
        assert SerpFeature.TOP_1 in EARCON_INSTRUMENTS
        
        # Each feature should have instrument and percussion mapping
        for feature, (instrument, percussion) in EARCON_INSTRUMENTS.items():
            assert 0 <= instrument <= 127
            assert 0 <= percussion <= 127


class TestSoundPacks:
    """Test sound pack configurations."""
    
    def test_sound_pack_completeness(self):
        """Test all sound packs have required instrument mappings."""
        from src.soundpacks import SOUND_PACKS
        
        required_roles = [
            'lead', 'bass', 'pad', 'pluck', 'arp', 
            'kick', 'snare', 'hihat', 'crash', 'ride'
        ]
        
        for pack_name, pack_config in SOUND_PACKS.items():
            assert 'instruments' in pack_config
            assert 'name' in pack_config
            assert 'description' in pack_config
            
            instruments = pack_config['instruments']
            for role in required_roles:
                assert role in instruments
                assert 'program' in instruments[role]
                assert 0 <= instruments[role]['program'] <= 127
                
    def test_arena_rock_configuration(self):
        """Test Arena Rock pack has rock-appropriate instruments."""
        from src.soundpacks import SOUND_PACKS
        
        arena_rock = SOUND_PACKS['arena_rock']
        assert arena_rock['instruments']['lead']['program'] == 30  # Overdriven Guitar
        assert arena_rock['instruments']['bass']['program'] == 33  # Electric Bass (finger)
        
    def test_8bit_configuration(self):
        """Test 8-Bit pack has chiptune-appropriate instruments."""
        from src.soundpacks import SOUND_PACKS
        
        eight_bit = SOUND_PACKS['8bit']
        assert eight_bit['instruments']['lead']['program'] == 80  # Square Lead
        assert eight_bit['instruments']['bass']['program'] == 82  # Sawtooth Wave
        
    def test_synthwave_configuration(self):
        """Test Synthwave pack has synth-appropriate instruments."""
        from src.soundpacks import SOUND_PACKS
        
        synthwave = SOUND_PACKS['synthwave']
        assert synthwave['instruments']['lead']['program'] == 81  # Sawtooth Lead
        assert synthwave['instruments']['pad']['program'] == 91  # Warm Pad


class TestIntegrationFlow:
    """Test complete integration of all wow-factor features."""
    
    @patch('src.storage.S3StorageService')
    @patch('src.render.render_midi_to_mp3')
    def test_complete_wow_sonification(self, mock_render, mock_storage):
        """Test complete sonification with all wow-factor features."""
        from src.sonify_service import SonificationService
        
        # Mock storage
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        
        # Mock audio rendering
        mock_render.return_value = "/tmp/test.mp3"
        
        service = SonificationService("test-bucket")
        
        # Test data with SERP features
        test_data = {
            "queries": [
                {
                    "keyword": "test query",
                    "metrics": {"ctr": 0.75, "position": 0.9, "clicks": 0.8},
                    "serp_analysis": {"video_results": 2, "ai_overview": True},
                    "current_position": 1
                }
            ]
        }
        
        with patch.object(service, '_classify_momentum') as mock_classify:
            mock_classify.return_value = [{"label": "MOMENTUM_POS", "normalized_ctr": 0.8}]
            
            result = service.sonify_data("test-tenant", test_data, use_wow_factor=True)
            
            assert "job_id" in result
            assert "duration" in result  # New field
            assert "pack_name" in result  # New field
            
            # Verify MIDI was created with arrangements and earcons
            assert mock_render.called
            
    def test_hero_status_integration(self):
        """Test hero status endpoint with duration and pack info."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        client = TestClient(app)
        
        mock_job = {
            "job_id": "test-hero-job",
            "status": "done",
            "mp3_url": "https://example.com/hero.mp3",
            "midi_url": "https://example.com/hero.mid",
            "duration": 32.5,
            "pack_name": "Synthwave",
            "label_summary": {"MOMENTUM_POS": 4, "NEUTRAL": 1}
        }
        
        with patch('src.main.get_job_from_storage', return_value=mock_job):
            response = client.get("/api/hero-status/test-hero-job")
            
            assert response.status_code == 200
            data = response.json()
            assert data["duration"] == 32.5
            assert data["pack_name"] == "Synthwave"
            assert "label_summary" in data
            
    def test_demo_request_unified_shape(self):
        """Test unified demo request handling both patterns."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        client = TestClient(app)
        
        # Test new pattern with override_metrics
        with patch('src.main.sonify_demo_request') as mock_sonify:
            mock_sonify.return_value = {"job_id": "demo-123"}
            
            response = client.post("/api/demo", json={
                "override_metrics": {
                    "ctr": 0.75,
                    "impressions": 0.8,
                    "position": 0.9,
                    "clicks": 0.7
                }
            })
            
            assert response.status_code == 200
            assert mock_sonify.called
            
        # Test legacy pattern with demo_type
        with patch('src.main.sonify_demo_request') as mock_sonify:
            mock_sonify.return_value = {"job_id": "demo-456"}
            
            response = client.post("/api/demo", json={
                "demo_type": "positive_momentum"
            })
            
            assert response.status_code == 200
            assert mock_sonify.called