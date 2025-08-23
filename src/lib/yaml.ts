/**
 * YAML utilities for SERP Radio Rules IDE.
 * Using a safe YAML parser for client-side validation.
 */

// In a real app, you'd install 'js-yaml' package
// For this example, we'll provide a minimal YAML parser interface
// npm install js-yaml @types/js-yaml

import * as yaml from 'js-yaml';

export interface YamlValidationResult {
  valid: boolean;
  error?: string;
  parsed?: any;
}

/**
 * Safely parse YAML text with validation.
 */
export function parseYaml(yamlText: string): YamlValidationResult {
  if (!yamlText.trim()) {
    return { valid: false, error: 'YAML content cannot be empty' };
  }
  
  // Check size limit (100KB)
  const sizeInBytes = new Blob([yamlText]).size;
  if (sizeInBytes > 100 * 1024) {
    return { 
      valid: false, 
      error: `YAML too large: ${Math.round(sizeInBytes / 1024)}KB (max 100KB)` 
    };
  }
  
  try {
    const parsed = yaml.load(yamlText, { 
      schema: yaml.SAFE_SCHEMA, // Only allow safe types
      json: true // Strict JSON compatibility
    });
    
    if (!parsed || typeof parsed !== 'object') {
      return { valid: false, error: 'YAML must be an object/dictionary' };
    }
    
    return { valid: true, parsed };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Invalid YAML syntax';
    return { valid: false, error: message };
  }
}

/**
 * Validate YAML structure for SERP Radio rules.
 */
export function validateRulesYaml(yamlText: string): YamlValidationResult {
  const parseResult = parseYaml(yamlText);
  if (!parseResult.valid) {
    return parseResult;
  }
  
  const rules = parseResult.parsed;
  
  // Check for required 'rules' key
  if (!rules.rules || !Array.isArray(rules.rules)) {
    return { 
      valid: false, 
      error: "YAML must contain a 'rules' array" 
    };
  }
  
  // Validate each rule
  for (let i = 0; i < rules.rules.length; i++) {
    const rule = rules.rules[i];
    
    if (!rule || typeof rule !== 'object') {
      return { 
        valid: false, 
        error: `Rule ${i + 1} must be an object` 
      };
    }
    
    if (!rule.choose_label || typeof rule.choose_label !== 'string') {
      return { 
        valid: false, 
        error: `Rule ${i + 1} must have a 'choose_label' string` 
      };
    }
    
    // Validate label values
    const validLabels = ['MOMENTUM_POS', 'MOMENTUM_NEG', 'VOLATILE_SPIKE', 'NEUTRAL'];
    if (!validLabels.includes(rule.choose_label)) {
      return {
        valid: false,
        error: `Rule ${i + 1}: invalid label '${rule.choose_label}'. Must be one of: ${validLabels.join(', ')}`
      };
    }
    
    // Validate 'when' conditions if present
    if (rule.when && typeof rule.when !== 'object') {
      return { 
        valid: false, 
        error: `Rule ${i + 1}: 'when' must be an object` 
      };
    }
    
    // Validate condition syntax
    if (rule.when) {
      for (const [metric, condition] of Object.entries(rule.when)) {
        if (typeof condition === 'string') {
          // Check for valid comparison operators
          const validOps = /^(>=|<=|>|<|=|!=)\d*\.?\d+$|^(gsc|serp)$/;
          if (typeof condition === 'string' && !validOps.test(condition) && !['gsc', 'serp'].includes(condition)) {
            return {
              valid: false,
              error: `Rule ${i + 1}: invalid condition '${condition}' for metric '${metric}'`
            };
          }
        }
      }
    }
  }
  
  return { valid: true, parsed: rules };
}

/**
 * Format YAML with consistent indentation.
 */
export function formatYaml(obj: any): string {
  try {
    return yaml.dump(obj, {
      indent: 2,
      lineWidth: 80,
      noRefs: true,
      sortKeys: false
    });
  } catch (error) {
    throw new Error(`Failed to format YAML: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Get default YAML template for rules.
 */
export function getDefaultRulesYaml(): string {
  return `# SERP Radio Metric-to-Label Mapping Rules
version: "1.0"
description: "Rules for mapping normalized metrics to musical labels"

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
`;
}

/**
 * Extract rule summary for display.
 */
export function getRuleSummary(rules: any): string[] {
  if (!rules?.rules || !Array.isArray(rules.rules)) {
    return ['No rules defined'];
  }
  
  const summary = rules.rules.map((rule: any, index: number) => {
    const conditions = rule.when ? Object.keys(rule.when).length : 0;
    const label = rule.choose_label || 'unknown';
    const desc = rule.description ? ` (${rule.description})` : '';
    
    if (conditions === 0) {
      return `${index + 1}. Default → ${label}${desc}`;
    } else {
      const condStr = conditions === 1 ? '1 condition' : `${conditions} conditions`;
      return `${index + 1}. ${condStr} → ${label}${desc}`;
    }
  });
  
  return summary;
}