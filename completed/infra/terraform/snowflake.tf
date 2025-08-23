# Snowflake Database
resource "snowflake_database" "serp_radio" {
  name    = "SERP_RADIO"
  comment = "Database for SERP Loop Radio market share data"
}

# Schema for market share data
resource "snowflake_schema" "market_share" {
  database = snowflake_database.serp_radio.name
  name     = "MARKET_SHARE"
  comment  = "Schema containing market share ranking data"
}

# Market Share Rank Table
resource "snowflake_table" "market_share_rank" {
  database = snowflake_database.serp_radio.name
  schema   = snowflake_schema.market_share.name
  name     = "MARKET_SHARE_RANK"
  comment  = "Table storing market share ranking data with DNA generation"

  column {
    name = "QUERY_ID"
    type = "VARCHAR(100)"
  }

  column {
    name = "KEYWORD"
    type = "VARCHAR(500)"
  }

  column {
    name = "DOMAIN"
    type = "VARCHAR(200)"
  }

  column {
    name = "CURRENT_RANK"
    type = "NUMBER(10,0)"
  }

  column {
    name = "PREVIOUS_RANK"
    type = "NUMBER(10,0)"
  }

  column {
    name = "RANK_DELTA"
    type = "NUMBER(10,0)"
  }

  column {
    name = "MARKET_SHARE_PCT"
    type = "NUMBER(5,2)"
  }

  column {
    name = "SEARCH_VOLUME"
    type = "NUMBER(20,0)"
  }

  column {
    name = "COMPETITION_SCORE"
    type = "NUMBER(3,2)"
  }

  column {
    name = "DATE_CAPTURED"
    type = "TIMESTAMP_NTZ"
  }

  column {
    name = "LOOP_DNA"
    type = "VARIANT"
    comment = "JSON object containing generated audio parameters"
  }

  column {
    name = "RANK_TIER"
    type = "VARCHAR(20)"
    comment = "Computed tier: TOP_3, TOP_10, TOP_50, BEYOND_50"
  }

  column {
    name = "CREATED_AT"
    type = "TIMESTAMP_NTZ"
    default {
      expression = "CURRENT_TIMESTAMP()"
    }
  }
}

# S3 Stage for CSV ingestion
resource "snowflake_stage" "serp_upload_stage" {
  database = snowflake_database.serp_radio.name
  schema   = snowflake_schema.market_share.name
  name     = "SERP_UPLOAD_STAGE"
  url      = "s3://${aws_s3_bucket.serp_upload_stage.bucket}/"
  
  storage_integration = snowflake_storage_integration.s3_integration.name
  
  file_format {
    type             = "CSV"
    skip_header      = 1
    field_delimiter  = ","
    record_delimiter = "\\n"
    null_if          = ["", "NULL", "null"]
    empty_field_as_null = true
    compression      = "AUTO"
  }
}

# Storage Integration for S3
resource "snowflake_storage_integration" "s3_integration" {
  name    = "SERP_S3_INTEGRATION"
  type    = "EXTERNAL_STAGE"
  enabled = true
  
  storage_allowed_locations = [
    "s3://${aws_s3_bucket.serp_upload_stage.bucket}/"
  ]
  
  storage_provider = "S3"
  storage_aws_role_arn = aws_iam_role.snowflake_role.arn
}

# Snowpipe for automatic ingestion
resource "snowflake_pipe" "serp_pipe" {
  database = snowflake_database.serp_radio.name
  schema   = snowflake_schema.market_share.name
  name     = "SERP_INGESTION_PIPE"
  
  copy_statement = <<-EOF
    COPY INTO ${snowflake_table.market_share_rank.name}
    (QUERY_ID, KEYWORD, DOMAIN, CURRENT_RANK, PREVIOUS_RANK, RANK_DELTA, 
     MARKET_SHARE_PCT, SEARCH_VOLUME, COMPETITION_SCORE, DATE_CAPTURED)
    FROM @${snowflake_stage.serp_upload_stage.name}
    FILE_FORMAT = (TYPE = 'CSV', SKIP_HEADER = 1)
    ON_ERROR = 'CONTINUE'
  EOF

  auto_ingest = true
  
  depends_on = [
    snowflake_table.market_share_rank,
    snowflake_stage.serp_upload_stage
  ]
}

# Task for daily DNA generation
resource "snowflake_task" "add_dna_task" {
  database  = snowflake_database.serp_radio.name
  schema    = snowflake_schema.market_share.name
  name      = "ADD_DNA_TASK"
  
  schedule  = "USING CRON 0 6 * * * UTC"  # Daily at 6 AM UTC
  
  sql_statement = <<-EOF
    UPDATE ${snowflake_table.market_share_rank.name}
    SET 
      RANK_TIER = CASE 
        WHEN CURRENT_RANK <= 3 THEN 'TOP_3'
        WHEN CURRENT_RANK <= 10 THEN 'TOP_10'
        WHEN CURRENT_RANK <= 50 THEN 'TOP_50'
        ELSE 'BEYOND_50'
      END,
      LOOP_DNA = OBJECT_CONSTRUCT(
        'tempo', CASE 
          WHEN ABS(RANK_DELTA) > 20 THEN 140 + (ABS(RANK_DELTA) * 2)
          WHEN ABS(RANK_DELTA) > 10 THEN 120 + ABS(RANK_DELTA)
          ELSE 110 + (ABS(RANK_DELTA) * 0.5)
        END,
        'instrument', CASE RANK_TIER
          WHEN 'TOP_3' THEN 'synth_lead'
          WHEN 'TOP_10' THEN 'electric_piano'
          WHEN 'TOP_50' THEN 'acoustic_guitar'
          ELSE 'bass_synth'
        END,
        'pitch_shift', CASE 
          WHEN RANK_DELTA > 0 THEN RANK_DELTA * 0.1  -- positive delta = higher pitch
          WHEN RANK_DELTA < 0 THEN RANK_DELTA * 0.05 -- negative delta = lower pitch
          ELSE 0
        END,
        'reverb_level', LEAST(0.8, COMPETITION_SCORE),
        'volume_boost', CASE 
          WHEN MARKET_SHARE_PCT > 50 THEN 1.2
          WHEN MARKET_SHARE_PCT > 25 THEN 1.1
          ELSE 1.0
        END,
        'emotional_weight', ABS(RANK_DELTA) / 100.0,
        'search_volume_factor', LOG(GREATEST(1, SEARCH_VOLUME)) / 20.0
      )
    WHERE LOOP_DNA IS NULL 
       OR DATE_TRUNC('DAY', CREATED_AT) = DATE_TRUNC('DAY', CURRENT_TIMESTAMP());
  EOF
  
  enabled = true
  
  depends_on = [snowflake_table.market_share_rank]
} 