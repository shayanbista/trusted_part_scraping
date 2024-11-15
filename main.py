import os
from bs4 import BeautifulSoup
from scraper.trusted_part_scraper import TrustedPartScraper


def main():
    folder_path = "./html"
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, "page_content.html")

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    soup = BeautifulSoup(content, "html.parser")
    scraper = TrustedPartScraper(soup)
    scraper.parse()


if __name__ == "__main__":
    main()
