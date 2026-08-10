import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper


class Sakarya3Scraper(BaseScraper):

    BASE_URL = "https://www.s3osb.org.tr"
    LIST_URL = f"{BASE_URL}/firmalar/"

    CITY = "Sakarya"

    OSB_NAME = (
        "Sakarya 3. Organize Sanayi Bolgesi"
    )

    DEFAULT_ADDRESS = (
        "Sakarya 3. Organize Sanayi Bolgesi, Sakarya"
    )

    MIN_EXPECTED_COMPANIES = 20

    EMAIL_RE = re.compile(
        r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}",
        re.IGNORECASE,
    )

    def label_key(self, value):
        """
        Normalizes labels such as Telefon, E-posta, Web.
        """

        return re.sub(
            r"[^a-z0-9]+",
            "",
            self.ascii_tr(value).casefold(),
        )

    @staticmethod
    def profile_slug(url):
        """
        Extracts company slug from profile URL.
        """

        match = re.search(
            r"/firma-detay/([^/?#]+)/?",
            url,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).lower()

        return ""

    def make_company_id(
        self,
        name,
        url,
    ):
        """
        Generates a stable company ID.
        """

        slug = self.profile_slug(url)

        if not slug:
            slug = re.sub(
                r"[^A-Z0-9]+",
                "",
                self.ascii_tr(name).upper(),
            )[:40]

        return f"sakarya3osb:{slug}"

    def normalize_email(self, value):
        """
        Extracts valid-looking e-mail addresses.
        """

        emails = []

        for email in self.EMAIL_RE.findall(
            self.clean_text(value)
        ):

            email = (
                email.lower()
                .strip(
                    ".,;:()[]{}<>\"'"
                )
            )

            if email not in emails:
                emails.append(email)

        return " | ".join(emails)

    def normalize_phone(self, value):
        """
        Cleans phone values.
        """

        value = self.clean_text(value)

        if not value:
            return ""

        phones = []

        for raw in re.split(
            r"[\n|;]+",
            value,
        ):

            raw = self.clean_text(raw)

            digit_count = len(
                re.sub(
                    r"\D",
                    "",
                    raw,
                )
            )

            if (
                digit_count >= 7
                and raw not in phones
            ):
                phones.append(raw)

        return " | ".join(phones)

    def normalize_website(
        self,
        value,
        base="",
    ):
        """
        Normalizes company website URLs.
        """

        value = self.clean_text(value)

        if not value:
            return ""

        if "@" in value:
            return ""

        match = re.search(
            r"(?:https?://|www\.)[^\s,;]+",
            value,
            re.IGNORECASE,
        )

        if match:
            value = match.group(0)

        if value.startswith(
            ("/", "./", "../")
        ):
            value = urljoin(
                base,
                value,
            )

        if not re.match(
            r"^https?://",
            value,
            re.IGNORECASE,
        ):
            value = (
                "http://"
                + value.lstrip("/")
            )

        parsed = urlparse(value)

        if not parsed.netloc:
            return ""

        osb_domain = urlparse(
            self.BASE_URL
        ).netloc.lower()

        current_domain = (
            parsed.netloc
            .lower()
            .removeprefix("www.")
        )

        osb_domain = osb_domain.removeprefix(
            "www."
        )

        if current_domain == osb_domain:
            return ""

        return value.rstrip(
            "/.,; "
        )

    def collect_company_links(self):
        """
        Collects company profile links
        from the Sakarya 3 OSB company list.
        """

        print(
            f"Opening company list: "
            f"{self.LIST_URL}"
        )

        html, final_url = self.get_html(
            self.LIST_URL
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        companies = {}

        for link in soup.select(
            'a[href*="/firma-detay/"]'
        ):

            url = urljoin(
                final_url,
                link.get(
                    "href",
                    "",
                ),
            )

            slug = self.profile_slug(url)

            title_element = (
                link.find("h4")
                or link.find("h5")
                or link
            )

            name = self.ascii_tr(
                title_element.get_text(
                    " ",
                    strip=True,
                )
            )

            # Remove unwanted website text
            name = re.sub(
                r"(?i)^continue reading\s+",
                "",
                name,
            ).strip()

            if slug and name:

                companies[slug] = {
                    "company_name": name,
                    "profile_url": url,
                }

        result = sorted(
            companies.values(),
            key=lambda item:
                item["company_name"],
        )

        print(
            f"Company profiles found: "
            f"{len(result)}"
        )

        if (
            len(result)
            < self.MIN_EXPECTED_COMPANIES
        ):
            raise RuntimeError(
                "Unexpectedly low company count."
            )

        return result

    def detail_list_fields(
        self,
        soup,
    ):
        """
        Reads structured information
        from the company detail box.
        """

        result = {}

        for item in soup.select(
            ".ttm-pf-detailbox-list > li"
        ):

            key_element = item.select_one(
                ".ttm-pf-data-title"
            )

            value_element = item.select_one(
                ".ttm-pf-data-details"
            )

            if not (
                key_element
                and value_element
            ):
                continue

            key = self.label_key(
                key_element.text
            )

            value = self.clean_text(
                value_element.text
            )

            if key and value:

                result.setdefault(
                    key,
                    [],
                ).append(value)

        return result

    def contact_fields(
        self,
        soup,
    ):
        """
        Reads contact information
        from the detail page.
        """

        result = {}

        contact_box = (
            soup.select_one(
                ".contact_class"
            )
            or soup.select_one(
                ".contact-info"
            )
        )

        if not contact_box:
            return result

        for heading in contact_box.select(
            "h4"
        ):

            sibling = (
                heading
                .find_next_sibling()
            )

            while (
                sibling
                and getattr(
                    sibling,
                    "name",
                    None,
                )
                not in (
                    "h4",
                    "p",
                )
            ):
                sibling = (
                    sibling
                    .find_next_sibling()
                )

            if (
                sibling
                and sibling.name == "p"
            ):

                key = self.label_key(
                    heading.text
                )

                value = self.clean_text(
                    sibling.text
                )

                if key and value:
                    result.setdefault(
                        key,
                        [],
                    ).append(value)

        return result

   
    def values_for(
        data,
        prefixes,
    ):
        """
        Returns values whose normalized label
        starts with one of the supplied prefixes.
        """

        result = []

        for key, values in data.items():

            if any(
                key.startswith(prefix)
                for prefix in prefixes
            ):
                result.extend(values)

        return result

    def parse_detail(
        self,
        html,
        item,
        url,
    ):
        """
        Parses a company detail page.
        """

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        title = soup.select_one(
            ".page-title-heading h2, "
            ".ttm-service-description h4"
        )

        company_name = self.ascii_tr(
            title.text
            if title
            else item["company_name"]
        )

        company_name = re.sub(
            r"(?i)^continue reading\s+",
            "",
            company_name,
        ).strip()

        info = self.detail_list_fields(
            soup
        )

        contact = self.contact_fields(
            soup
        )

        sector_values = self.values_for(
            info,
            (
                "faaliyet",
                "sektor",
                "uretim",
                "yatirimkonusu",
            ),
        )

        sector = (
            self.ascii_tr(
                sector_values[0]
            )
            if sector_values
            else ""
        )

        address_values = self.values_for(
            contact,
            ("adres",),
        )

        address = (
            self.ascii_tr(
                address_values[0]
            )
            if address_values
            else self.DEFAULT_ADDRESS
        )

        phone_values = self.values_for(
            contact,
            (
                "telefon",
                "tel",
            ),
        )

        phone = " | ".join(
            filter(
                None,
                (
                    self.normalize_phone(
                        value
                    )
                    for value
                    in phone_values
                ),
            )
        )

        fax_values = self.values_for(
            contact,
            (
                "faks",
                "fax",
                "gsm",
            ),
        )

        fax = " | ".join(
            filter(
                None,
                (
                    self.normalize_phone(
                        value
                    )
                    for value
                    in fax_values
                ),
            )
        )

        email_values = self.values_for(
            contact,
            (
                "mail",
                "email",
                "eposta",
                "epostaadresi",
            ),
        )

        email = self.normalize_email(
            " ".join(
                email_values
            )
        )

        website = ""

        website_values = self.values_for(
            info,
            (
                "web",
                "website",
                "internet",
            ),
        )

        for value in website_values:

            website = (
                self.normalize_website(
                    value,
                    url,
                )
            )

            if website:
                break

        return {
            "city": self.CITY,
            "osb_name": self.OSB_NAME,
            "sector": sector,
            "company_name":
                company_name,
            "address": address,
            "phone": phone,
            "fax": fax,
            "website": website,
            "email": email,
            "activity_subject":
                sector,
            "profile_url": url,
            "company_id":
                self.make_company_id(
                    company_name,
                    url,
                ),
        }

    def scrape(self):
        """
        Runs the Sakarya 3 scraper.
        """

        links = (
            self.collect_company_links()
        )

        records = []

        total = len(links)

        for index, item in enumerate(
            links,
            start=1,
        ):

            print(
                f"[{index}/{total}] "
                f"{item['company_name']}"
            )

            try:

                html, final_url = (
                    self.get_html(
                        item["profile_url"]
                    )
                )

                record = self.parse_detail(
                    html,
                    item,
                    final_url,
                )

                records.append(record)

                print(
                    "OK "
                    f"email="
                    f"{bool(record['email'])} "
                    f"website="
                    f"{bool(record['website'])}"
                )

            except Exception as exc:

                print(
                    "ERROR:",
                    type(exc).__name__,
                    exc,
                )

            self.wait_between_requests()

        unique_records = {
            record["company_id"]:
                record
            for record
            in records
        }

        records = list(
            unique_records.values()
        )

        print(
            f"\nParsed companies: "
            f"{len(records)}"
        )

        return records