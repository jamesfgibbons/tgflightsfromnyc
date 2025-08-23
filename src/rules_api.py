"""
YAML rules management API for SERP Radio.
"""

import logging
import os
import yaml
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from .models import SaveRulesRequest, SaveRulesResponse, SonifyRequest
from .storage import read_text_s3, put_bytes, ensure_tenant_prefix, StorageError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["rules"])

# Environment configuration
S3_BUCKET = os.getenv("S3_BUCKET", "serp-radio-artifacts")
RULES_S3 = os.getenv("RULES_S3", "s3://serp-radio-config/metric_to_label.yaml")


@router.get("/rules", response_class=PlainTextResponse)
async def get_rules(tenant: str = Query(..., description="Tenant identifier")):
    """
    Get current YAML rules for tenant.
    
    Args:
        tenant: Tenant identifier
    
    Returns:
        YAML rules as plain text
    """
    try:
        # Validate tenant
        if not tenant or not tenant.replace("-", "").replace("_", "").isalnum():
            raise HTTPException(400, "Invalid tenant identifier")
        
        # Try tenant-specific rules first
        tenant_rules_key = ensure_tenant_prefix(tenant, "config", "metric_to_label.yaml")
        tenant_rules_uri = f"s3://{S3_BUCKET}/{tenant_rules_key}"
        
        try:
            rules_text = read_text_s3(tenant_rules_uri)
            logger.info(f"Retrieved tenant-specific rules for {tenant}")
            return rules_text
        except StorageError:
            # Fallback to global rules
            if RULES_S3:
                try:
                    rules_text = read_text_s3(RULES_S3)
                    logger.info(f"Retrieved global rules for {tenant}")
                    return rules_text
                except StorageError:
                    pass
        
        # Ultimate fallback - default rules
        default_rules = get_default_rules()
        logger.info(f"Using default rules for {tenant}")
        return default_rules
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rules for tenant {tenant}: {e}")
        raise HTTPException(500, "Failed to retrieve rules")


@router.put("/rules", response_model=SaveRulesResponse)
async def save_rules(request: SaveRulesRequest):
    """
    Save YAML rules for tenant.
    
    Args:
        request: Rules save request
    
    Returns:
        Save confirmation with version key
    """
    try:
        # Validate YAML format
        try:
            yaml_data = yaml.safe_load(request.yaml_text)
            if not isinstance(yaml_data, dict):
                raise HTTPException(400, "YAML must be a dictionary")
        except yaml.YAMLError as e:
            raise HTTPException(400, f"Invalid YAML format: {e}")
        
        # Validate required structure
        if "rules" not in yaml_data:
            raise HTTPException(400, "YAML must contain 'rules' key")
        
        if not isinstance(yaml_data["rules"], list):
            raise HTTPException(400, "Rules must be a list")
        
        # Validate each rule
        for i, rule in enumerate(yaml_data["rules"]):
            if not isinstance(rule, dict):
                raise HTTPException(400, f"Rule {i} must be a dictionary")
            if "choose_label" not in rule:
                raise HTTPException(400, f"Rule {i} must have 'choose_label'")
        
        # Create versioned key
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        version_key = f"serp-radio-config/{timestamp}/tenant_{request.tenant}_metric_to_label.yaml"
        
        # Save versioned copy
        put_bytes(
            S3_BUCKET,
            version_key,
            request.yaml_text.encode("utf-8"),
            "application/x-yaml"
        )
        
        # Save as current tenant rules
        current_key = ensure_tenant_prefix(request.tenant, "config", "metric_to_label.yaml")
        put_bytes(
            S3_BUCKET,
            current_key,
            request.yaml_text.encode("utf-8"),
            "application/x-yaml"
        )
        
        logger.info(f"Saved rules for tenant {request.tenant}: {version_key}")
        
        return SaveRulesResponse(
            version_key=version_key,
            tenant=request.tenant,
            saved_at=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save rules for tenant {request.tenant}: {e}")
        raise HTTPException(500, "Failed to save rules")


@router.post("/preview")
async def preview_sonification(request: SonifyRequest):
    """
    Preview sonification with demo data (synchronous).
    
    Args:
        request: Sonification request (limited to demo mode)
    
    Returns:
        Presigned URLs for preview artifacts
    """
    # Force demo mode for preview
    if request.source != "demo":
        raise HTTPException(400, "Preview only supports demo mode")
    
    # Limit to small demo data
    if not request.override_metrics:
        request.override_metrics = {
            "ctr": 0.65,
            "impressions": 0.75, 
            "position": 0.8,
            "clicks": 0.7
        }
    
    try:
        from .sonify_service import create_sonification_service
        from .storage import get_presigned_url
        
        service = create_sonification_service(S3_BUCKET)
        
        # Generate unique preview ID
        preview_id = f"preview_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        input_key = ensure_tenant_prefix(request.tenant, "midi_input", "baseline.mid")
        output_base = ensure_tenant_prefix(request.tenant, "preview", preview_id)
        
        # Run synchronous sonification (small demo data only)
        result = service.run_sonification(request, input_key, output_base)
        
        # Generate presigned URLs
        urls = {}
        if result.get("midi_key"):
            urls["midi_url"] = get_presigned_url(S3_BUCKET, result["midi_key"], expires=1800, force_download=False)  # 30 min
        if result.get("mp3_key"):
            urls["mp3_url"] = get_presigned_url(S3_BUCKET, result["mp3_key"], expires=1800, force_download=False)
        if result.get("momentum_key"):
            urls["momentum_url"] = get_presigned_url(S3_BUCKET, result["momentum_key"], expires=1800)
        
        urls["label_summary"] = result.get("label_summary", {})
        
        logger.info(f"Preview generated for tenant {request.tenant}")
        return urls
        
    except Exception as e:
        logger.error(f"Preview failed for tenant {request.tenant}: {e}")
        raise HTTPException(500, f"Preview generation failed: {str(e)}")


def get_default_rules() -> str:
    """Get default YAML rules."""
    return """# Default SERP Radio metric-to-label mapping rules
version: "1.0"
description: "Default rules for mapping normalized metrics to musical labels"

rules:
  # High performance indicators
  - when:
      ctr: ">=0.7"
      position: ">=0.8" 
      clicks: ">=0.6"
    choose_label: "MOMENTUM_POS"
    description: "Strong positive momentum"

  # Poor performance indicators  
  - when:
      ctr: "<0.3"
      position: "<0.4"
    choose_label: "MOMENTUM_NEG"
    description: "Negative momentum"

  # High volatility
  - when:
      volatility_index: ">=0.6"
    choose_label: "VOLATILE_SPIKE"
    description: "High volatility period"

  # GSC high impressions special case
  - when:
      impressions: ">=0.8"
      mode: "gsc"
    choose_label: "VOLATILE_SPIKE"
    description: "GSC impression spike"

  # Default fallback
  - when: {}
    choose_label: "NEUTRAL"
    description: "Neutral/balanced metrics"
"""