from scrapers.sakarya3 import Sakarya3Scraper


def main():
    print("\nOSB Company Scraper")
    print("===================\n")

    scraper = Sakarya3Scraper()
    records = scraper.scrape()

    print(f"\nToplam firma: {len(records)}")


if __name__ == "__main__":
    main()