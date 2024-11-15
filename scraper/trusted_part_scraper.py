import time
import sys
import os

import re

from scrapingbee import ScrapingBeeClient
from bs4 import BeautifulSoup
from utils.button_utils import extract_button_info

import json


class TrustedPartScraper:
    def __init__(self, soup):
        self.soup = soup

    def parse(self):
        scraped_data = {}

        title, model, stock_availability = self.scrape_title()

        scraped_data["mfg"] = title
        scraped_data["mpn"] = model
        scraped_data["part_status"] = stock_availability

        categories, description = self.scrape_categories()

        scraped_data["categories"] = categories
        scraped_data["description"] = description

        stock_and_price_data = self.scrape_stock_and_price()
        if stock_and_price_data:
            scraped_data["stock_and_price"] = stock_and_price_data

        product_informations = self.scrape_product_informations()
        scraped_data["product_information"] = product_informations

        similar_parts = self.scrape_similar_parts_serial_number()
        scraped_data["similar_parts"] = similar_parts

        long_desc = self.scrape_descriptions()
        scraped_data["long_desc"] = long_desc

        referenced_names = self.scrape_referenced_names()
        scraped_data["referenced_names"] = referenced_names

        with open("file.json", "w") as file:
            json.dump(scraped_data, file)

        print("scraped data", scraped_data)

    def scrape_title(self):
        title_tag = self.soup.find("h1")
        stock_availability = self.soup.find(
            "div",
            class_="rounded-sm font-bold text-lg px-3 py-1.5 text-success-900 bg-success-200 whitespace-nowrap",
        )
        stock_availability = (
            stock_availability.text.strip() if stock_availability else None
        )
        if title_tag:
            span_tag = title_tag.find("span")
            if span_tag:
                product_model = span_tag.text.strip()
                title_text = title_tag.text.replace(product_model, "").strip()
                return title_text, product_model, stock_availability
            else:
                title_text = title_tag.text.strip()
                return title_text, None, stock_availability
        else:
            return None, None, stock_availability

    def scrape_categories(self):
        category_div = self.soup.find("div", class_="flex flex-col gap-2")

        if not category_div:
            return None

        description_div = self.soup.find("div", class_="lg:group-[.is-sticky]:hidden")

        description = description_div.text.strip() if description_div else None

        categories = []
        category_anchors = category_div.find_all("a")

        for anchor in category_anchors:
            category_name = anchor.text.strip()
            category_url = anchor.get("href")
            categories.append({"category_name": category_name})

        return categories, description

    def scrape_product_title(self):

        product_info = None
        a_tag = self.soup.find("a", class_="block mb-4")
        if not a_tag:
            return product_info
        product_info = {}
        product_info["product_title"] = a_tag["title"] if a_tag else None
        product_info["product_href"] = a_tag["href"] if a_tag else None
        return product_info

    def scrape_risks(self):
        risks = None
        buttons = self.soup.find_all("button", class_="flex items-stretch")
        if buttons:
            risks = {}
            lifecycle_button, supplychain_button = buttons[:2]

            lifecycle_risk, risk_level = extract_button_info(lifecycle_button)
            supplychain_risk, supplychain_risk_level = extract_button_info(
                supplychain_button
            )

            risks["lifecycle_risk_name"] = lifecycle_risk
            risks["risk_level"] = risk_level
            risks["supplychain_risk_name"] = supplychain_risk
            risks["supplychain_risk_level"] = supplychain_risk_level
            return risks
        return risks

    def scrape_stock_and_price(self):

        stock_table = self.soup.find("table", {"id": "ExactMatchesTable"})
        stock_table_body = stock_table.find("tbody")
        table_rows = stock_table_body.find_all("tr")

        thead = stock_table.find("thead")
        if thead:
            headers = [header.get_text(strip=True) for header in thead.find_all("th")]
            if headers:
                headers.pop(-1)

        results = []

        for row in table_rows:
            data_dist = row.get("data-dist")
            data_cur = row.get("data-cur")
            data_stock = row.get("data-stock-qty")
            data_mfr = row.get("data-mfr")

            _data = {
                "data_dist": data_dist,
                "data_cur": data_cur,
                "data_stock": data_stock,
                "data_mfr": data_mfr,
                "quantity_price": [],
            }

            price_section = row.find("td", class_="text-nowrap")
            if price_section:
                sections = price_section.find_all("section", class_="flex py-0.5")
                for section in sections:
                    spans = section.find_all("span")
                    if len(spans) >= 2:
                        quantity = spans[0].get_text(strip=True) or None
                        price = spans[-1].get_text(strip=True) or None
                        if (quantity, price) not in _data["quantity_price"]:
                            _data["quantity_price"].append((quantity, price))

            data_cells = row.find_all("td")
            for index, cell in enumerate(data_cells):
                buttons = cell.find_all("button")
                for button in buttons:
                    button.extract()

                link = cell.find("a", class_="flex justify-center items-start")

                if link:
                    _data["product_url"] = link.get("href") or None
                    _data["img_src"] = (
                        link.find("img")["src"] if link.find("img") else None
                    )
                    _data["product_name"] = link.get("title") or None

                cell_data = cell.get_text(strip=True) or None

                if index < len(headers):
                    column_name = headers[index]
                    if column_name not in ["Datasheet", "Pricing"]:
                        _data[column_name] = cell_data

            _pkg_moq = _data.get("Pkg (MOQ)")

            if _pkg_moq:

                match = re.match(r"([A-Za-z\s]+)\((\d+)\)", _pkg_moq)

                if match:
                    pkg = match.group(1).strip()
                    moq = int(match.group(2))
                else:
                    pkg = _pkg_moq.strip()
                    moq = None
            else:
                pkg, moq = None, None

            selected_data = {
                "data_dist": _data.get("data_dist"),
                "data_cur": _data.get("data_cur"),
                "data_stock": _data.get("data_stock"),
                "data_mfr": _data.get("data_stock"),
                "sku": _data.get("Distributor Part #"),
                "packaging": pkg,
                "moq": moq,
                "seller_url": _data.get("product_url"),
                "seller_image": _data.get("img_src"),
                "seller_name": _data.get("product_name"),
                "aviliable_qty": _data.get("data_stock"),
                "prices": _data.get("quantity_price"),
                "purchase_url": _data.get("product_url"),
            }

            results.append(selected_data)

        if not results:
            return None

        return results

    def scrape_product_informations(self):
        specs_data = None
        specs_container = self.soup.find("div", id="product-specs")
        if specs_container:
            specs_data = {}
            for term, description in zip(
                specs_container.find_all("dt"), specs_container.find_all("dd")
            ):
                spec_name = term.get_text(strip=True)
                spec_value = description.get_text(strip=True)
                specs_data[spec_name] = spec_value
        return specs_data

    def scrape_similar_parts(self):
        similar_parts_data = {}

        similar_parts_table = self.soup.find("table", id="SimilarPartsTable")
        if not similar_parts_table:
            return similar_parts_data

        headers = []
        header_row = similar_parts_table.find("tr")

        if header_row:
            headers = [
                header.get_text(strip=True) for header in header_row.find_all("td")[1:]
            ]

        products_data = []
        rows = similar_parts_table.find_all("tr")

        if len(rows) > 1:
            product_columns = rows[1].find_all("td")[1:]

            for product in product_columns:
                product_info = {}

                title_tag = product.find("a", href=True)
                product_info["Product_Link"] = title_tag["href"] if title_tag else None

                stock_tag = product.find("span", class_="text-success")
                product_info["Stock"] = (
                    stock_tag.get_text(strip=True) if stock_tag else None
                )

                for spec_row in rows[2:]:
                    spec_name_cell = spec_row.find("td", class_="!text-right")
                    spec_name = (
                        spec_name_cell.get_text(strip=True) if spec_name_cell else None
                    )

                    spec_value_cell = (
                        spec_row.find_all("td")[product_columns.index(product) + 1]
                        if len(spec_row.find_all("td"))
                        > (product_columns.index(product) + 1)
                        else None
                    )

                    spec_value = (
                        spec_value_cell.get_text(strip=True)
                        if spec_value_cell
                        else None
                    )

                    if spec_name:
                        product_info[spec_name] = spec_value

                products_data.append(product_info)

        similar_parts_data["similar_products"] = products_data
        return similar_parts_data

    def scrape_similar_parts_serial_number(self):
        similar_parts_table = self.soup.find("table", id="SimilarPartsTable")

        if not similar_parts_table:
            return None

        part_divs = similar_parts_table.find_all(
            "div", class_="flex flex-col items-center justify-center p-1"
        )

        if not part_divs:
            return None

        part_names = []

        for div in part_divs:
            a_tags = div.find_all("a")
            if a_tags and len(a_tags) > 1:
                part_number = a_tags[1].get_text(strip=True)
                if part_number:
                    part_names.append(part_number)

        if not part_names:
            return None

        return part_names

    def scrape_descriptions(self):
        li_elements = self.soup.select("section.part-detail-section ul.panel-body li")
        if not li_elements:
            return None

        long_desc = [li.get_text(strip=True) for li in li_elements]

        if not long_desc:
            return None

        return " ".join(long_desc)

    def scrape_referenced_names(self):
        div_elements = self.soup.select("div.panel.py-4.px-8 div")
        if not div_elements:
            return None

        referenced_texts = [div.get_text(strip=True) for div in div_elements]

        if not referenced_texts:
            return None

        return referenced_texts
