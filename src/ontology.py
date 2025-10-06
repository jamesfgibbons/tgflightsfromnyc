"""Destination Ontology Loader

Loads config/destination_ontology.yaml and provides helpers to look up
recommended palettes and tags for cities/airports.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@lru_cache(maxsize=1)
def _load_ontology() -> Dict[str, Any]:
    path = os.getenv("DESTINATION_ONTOLOGY_PATH", "config/destination_ontology.yaml")
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
            return data
    except FileNotFoundError:
        return {"destinations": {}, "aliases": {}}


def get_palette_for_destination(code_or_city: str) -> Optional[str]:
    data = _load_ontology()
    destinations: Dict[str, Dict[str, Any]] = data.get("destinations", {})
    aliases: Dict[str, str] = data.get("aliases", {})

    key = (code_or_city or "").strip()
    if not key:
        return None

    key_up = key.upper()
    if key_up in destinations:
        return destinations[key_up].get("default_palette")

    # Try alias by case-sensitive city name
    alias = aliases.get(key) or aliases.get(key.title())
    if alias and alias.upper() in destinations:
        return destinations[alias.upper()].get("default_palette")
    return None


def get_tags_for_destination(code_or_city: str) -> list[str]:
    data = _load_ontology()
    destinations: Dict[str, Dict[str, Any]] = data.get("destinations", {})
    aliases: Dict[str, str] = data.get("aliases", {})

    key = (code_or_city or "").strip()
    if not key:
        return []
    key_up = key.upper()
    if key_up in destinations:
        return list(destinations[key_up].get("tags") or [])
    alias = aliases.get(key) or aliases.get(key.title())
    if alias and alias.upper() in destinations:
        return list(destinations[alias.upper()].get("tags") or [])
    return []

