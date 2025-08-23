# JSON Schema for OpenAI Structured Outputs
OFFER_JSON_SCHEMA = {
    "name": "flight_offers",
    "schema": {
        "type": "object",
        "properties": {
            "offers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["origin", "destination", "brand", "brand_code", "price", "currency", "nonstop", "fare_type", "departure_date", "notes", "approximate"],
                    "properties": {
                        "origin": {"type": "string", "description": "IATA code (e.g., JFK)"},
                        "destination": {"type": "string", "description": "IATA code (e.g., STT)"},
                        "brand": {"type": "string", "description": "Marketing carrier name (e.g., JetBlue)"},
                        "brand_code": {"type": "string", "description": "IATA code (e.g., B6)"},
                        "price": {"type": "number", "description": "Numeric fare"},
                        "currency": {"type": "string", "description": "ISO-4217 (e.g., USD)"},
                        "nonstop": {"type": "boolean", "default": True},
                        "fare_type": {"type": "string", "enum": ["base", "bundled", "unknown"], "default": "base"},
                        "departure_date": {"type": "string", "description": "YYYY-MM-DD"},
                        "notes": {"type": "string"},
                        "approximate": {"type": "boolean", "default": False}
                    },
                    "additionalProperties": False
                }
            }
        },
        "required": ["offers"],
        "additionalProperties": False
    },
    "strict": True
}