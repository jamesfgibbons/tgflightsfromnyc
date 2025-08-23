import os

def main():
    # Orchestrates the Caribbean Kokomo pipeline end-to-end.
    os.system("python -m src.pipeline.fetch_offers_nyc_caribbean --days 14 --nonstop-only");
    os.system("python -m src.pipeline.build_visibility --days 14");
    os.system("python -m src.pipeline.openai_enrich --days 7");
    os.system("python -m src.pipeline.build_momentum --days 7");
    os.system("python -m src.pipeline.publish_catalog");

if __name__ == "__main__":
    main()
