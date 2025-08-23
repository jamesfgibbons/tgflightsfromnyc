# S3 Bucket for CSV Upload Staging
resource "aws_s3_bucket" "serp_upload_stage" {
  bucket = "${var.project_name}-upload-stage-${var.environment}"
  
  tags = {
    Name = "SERP Upload Staging"
    Purpose = "CSV file ingestion for Snowpipe"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "serp_upload_stage" {
  bucket = aws_s3_bucket.serp_upload_stage.id

  rule {
    id     = "expire_csv_files"
    status = "Enabled"

    expiration {
      days = var.s3_lifecycle_days
    }
  }
}

resource "aws_s3_bucket_notification" "serp_upload_notification" {
  bucket = aws_s3_bucket.serp_upload_stage.id

  queue {
    queue_arn = aws_sqs_queue.snowpipe_queue.arn
    events    = ["s3:ObjectCreated:*"]
  }
}

# S3 Bucket for HLS Output
resource "aws_s3_bucket" "serp_hls_output" {
  bucket = "${var.project_name}-hls-output-${var.environment}"
  
  tags = {
    Name = "SERP HLS Output"
    Purpose = "HLS audio stream chunks and manifests"
  }
}

resource "aws_s3_bucket_cors_configuration" "serp_hls_output" {
  bucket = aws_s3_bucket.serp_hls_output.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# CloudFront Distribution for HLS
resource "aws_cloudfront_distribution" "serp_hls_cf" {
  origin {
    domain_name = aws_s3_bucket.serp_hls_output.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.serp_hls_output.bucket}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.hls_oai.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "SERP Loop Radio HLS Distribution"
  default_root_object = "index.m3u8"

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.serp_hls_output.bucket}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "SERP HLS CloudFront"
  }
}

resource "aws_cloudfront_origin_access_identity" "hls_oai" {
  comment = "OAI for SERP HLS bucket"
}

# DynamoDB Table for User Preferences
resource "aws_dynamodb_table" "user_prefs" {
  name           = "${var.project_name}-user-prefs-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  tags = {
    Name = "SERP User Preferences"
  }
}

# SQS Queue for Snowpipe notifications
resource "aws_sqs_queue" "snowpipe_queue" {
  name = "${var.project_name}-snowpipe-queue-${var.environment}"
}

# IAM Role for Snowflake
resource "aws_iam_role" "snowflake_role" {
  name = "${var.project_name}-snowflake-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "snowflake_s3_policy" {
  name = "${var.project_name}-snowflake-s3-policy"
  role = aws_iam_role.snowflake_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.serp_upload_stage.arn,
          "${aws_s3_bucket.serp_upload_stage.arn}/*"
        ]
      }
    ]
  })
}

# IAM Role for Lambda Functions
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name = "${var.project_name}-lambda-permissions"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.serp_upload_stage.arn}/*",
          "${aws_s3_bucket.serp_hls_output.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.user_prefs.arn
      }
    ]
  })
}

# Lambda Function: DNA Mapper
resource "aws_lambda_function" "dna_mapper" {
  filename         = "dna_mapper.zip"
  function_name    = "${var.project_name}-dna-mapper-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.12"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  environment {
    variables = {
      SNOWFLAKE_ACCOUNT  = var.snowflake_account
      SNOWFLAKE_USERNAME = var.snowflake_username
      SNOWFLAKE_PASSWORD = var.snowflake_password
      S3_BUCKET_PAYLOADS = aws_s3_bucket.serp_hls_output.bucket
      ENVIRONMENT        = var.environment
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_basic_execution]
}

# Lambda Function: Renderer
resource "aws_lambda_function" "renderer" {
  filename         = "renderer.zip"
  function_name    = "${var.project_name}-renderer-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "handler.handler"
  runtime         = "nodejs20.x"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  environment {
    variables = {
      OPENAI_API_KEY     = var.openai_api_key
      S3_BUCKET_OUTPUT   = aws_s3_bucket.serp_hls_output.bucket
      CLOUDFRONT_DOMAIN  = aws_cloudfront_distribution.serp_hls_cf.domain_name
      ENVIRONMENT        = var.environment
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_basic_execution]
}

# API Gateway HTTP API v2
resource "aws_apigatewayv2_api" "serp_api" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"
  description   = "SERP Loop Radio API"

  cors_configuration {
    allow_credentials = false
    allow_headers     = ["content-type", "x-amz-date", "authorization", "x-api-key"]
    allow_methods     = ["*"]
    allow_origins     = ["*"]
    expose_headers    = ["date", "keep-alive"]
    max_age          = 86400
  }
}

resource "aws_apigatewayv2_stage" "serp_api_stage" {
  api_id      = aws_apigatewayv2_api.serp_api.id
  name        = var.environment
  auto_deploy = true
}

# API Gateway Integrations
resource "aws_apigatewayv2_integration" "dna_mapper_integration" {
  api_id             = aws_apigatewayv2_api.serp_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.dna_mapper.invoke_arn
}

resource "aws_apigatewayv2_integration" "renderer_integration" {
  api_id             = aws_apigatewayv2_api.serp_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.renderer.invoke_arn
}

# API Gateway Routes
resource "aws_apigatewayv2_route" "play_route" {
  api_id    = aws_apigatewayv2_api.serp_api.id
  route_key = "GET /play"
  target    = "integrations/${aws_apigatewayv2_integration.renderer_integration.id}"
}

resource "aws_apigatewayv2_route" "setup_route" {
  api_id    = aws_apigatewayv2_api.serp_api.id
  route_key = "POST /setup"
  target    = "integrations/${aws_apigatewayv2_integration.dna_mapper_integration.id}"
}

# Lambda Permissions for API Gateway
resource "aws_lambda_permission" "dna_mapper_api_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dna_mapper.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.serp_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "renderer_api_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.renderer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.serp_api.execution_arn}/*/*"
}

# Data source for current AWS account
data "aws_caller_identity" "current" {} 