import argparse
import sys
import os
from src.scraper_robust import CarScraper
from src.poster import PosterGenerator
from src.mock_data import MOCK_CAR_DATA, get_country_for_make

def main():
    parser = argparse.ArgumentParser(description="Auto-Poster Generator")
    parser.add_argument("--make", type=str, help="Car Make (e.g. Audi)")
    parser.add_argument("--model", type=str, help="Car Model (optional, will use first found)")
    parser.add_argument("--mock", action="store_true", help="Use mock data (skip scraping)")
    parser.add_argument("--openai-key", type=str, help="OpenAI API Key for background generation")

    args = parser.parse_args()

    if args.mock:
        print("Using Mock Data...")
        data = MOCK_CAR_DATA
    else:
        if not args.make:
            print("Error: --make is required unless --mock is used.")
            return

        print(f"Starting Scraper for {args.make}...")
        scraper = CarScraper()

        try:
            # 1. Search Make
            print(f"Searching for make: {args.make}...")
            make_url = scraper.search_make(args.make)
            print(f"Found make URL: {make_url}")

            # 2. Get Models
            print("Fetching models...")
            models = scraper.get_models(make_url)

            if not models:
                raise Exception("No models found for this make.")

            # If user specified model, search for it
            target_model = None
            if args.model:
                for m in models:
                    if args.model.lower() in m['name'].lower():
                        target_model = m
                        break
                if not target_model:
                    print(f"Model '{args.model}' not found. Using first available: {models[0]['name']}")
                    target_model = models[0]
            else:
                target_model = models[0]
                print(f"No model specified. Using first available: {target_model['name']}")

            # 3. Get Submodels (Mandatory for accurate specs/image)
            print(f"Fetching submodels for {target_model['name']}...")
            submodels = scraper.get_submodels(target_model['url'])

            if not submodels:
                 # Fallback to model page if no submodels found (unlikely)
                 target_submodel = target_model
                 target_submodel['navigation_url'] = target_model['url']
            else:
                 # Prefer the first one (usually the base/launch model)
                 target_submodel = submodels[0]
                 print(f"Using submodel: {target_submodel['name']}")

            # 4. Get Specs from the specific car page
            print(f"Fetching detailed specs for {target_submodel['name']}...")
            specs = scraper.get_specs(target_submodel['navigation_url'])

            # 5. Download car image
            image_path = None
            if specs.get('image_url'):
                print(f"Downloading car image...")
                os.makedirs('assets', exist_ok=True)
                image_path = f"assets/{args.make.lower().replace(' ', '_')}.jpg"
                scraper.download_image(specs['image_url'], image_path)

            # 5. Build data structure for poster
            import re
            raw_model_name = target_model.get('name', '')

            # Extract year range (e.g. 2016-2023) if present in the raw name
            year_match = re.search(r'(\d{4}\s*-\s*\d{4})', raw_model_name)
            year_display = year_match.group(1) if year_match else specs.get('year', 'N/A')

            # Clean the model name for the header
            clean_model = re.sub(r'\s*\(?\d{4}-\d{4}\)?', '', raw_model_name).strip()

            data = {
                'make': args.make,
                'model': clean_model,
                'year': year_display,
                'specs': {
                    'engine': specs.get('engine', '-'),
                    'power': specs.get('power', '-'),
                    'torque': specs.get('torque', '-'),
                    'weight': specs.get('weight', '-'),
                    '0-100': specs.get('0-100', '-'),
                    'top_speed': specs.get('top_speed', '-')
                },
                'country_code': get_country_for_make(args.make),
                'image_path': image_path
            }

            print("Scraping completed successfully!")

        except Exception as e:
            print(f"Scraping failed: {e}")
            print("Falling back to mock data for demonstration.")
            data = MOCK_CAR_DATA
        finally:
            scraper.close()

    # Generate Poster
    print("Generating Poster...")
    poster_gen = PosterGenerator(output_dir="output")
    output_path = poster_gen.create_poster(data)

    # Notify
    print(f"\n[OK] Done! Result saved to: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    main()
