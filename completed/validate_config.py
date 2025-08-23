#!/usr/bin/env python3
"""
Configuration validator for SERP Radio training system.
Validates rules, labels, and deployment readiness.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List
import argparse

def validate_yaml_rules(rules_path: str) -> List[str]:
    """Validate YAML rules configuration."""
    issues = []
    
    try:
        with open(rules_path) as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        return [f"Rules file not found: {rules_path}"]
    except yaml.YAMLError as e:
        return [f"Invalid YAML syntax: {e}"]
    
    # Check required structure
    if "rules" not in config:
        issues.append("Missing 'rules' section")
        return issues
    
    rules = config["rules"]
    if not isinstance(rules, list):
        issues.append("'rules' must be a list")
        return issues
    
    # Validate each rule
    has_default = False
    valid_labels = {"MOMENTUM_POS", "MOMENTUM_NEG", "VOLATILE_SPIKE", "NEUTRAL", "UNLABELED"}
    
    for i, rule in enumerate(rules):
        rule_prefix = f"Rule {i+1}"
        
        if "choose_label" not in rule:
            issues.append(f"{rule_prefix}: Missing 'choose_label'")
            continue
        
        label = rule["choose_label"]
        if label not in valid_labels:
            issues.append(f"{rule_prefix}: Invalid label '{label}'. Must be one of: {valid_labels}")
        
        # Check conditions
        conditions = rule.get("when", {})
        if not conditions:  # Default rule
            has_default = True
        else:
            for metric, threshold in conditions.items():
                if isinstance(threshold, str):
                    # Validate threshold syntax
                    valid_operators = [">=", "<=", ">", "<", "==", "="]
                    if not any(threshold.startswith(op) for op in valid_operators):
                        if metric != "mode":  # Mode can be a direct string
                            issues.append(f"{rule_prefix}: Invalid threshold format for {metric}: '{threshold}'")
    
    if not has_default:
        issues.append("No default rule found (rule with empty 'when' conditions)")
    
    return issues

def validate_motif_catalog(catalog_path: str) -> List[str]:
    """Validate motif catalog structure and labels."""
    issues = []
    
    try:
        with open(catalog_path) as f:
            catalog = json.load(f)
    except FileNotFoundError:
        return [f"Catalog file not found: {catalog_path}"]
    except json.JSONDecodeError as e:
        return [f"Invalid JSON in catalog: {e}"]
    
    # Check structure
    if "motifs" not in catalog:
        issues.append("Missing 'motifs' section")
        return issues
    
    motifs = catalog["motifs"]
    if not isinstance(motifs, list):
        issues.append("'motifs' must be a list")
        return issues
    
    # Count labels
    label_counts = {}
    total_motifs = len(motifs)
    
    for i, motif in enumerate(motifs):
        if "id" not in motif:
            issues.append(f"Motif {i}: Missing 'id' field")
        
        label = motif.get("label", "UNLABELED")
        label_counts[label] = label_counts.get(label, 0) + 1
    
    # Check label coverage
    labeled_count = sum(count for label, count in label_counts.items() if label != "UNLABELED")
    coverage = (labeled_count / total_motifs * 100) if total_motifs > 0 else 0
    
    if coverage < 5:
        issues.append(f"Very low training coverage: {coverage:.1f}% labeled")
    elif coverage < 20:
        issues.append(f"Low training coverage: {coverage:.1f}% labeled (consider adding more)")
    
    # Check for unbalanced labels
    for label, count in label_counts.items():
        if label != "UNLABELED" and count < 2:
            issues.append(f"Very few examples of '{label}' ({count} motifs)")
    
    return issues

def validate_deployment_readiness() -> Dict[str, Any]:
    """Check overall deployment readiness."""
    status = {
        "ready": True,
        "issues": [],
        "warnings": [],
        "recommendations": []
    }
    
    # Check required files
    required_files = {
        "config/metric_to_label.yaml": "Label rules configuration",
        "motifs_catalog.json": "Motif catalog with training data",
        "2025-08-03T174139Z.midi": "Baseline MIDI file"
    }
    
    for file_path, description in required_files.items():
        if not Path(file_path).exists():
            status["issues"].append(f"Missing {description}: {file_path}")
            status["ready"] = False
    
    # Validate configurations
    if Path("config/metric_to_label.yaml").exists():
        rule_issues = validate_yaml_rules("config/metric_to_label.yaml")
        status["issues"].extend(rule_issues)
        if rule_issues:
            status["ready"] = False
    
    if Path("motifs_catalog.json").exists():
        catalog_issues = validate_motif_catalog("motifs_catalog.json")
        status["issues"].extend(catalog_issues)
        
        # Separate warnings from blocking issues
        warning_keywords = ["low training coverage", "few examples"]
        for issue in catalog_issues:
            if any(keyword in issue.lower() for keyword in warning_keywords):
                status["warnings"].append(issue)
            else:
                status["ready"] = False
    
    # Add recommendations
    if status["ready"]:
        status["recommendations"] = [
            "Test the system with real tenant data before production deployment",
            "Set up monitoring for label decision logs in production",
            "Consider A/B testing trained vs. rule-based selection",
            "Plan for periodic retraining as more data becomes available"
        ]
    
    return status

def check_audio_setup() -> List[str]:
    """Check audio playback setup."""
    issues = []
    
    # Check for FluidSynth
    import subprocess
    try:
        result = subprocess.run(["fluidsynth", "--version"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            issues.append("FluidSynth not working properly")
    except FileNotFoundError:
        issues.append("FluidSynth not installed (recommended: brew install fluidsynth)")
    
    # Check for SoundFont
    soundfont_paths = [
        "GeneralUser.sf2",
        "/usr/share/sounds/sf2/GeneralUser.sf2", 
        "/usr/local/share/sounds/sf2/GeneralUser.sf2"
    ]
    
    has_soundfont = any(Path(p).exists() for p in soundfont_paths)
    if not has_soundfont:
        issues.append("No SoundFont found (download GeneralUser.sf2 for better audio quality)")
    
    return issues

def main():
    """CLI entry point for configuration validation."""
    parser = argparse.ArgumentParser(description="Validate SERP Radio configuration")
    parser.add_argument("--rules", default="config/metric_to_label.yaml",
                       help="Path to rules YAML file")
    parser.add_argument("--catalog", default="motifs_catalog.json",
                       help="Path to motif catalog JSON file")
    parser.add_argument("--check-audio", action="store_true",
                       help="Check audio playback setup")
    
    args = parser.parse_args()
    
    print("🔍 SERP Radio Configuration Validation")
    print("=" * 50)
    
    all_good = True
    
    # Validate rules
    print(f"\n📋 Validating Rules: {args.rules}")
    rule_issues = validate_yaml_rules(args.rules)
    if rule_issues:
        all_good = False
        for issue in rule_issues:
            print(f"   ❌ {issue}")
    else:
        print("   ✅ Rules configuration valid")
    
    # Validate catalog
    print(f"\n🎼 Validating Catalog: {args.catalog}")
    catalog_issues = validate_motif_catalog(args.catalog)
    if catalog_issues:
        for issue in catalog_issues:
            if "low" in issue.lower() or "few" in issue.lower():
                print(f"   ⚠️ {issue}")
            else:
                print(f"   ❌ {issue}")
                all_good = False
    else:
        print("   ✅ Motif catalog valid")
    
    # Check audio setup
    if args.check_audio:
        print(f"\n🎵 Checking Audio Setup")
        audio_issues = check_audio_setup()
        if audio_issues:
            for issue in audio_issues:
                print(f"   ⚠️ {issue}")
        else:
            print("   ✅ Audio setup ready")
    
    # Overall deployment readiness
    print(f"\n🚀 Deployment Readiness Check")
    status = validate_deployment_readiness()
    
    if status["ready"]:
        print("   ✅ System ready for deployment!")
    else:
        print("   ❌ System not ready for deployment")
        all_good = False
    
    # Show issues and warnings
    for issue in status["issues"]:
        print(f"   ❌ {issue}")
    
    for warning in status["warnings"]:
        print(f"   ⚠️ {warning}")
    
    # Show recommendations
    if status["recommendations"]:
        print(f"\n💡 Recommendations:")
        for rec in status["recommendations"]:
            print(f"   • {rec}")
    
    # Summary
    print(f"\n{'✅ Validation Complete!' if all_good else '❌ Issues Found'}")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    exit(main())