# 🚀 SERP Radio - Deployment Guide

## Overview

Deploy the SERP Radio production FastAPI backend with complete sonification capabilities, supporting both staging and production environments.

> **📌 Note**: For a simpler deployment using Supabase Storage instead of AWS S3, see [README_DEPLOY_SUPABASE.md](./README_DEPLOY_SUPABASE.md)

## 🏗️ Staging Environment

### AWS Resources (Staging)
- **Private S3 Bucket**: `serp-radio-staging-artifacts`
- **Public S3 Bucket**: `serp-radio-staging-public`
- **CDN Domain**: `d1abc123def456.cloudfront.net`
- **KMS Key**: `arn:aws:kms:us-east-1:123456789012:key/abcd1234-5678-9012-efgh-123456789012`

### Environment Variables (Staging)
```bash
# Core Configuration
APP_VERSION=1.0.0
PORT=8080
AWS_REGION=us-east-1

# S3 Storage
S3_BUCKET=serp-radio-staging-artifacts
S3_PUBLIC_BUCKET=serp-radio-staging-public
PUBLIC_CDN_DOMAIN=d1abc123def456.cloudfront.net

# Optional
ADMIN_SECRET=your_admin_secret_here
```

## 📋 Prerequisites

1. **Lovable Account** with Python/FastAPI support or AWS deployment environment
2. **AWS Account** with S3 access for artifact storage
3. **Optional:** Snowflake account for GSC data integration

## 🔧 Setup Instructions

### Step 1: Environment Configuration

Copy the environment template and configure your values:

```bash
cp .env.example .env
```

**Required Variables:**
```bash
# AWS (Required for S3 storage)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET=your-serp-radio-bucket

# CORS (Update with your Lovable URL)
CORS_ORIGINS=https://your-project.lovable.dev
```

**Optional Variables:**
```bash
# Snowflake (for real GSC data)
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_ACCOUNT=your-account.region

# Audio Rendering (disabled by default on Lovable)
RENDER_MP3=0
```

### Step 2: Lovable Deployment

1. **Create New Lovable Project**
   - Choose "Python FastAPI" template
   - Upload your codebase files

2. **Configure Environment Variables**
   - In Lovable dashboard → Settings → Environment Variables
   - Add all variables from your `.env` file
   - **IMPORTANT:** Do not expose secrets in client-side code

3. **Set Start Command**
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}
   ```

4. **Deploy**
   - Lovable will automatically install dependencies from `requirements.txt`
   - Backend will be available at your Lovable URL + API endpoints

### Step 3: Verify Deployment

Test your deployment:

```bash
# Health check
curl https://your-project.lovable.dev/health

# API documentation
open https://your-project.lovable.dev/docs
```

## 📡 API Endpoints

### Core Endpoints
- `POST /api/sonify` - Create sonification job
- `GET /api/jobs/{id}` - Get job status and download URLs
- `POST /api/upload-csv` - Upload CSV datasets
- `GET /health` - Health check

### Rules Management  
- `GET /api/rules?tenant=acme` - Get YAML rules
- `PUT /api/rules` - Save custom rules
- `POST /api/preview` - Preview sonification

### Documentation
- `/docs` - Interactive API documentation (Swagger)
- `/redoc` - ReDoc documentation

## 🔒 Security Considerations

### Environment Variables
- **Never expose AWS credentials to frontend**
- Use Lovable's secure environment variable storage
- Rotate API keys regularly

### CORS Configuration
```bash
# Update CORS_ORIGINS with your exact domains
CORS_ORIGINS=https://your-project.lovable.dev,https://your-domain.com
```

### File Uploads
- CSV uploads limited to 10MB
- Tenant isolation enforced on all S3 operations
- Input validation on all file operations

## 🎵 Usage Examples

### Basic Sonification
```javascript
// Frontend JavaScript example
const response = await fetch('/api/sonify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    tenant: 'my-company',
    source: 'demo',
    use_training: true,
    momentum: true,
    override_metrics: {
      ctr: 0.75,
      impressions: 0.8,
      position: 0.9,
      clicks: 0.7
    }
  })
});

const { job_id } = await response.json();

// Poll for completion
const checkStatus = async () => {
  const status = await fetch(`/api/jobs/${job_id}`).then(r => r.json());
  
  if (status.status === 'done') {
    console.log('MIDI URL:', status.midi_url);
    console.log('MP3 URL:', status.mp3_url);  // If enabled
    console.log('Labels used:', status.label_summary);
  }
};
```

### Upload CSV Data
```javascript
const formData = new FormData();
formData.append('file', csvFile);

const response = await fetch('/api/upload-csv?tenant=my-company', {
  method: 'POST',
  body: formData
});

const { dataset_id, inferred_schema } = await response.json();
```

## 🏗️ Architecture

```
Frontend (Lovable) ←→ FastAPI Backend (Lovable) ←→ S3 Storage (AWS)
                           ↓
                    Background Jobs (FastAPI)
                           ↓
                    Domain Logic (Python modules)
                           ↓
                    MIDI/MP3 Output (S3)
```

## 📈 Monitoring & Logs

### Health Monitoring
```bash
# Check service health
curl https://your-project.lovable.dev/health
```

### Structured Logging
All API requests and processing steps are logged in JSON format:
```json
{"timestamp": "2024-01-15T10:30:00Z", "level": "INFO", "message": "Sonification job created: abc123 for tenant my-company"}
```

### Job Status Tracking
- Jobs persist in memory (PoC) or DynamoDB (production)
- Background processing with FastAPI BackgroundTasks
- Presigned S3 URLs for secure artifact access

## 🚨 Troubleshooting

### Common Issues

**1. CORS Errors**
```bash
# Update CORS_ORIGINS environment variable
CORS_ORIGINS=https://your-actual-lovable-url.lovable.dev
```

**2. S3 Access Denied**
```bash
# Verify AWS credentials and bucket permissions
AWS_ACCESS_KEY_ID=correct-access-key
S3_BUCKET=accessible-bucket-name
```

**3. Module Import Errors**
```bash
# Ensure all dependencies in requirements.txt
# Check Python path configuration
```

**4. Audio Rendering Issues**
```bash
# Disable MP3 rendering on Lovable (binary limitations)
RENDER_MP3=0
```

### Debug Mode
Enable debug logging:
```bash
# Add to environment variables
LOG_LEVEL=DEBUG
```

## 📞 Support

- **API Documentation:** `/docs` on your deployment
- **Health Status:** `/health` endpoint
- **GitHub Issues:** [Project repository](https://github.com/your-repo)

## 🔄 Updates and Maintenance

### Updating Rules
```bash
# Update sonification rules without redeployment
PUT /api/rules
{
  "tenant": "my-company",
  "yaml_text": "rules:\n  - when: {ctr: '>=0.8'}\n    choose_label: 'HIGH_PERFORMANCE'"
}
```

### S3 Artifact Cleanup
- Presigned URLs expire after 1 hour (configurable)
- Implement automated S3 lifecycle policies
- Monitor storage costs and usage

---

**🎉 Your SERP Radio backend is now live on Lovable with enterprise-grade sonification capabilities!**