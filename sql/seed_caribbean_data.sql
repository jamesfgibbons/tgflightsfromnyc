-- SERP Radio: Caribbean "Kokomo" Theme Seed Data
-- Based on Google keyword CSV data and visibility inventory

-- Insert Caribbean flight visibility data
INSERT INTO flight_visibility (
    region, origin_code, destination_code, destination_name,
    keyword, impressions, clicks, avg_position, ctr,
    search_volume, avg_price_usd, price_volatility,
    theme, sub_theme, sound_pack_hint,
    data_date
) VALUES 

-- Puerto Rico (SJU) - High volume routes
('Caribbean', 'JFK', 'SJU', 'Puerto Rico', 'cheap flights nyc to puerto rico', 8540, 183, 3.2, 0.0214, 5490, 289.50, 0.15, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'LGA', 'SJU', 'Puerto Rico', 'laguardia to san juan flights', 4210, 95, 4.1, 0.0226, 2890, 315.75, 0.18, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'EWR', 'SJU', 'Puerto Rico', 'newark puerto rico direct flights', 3650, 78, 3.8, 0.0214, 2340, 298.25, 0.12, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),

-- Aruba (AUA) - Premium beach destination
('Caribbean', 'JFK', 'AUA', 'Aruba', 'jfk to aruba nonstop', 5120, 142, 2.9, 0.0277, 3610, 485.90, 0.22, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'EWR', 'AUA', 'Aruba', 'newark aruba flights', 2890, 68, 4.2, 0.0235, 1950, 465.50, 0.19, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'JFK', 'AUA', 'Aruba', 'cheap flights to aruba from nyc', 4560, 98, 3.6, 0.0215, 3200, 445.75, 0.25, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),

-- Dominican Republic (SDQ) - Budget-friendly option
('Caribbean', 'JFK', 'SDQ', 'Dominican Republic', 'jfk to santo domingo flights', 4890, 125, 3.4, 0.0256, 3580, 325.80, 0.28, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'LGA', 'SDQ', 'Dominican Republic', 'laguardia dominican republic', 2340, 54, 4.8, 0.0231, 1680, 345.25, 0.24, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'EWR', 'SDQ', 'Dominican Republic', 'newark to punta cana flights', 3210, 71, 4.1, 0.0221, 2450, 298.95, 0.31, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),

-- Jamaica (MBJ) - Montego Bay focus
('Caribbean', 'JFK', 'MBJ', 'Jamaica', 'jfk to montego bay jamaica', 4650, 118, 3.1, 0.0254, 3560, 415.60, 0.20, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'EWR', 'MBJ', 'Jamaica', 'newark to jamaica flights', 2580, 62, 4.3, 0.0240, 1890, 395.40, 0.17, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'JFK', 'MBJ', 'Jamaica', 'cheap nyc to jamaica flights', 3890, 89, 3.9, 0.0229, 2890, 375.85, 0.23, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),

-- Cancún (CUN) - Mexican Caribbean
('Caribbean', 'JFK', 'CUN', 'Cancún', 'jfk to cancun direct flights', 5460, 156, 2.7, 0.0286, 3040, 345.75, 0.19, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'LGA', 'CUN', 'Cancún', 'laguardia to cancun flights', 3120, 78, 4.0, 0.0250, 2180, 365.50, 0.22, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'EWR', 'CUN', 'Cancún', 'newark cancun nonstop', 2890, 65, 3.8, 0.0225, 1950, 355.25, 0.16, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),

-- Curaçao (CUR) - Dutch Caribbean gem
('Caribbean', 'JFK', 'CUR', 'Curaçao', 'jfk to curacao flights', 1450, 38, 4.6, 0.0262, 860, 625.40, 0.35, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'EWR', 'CUR', 'Curaçao', 'newark to curacao', 890, 21, 5.2, 0.0236, 580, 645.75, 0.32, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'JFK', 'CUR', 'Curaçao', 'cheap flights nyc curacao', 1120, 28, 4.9, 0.0250, 720, 598.60, 0.38, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),

-- Nassau, Bahamas (NAS) - Close Caribbean option
('Caribbean', 'JFK', 'NAS', 'Nassau', 'jfk to nassau bahamas', 2180, 58, 3.5, 0.0266, 1240, 285.90, 0.21, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'LGA', 'NAS', 'Nassau', 'laguardia to bahamas flights', 1560, 42, 4.4, 0.0269, 890, 295.75, 0.18, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'EWR', 'NAS', 'Nassau', 'newark bahamas direct', 1290, 31, 4.7, 0.0240, 720, 305.50, 0.24, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),

-- Special Caribbean search patterns
('Caribbean', 'NYC_ALL', 'MULTI', 'Caribbean', 'best caribbean islands from nyc', 6890, 189, 2.8, 0.0274, 4580, 425.00, 0.30, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'NYC_ALL', 'MULTI', 'Caribbean', 'cheap caribbean flights winter', 5240, 142, 3.2, 0.0271, 3650, 375.25, 0.28, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'NYC_ALL', 'MULTI', 'Caribbean', 'nyc to caribbean vacation deals', 4560, 125, 3.6, 0.0274, 3120, 395.80, 0.26, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE),
('Caribbean', 'NYC_ALL', 'MULTI', 'Caribbean', 'hurricane season caribbean flight deals', 2890, 78, 4.1, 0.0270, 1950, 298.50, 0.42, 'flights_from_nyc', 'caribbean_kokomo', 'Tropical Pop', CURRENT_DATE);

-- Insert sample cache jobs for Caribbean theme
INSERT INTO cache_jobs (
    job_id, vertical, theme, sub_theme, origin_prompt, openai_response, 
    tokens_used, processing_time_ms, status
) VALUES 

('kokomo_001_20250116', 'travel', 'flights_from_nyc', 'caribbean_kokomo', 
 'Cheapest JFK → Puerto Rico in next 60 days; include ultra-budget options',
 '{"estimated_price_range": [245, 385], "carrier_likelihood": ["JetBlue", "Spirit", "Southwest"], "routing_strategy": "direct", "novelty_score": 7, "deal_quality": "good", "seasonal_factors": ["winter_escape", "spring_break_approaching"]}',
 145, 1250, 'completed'),

('kokomo_002_20250116', 'travel', 'flights_from_nyc', 'caribbean_kokomo',
 'JFK to Aruba: red-eye only; find sub-$400 windows', 
 '{"estimated_price_range": [380, 520], "carrier_likelihood": ["American", "JetBlue"], "routing_strategy": "direct", "novelty_score": 6, "deal_quality": "fair", "seasonal_factors": ["premium_beach_destination"]}',
 138, 1180, 'completed'),

('kokomo_003_20250116', 'travel', 'flights_from_nyc', 'caribbean_kokomo',
 'Which Caribbean island has the biggest JFK fare drops in winter?',
 '{"estimated_price_range": [295, 450], "carrier_likelihood": ["Multiple"], "routing_strategy": "variable", "novelty_score": 8, "deal_quality": "excellent", "seasonal_factors": ["winter_deals", "hurricane_season_recovery"]}',
 152, 1320, 'completed'),

('kokomo_004_20250116', 'travel', 'flights_from_nyc', 'caribbean_kokomo',
 'Ultra-budget NYC to Caribbean: Spirit vs JetBlue vs connecting flights',
 '{"estimated_price_range": [189, 295], "carrier_likelihood": ["Spirit", "JetBlue", "Southwest"], "routing_strategy": "connecting", "novelty_score": 9, "deal_quality": "excellent", "seasonal_factors": ["budget_carrier_war"]}',
 167, 1420, 'completed');

-- Insert sample momentum cache entries
INSERT INTO momentum_cache (
    cache_key, vertical, theme, sub_theme, origin, destination,
    momentum_bands, label_summary, sound_pack, tempo_bpm, total_bars, duration_sec
) VALUES 

('kokomo_jfk_sju_001', 'travel', 'flights_from_nyc', 'caribbean_kokomo', 'JFK', 'SJU',
 '[{"t0": 0, "t1": 3.2, "label": "positive", "score": 0.7}, {"t0": 3.2, "t1": 6.4, "label": "positive", "score": 0.5}, {"t0": 6.4, "t1": 9.6, "label": "neutral", "score": 0.1}, {"t0": 9.6, "t1": 12.8, "label": "positive", "score": 0.6}]',
 '{"positive": 6, "neutral": 2, "negative": 2}', 'Tropical Pop', 104, 28, 32.3),

('kokomo_jfk_aua_001', 'travel', 'flights_from_nyc', 'caribbean_kokomo', 'JFK', 'AUA',
 '[{"t0": 0, "t1": 3.2, "label": "positive", "score": 0.8}, {"t0": 3.2, "t1": 6.4, "label": "positive", "score": 0.6}, {"t0": 6.4, "t1": 9.6, "label": "neutral", "score": 0.2}, {"t0": 9.6, "t1": 12.8, "label": "positive", "score": 0.7}]',
 '{"positive": 7, "neutral": 2, "negative": 1}', 'Tropical Pop', 104, 28, 32.3),

('kokomo_multi_winter', 'travel', 'flights_from_nyc', 'caribbean_kokomo', 'NYC_ALL', 'MULTI',
 '[{"t0": 0, "t1": 3.2, "label": "positive", "score": 0.9}, {"t0": 3.2, "t1": 6.4, "label": "positive", "score": 0.8}, {"t0": 6.4, "t1": 9.6, "label": "positive", "score": 0.6}, {"t0": 9.6, "t1": 12.8, "label": "positive", "score": 0.7}]',
 '{"positive": 8, "neutral": 1, "negative": 1}', 'Tropical Pop', 104, 30, 34.6);

-- Create regional keyword aggregations
INSERT INTO flight_visibility (
    region, origin_code, destination_code, destination_name,
    keyword, impressions, clicks, avg_position, ctr,
    search_volume, avg_price_usd, price_volatility,
    theme, sub_theme, sound_pack_hint,
    data_date
) 
SELECT 
    'Caribbean_Summary' as region,
    'NYC_ALL' as origin_code,
    'CARIBBEAN' as destination_code,
    'Caribbean Islands' as destination_name,
    'caribbean vacation from nyc' as keyword,
    SUM(impressions) as impressions,
    SUM(clicks) as clicks,
    AVG(avg_position) as avg_position,
    AVG(ctr) as ctr,
    SUM(search_volume) as search_volume,
    AVG(avg_price_usd) as avg_price_usd,
    AVG(price_volatility) as price_volatility,
    'flights_from_nyc' as theme,
    'caribbean_kokomo' as sub_theme,
    'Tropical Pop' as sound_pack_hint,
    CURRENT_DATE as data_date
FROM flight_visibility 
WHERE region = 'Caribbean';