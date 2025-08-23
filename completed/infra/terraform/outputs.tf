output "snowflake_account" {
  description = "Snowflake account identifier"
  value       = var.snowflake_account
}

output "snowflake_database" {
  description = "Snowflake database name"
  value       = snowflake_database.serp_radio.name
}

output "snowflake_schema" {
  description = "Snowflake schema name"
  value       = snowflake_schema.market_share.name
}

output "snowflake_table" {
  description = "Snowflake table name"
  value       = snowflake_table.market_share_rank.name
}

output "lambda_dna_mapper_arn" {
  description = "ARN of the DNA Mapper Lambda function"
  value       = aws_lambda_function.dna_mapper.arn
}

output "lambda_renderer_arn" {
  description = "ARN of the Renderer Lambda function"
  value       = aws_lambda_function.renderer.arn
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.serp_hls_cf.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.serp_hls_cf.id
}

output "s3_upload_bucket" {
  description = "S3 bucket for CSV uploads"
  value       = aws_s3_bucket.serp_upload_stage.bucket
}

output "s3_hls_bucket" {
  description = "S3 bucket for HLS output"
  value       = aws_s3_bucket.serp_hls_output.bucket
}

output "dynamodb_table_name" {
  description = "DynamoDB table for user preferences"
  value       = aws_dynamodb_table.user_prefs.name
}

output "api_gateway_url" {
  description = "API Gateway base URL"
  value       = "${aws_apigatewayv2_api.serp_api.api_endpoint}/${aws_apigatewayv2_stage.serp_api_stage.name}"
}

output "api_gateway_play_endpoint" {
  description = "API Gateway play endpoint"
  value       = "${aws_apigatewayv2_api.serp_api.api_endpoint}/${aws_apigatewayv2_stage.serp_api_stage.name}/play"
}

output "api_gateway_setup_endpoint" {
  description = "API Gateway setup endpoint"
  value       = "${aws_apigatewayv2_api.serp_api.api_endpoint}/${aws_apigatewayv2_stage.serp_api_stage.name}/setup"
}

output "snowflake_pipe_arn" {
  description = "Snowflake pipe for auto-ingestion"
  value       = snowflake_pipe.serp_pipe.name
}

output "environment_variables" {
  description = "Environment variables for frontend configuration"
  value = {
    NEXT_PUBLIC_API_URL     = "${aws_apigatewayv2_api.serp_api.api_endpoint}/${aws_apigatewayv2_stage.serp_api_stage.name}"
    NEXT_PUBLIC_CF_DOMAIN   = aws_cloudfront_distribution.serp_hls_cf.domain_name
    DYNAMODB_TABLE_NAME     = aws_dynamodb_table.user_prefs.name
    S3_HLS_BUCKET          = aws_s3_bucket.serp_hls_output.bucket
  }
  sensitive = false
} 