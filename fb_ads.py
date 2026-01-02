import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()
ZENROWS_API_KEY = os.getenv("ZENROWS_API_KEY")
if not ZENROWS_API_KEY:
    raise ValueError("ZENROWS_API_KEY missing from .env")

def get_facebook_ad_trends():
    products = {"men": [], "women": []}

    base_params = {
        "apikey": ZENROWS_API_KEY,
        "js_render": "true",
        "antibot": "true",
        "premium_proxy": "true",
        "original_status": "true",
        "wait": "5000",
        "window_width": "1920",
        "window_height": "1080",
    }

    # JS instructions to handle infinite scroll: scroll to bottom multiple times with waits
    scroll_instructions = [{"scroll_y": "100%"}, {"wait": 3000}] * 5  # Scroll 5 times to load more ads

    def fetch_category(base_url, query, gender):
        url = f"{base_url}&q={query.replace(' ', '+')}"
        params = base_params.copy()
        params["url"] = url
        params["js_instructions"] = json.dumps(scroll_instructions)
        try:
            print(f"Fetching Facebook Ad Library {gender.capitalize()} fashion ads...")
            resp = requests.get("https://api.zenrows.com/v1/", params=params, timeout=180)
            resp.raise_for_status()
            html = resp.text
            print(f"Response size: {len(html)} chars")

            # Save raw HTML for debugging and manual inspection
            raw_file = f"fb_ads_{gender}_raw.html"
            with open(raw_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Raw HTML saved: {raw_file}")

            soup = BeautifulSoup(html, "html.parser")

            # Find ad cards - Facebook uses dynamic classes, so this may need adjustment
            # Based on known structures: main container often has class starting with '_9c' or 'x1t2pt76'
            # Here, trying a broad selector; inspect saved HTML to refine
            ad_container = soup.find("div", class_=lambda c: c and ("_9cb_" in c or "x1t2pt76" in c))
            if not ad_container:
                print("No ad container found - check raw HTML and update selector")
                return []

            product_cards = ad_container.find_all("div", recursive=False)  # Child divs as ad cards

            print(f"Found {len(product_cards)} potential ad cards for {gender}")

            collected = []
            for card in product_cards:
                # Advertiser/Brand (often in span or div with specific class)
                brand_tag = card.find("span", class_=lambda c: c and "dgpf1xc5" in c) or \
                            card.find("div", class_=lambda c: c and "x1heor9g" in c)
                brand = brand_tag.get_text(strip=True) if brand_tag else "N/A"

                # Ad description/text
                desc_tag = card.find("div", class_=lambda c: c and "lrazzd5p" in c) or \
                           card.find("span", class_=lambda c: c and "x193iq5w" in c)
                description = desc_tag.get_text(strip=True) if desc_tag else "N/A"

                # Image
                img_tag = card.find("img")
                image = img_tag["src"] if img_tag and img_tag.has_attr("src") else ""

                # URL (See ad details or CTA link)
                url_tag = card.find("a", string=lambda t: t and "See ad details" in t) or \
                          card.find("a", class_=lambda c: c and "x1i10hfl" in c)
                url = url_tag["href"] if url_tag else ""
                if url and not url.startswith("http"):
                    url = "https://www.facebook.com" + url

                # Price - rarely in ads, so N/A or extract from text if possible
                price = "N/A"  # Could parse description for $ amounts if needed

                if brand != "N/A" or description != "N/A":
                    collected.append({
                        "brand": brand,
                        "gender": gender,
                        "name": description[:50] + "..." if description != "N/A" else "Ad Description",
                        "url": url or "N/A",
                        "price": price,
                        "image": image
                    })

            print(f"SUCCESS! Extracted {len(collected)} ads for {gender}")
            return collected[:15]  # Limit to top 15 "popular" ads (based on relevancy sort)

        except requests.exceptions.RequestException as e:
            print(f"ZenRows request failed for {gender}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error parsing {gender}: {e}")
            return []

    base_url = "https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped&search_type=keyword_unordered&media_type=all"
    products["men"] = fetch_category(base_url, "men fashion clothing", "men")
    products["women"] = fetch_category(base_url, "women fashion clothing", "women")

    return products

# ================ Pretty Console Output ================
if __name__ == "__main__":
    print("═" * 60)
    print("       Fashion Trend Bot | Facebook Ad Library Edition")
    print(f"       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 60)

    trends = get_facebook_ad_trends()

    total = len(trends["men"]) + len(trends["women"])
    print(f"Successfully collected {total} trending ad products! (Inferred popularity from ad reach/exposure)")
    print("Note: Facebook doesn't show exact reach, but top results are sorted by relevancy. Inspect raw HTML if parsing fails.\n")

    if trends["men"]:
        print("👔 MEN'S TOP 15 ADS")
        print("─" * 50)
        for i, p in enumerate(trends["men"], 1):
            print(f"{i:2}. {p['name']}")
            print(f"    Brand: {p['brand']}  |  Price: {p['price']}  |  Link: {p['url']}")
            print(f"    Image: {p['image'][:70]}{'...' if len(p['image']) > 70 else ''}\n")
    else:
        print("⚠ No men's ads found. Check raw HTML and update selectors.\n")

    if trends["women"]:
        print("👗 WOMEN'S TOP 15 ADS")
        print("─" * 50)
        for i, p in enumerate(trends["women"], 1):
            print(f"{i:2}. {p['name']}")
            print(f"    Brand: {p['brand']}  |  Price: {p['price']}  |  Link: {p['url']}")
            print(f"    Image: {p['image'][:70]}{'...' if len(p['image']) > 70 else ''}\n")
    else:
        print("⚠ No women's ads found. Check raw HTML and update selectors.\n")

    print("Finished. Adjust scroll count or selectors as needed for more/better results!")
    print("═" * 60)
