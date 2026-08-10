

"""
OSB Company Scraper

"""

from __future__ import annotations

import csv
import html as html_lib
import os
import random
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError



BASE_URL = "https://www.s3osb.org.tr"
LIST_URL = f"{BASE_URL}/firmalar/"

CITY = "Sakarya"
OSB_NAME = "Sakarya 3. Organize Sanayi Bolgesi"
DEFAULT_ADDRESS = "Sakarya 3. Organize Sanayi Bolgesi, Sakarya"

TAB_NAME = "Sakarya_3_OSB"

REQUEST_TIMEOUT = 40
MIN_EXPECTED_COMPANIES = 20

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)

SHEET_HEADER = [
    "city",
    "osb_name",
    "sector",
    "company_name",
    "address",
    "phone",
    "fax",
    "website",
    "email",
    "activity_subject",
    "profile_url",
    "company_id",
]

TURKISH_TRANSLATION = str.maketrans(
    "çğıöşüÇĞİÖŞÜ",
    "cgiosuCGIOSU",
)



def clean_text(value: Any) -> str:
    """
    Remove unnecessary whitespace and HTML entities.
    """

    text = "" if value is None else str(value)

    text = (
        html_lib.unescape(text)
        .replace("\xa0", " ")
        .replace("\u00ad", "")
    )

    return re.sub(r"\s+", " ", text).strip(" -|\t\r\n")


def ascii_tr(value: str) -> str:
    """
    Convert Turkish characters to ASCII characters.
    """

    return clean_text(value).translate(TURKISH_TRANSLATION)


def label_key(value: str) -> str:
    """
    Normalize HTML labels for easier comparison.
    """

    return re.sub(
        r"[^a-z0-9]+",
        "",
        ascii_tr(value).casefold(),
    )


def profile_slug(url: str) -> str:
    """
    Extract company slug from profile URL.
    """

    match = re.search(
        r"/firma-detay/([^/?#]+)/?",
        url,
        re.IGNORECASE,
    )

    return match.group(1).lower() if match else ""


def make_company_id(name: str, url: str) -> str:
    """
    Create a stable identifier for each company.
    """

    slug = profile_slug(url)

    if not slug:
        slug = re.sub(
            r"[^A-Z0-9]+",
            "",
            ascii_tr(name).upper(),
        )[:40]

    return f"sakarya3osb:{slug}"


def unique_join(values) -> str:
    """
    Combine unique non-empty values.
    """

    result = []

    for value in values:

        value = clean_text(value)

        if value and value not in result:
            result.append(value)

    return " | ".join(result)


def normalize_phone(value: str) -> str:
    """
    Clean phone numbers.
    """

    value = clean_text(value)

    if not value:
        return ""

    phones = []

    for raw in re.split(r"[\n|;]+", value):

        raw = clean_text(raw)

        digit_count = len(
            re.sub(r"\D", "", raw)
        )

        if digit_count >= 7 and raw not in phones:
            phones.append(raw)

    return " | ".join(phones)


EMAIL_RE = re.compile(
    r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}",
    re.IGNORECASE,
)


def normalize_email(value: str) -> str:
    """
    Extract and normalize e-mail addresses.
    """

    emails = []

    for email in EMAIL_RE.findall(
        clean_text(value)
    ):

        email = (
            email.lower()
            .strip(".,;:()[]{}<>\"'")
        )

        if email not in emails:
            emails.append(email)

    return " | ".join(emails)


def normalize_website(
    value: str,
    base: str = "",
) -> str:

    """
    Normalize website URLs.
    """

    value = clean_text(value)

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
        value = urljoin(base, value)

    if not re.match(
        r"^https?://",
        value,
        re.IGNORECASE,
    ):
        value = "http://" + value.lstrip("/")

    parsed = urlparse(value)

    if not parsed.netloc:
        return ""

    osb_domain = urlparse(
        BASE_URL
    ).netloc

    current_domain = (
        parsed.netloc
        .lower()
        .removeprefix("www.")
    )

    if current_domain == osb_domain:
        return ""

    return value.rstrip("/.,; ")


def build_session() -> requests.Session:

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),
            "Accept-Language":
                "tr-TR,tr;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
    )

    return session


def access_blocked(html: str) -> bool:
    """
    Detect common anti-bot pages.
    """

    text = ascii_tr(html).casefold()

    keywords = (
        "cf-chl-",
        "challenge-platform",
        "verify you are human",
        "insan oldugunuzu dogrulayin",
        "just a moment...",
    )

    return any(
        word in text
        for word in keywords
    )


def get_html(
    session: requests.Session,
    url: str,
) -> tuple[str, str]:

    """
    Download HTML with retry logic.
    """

    last_error = None

    for attempt in range(4):

        try:

            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            response.raise_for_status()

            response.encoding = (
                response.apparent_encoding
                or "utf-8"
            )

            if (
                access_blocked(response.text)
                or len(response.text) < 700
            ):
                raise RuntimeError(
                    "Page blocked or response too short."
                )

            return (
                response.text,
                response.url,
            )

        except Exception as exc:

            last_error = exc

            if attempt < 3:

                wait_time = (
                    (2 ** attempt)
                    + random.uniform(
                        0.25,
                        0.8,
                    )
                )

                time.sleep(wait_time)

    raise RuntimeError(
        f"Could not fetch {url}: "
        f"{last_error}"
    )



def collect_company_links(
    session: requests.Session,
) -> list[dict[str, str]]:

    print(
        f"Opening company list: "
        f"{LIST_URL}"
    )

    html, final_url = get_html(
        session,
        LIST_URL,
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
            link.get("href", ""),
        )

        slug = profile_slug(url)

        title_element = (
            link.find("h4")
            or link.find("h5")
            or link
        )

        name = ascii_tr(
            title_element.get_text(
                " ",
                strip=True,
            )
        )

        if slug and name:

            companies[slug] = {
                "company_name": name,
                "profile_url": url,
            }

    company_list = sorted(
        companies.values(),
        key=lambda item:
            item["company_name"],
    )

    print(
        f"Company profiles found: "
        f"{len(company_list)}"
    )

    if (
        len(company_list)
        < MIN_EXPECTED_COMPANIES
    ):

        raise RuntimeError(
            "Unexpectedly low company count."
        )

    return company_list

def detail_list_fields(
    soup: BeautifulSoup,
) -> dict[str, list[str]]:

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

        key = label_key(
            key_element.text
        )

        value = clean_text(
            value_element.text
        )

        if key and value:

            result.setdefault(
                key,
                [],
            ).append(value)

    return result


def contact_fields(
    soup: BeautifulSoup,
) -> dict[str, list[str]]:

    result = {}

    contact_box = (
        soup.select_one(".contact_class")
        or soup.select_one(".contact-info")
    )

    if not contact_box:
        return result

    for heading in contact_box.select("h4"):

        sibling = (
            heading.find_next_sibling()
        )

        while (
            sibling
            and getattr(
                sibling,
                "name",
                None,
            )
            not in ("h4", "p")
        ):

            sibling = (
                sibling
                .find_next_sibling()
            )

        if (
            sibling
            and sibling.name == "p"
        ):

            key = label_key(
                heading.text
            )

            value = clean_text(
                sibling.text
            )

            if key and value:

                result.setdefault(
                    key,
                    [],
                ).append(value)

    return result


def values_for(
    data: dict[str, list[str]],
    prefixes: tuple[str, ...],
) -> list[str]:

    result = []

    for key, values in data.items():

        if any(
            key.startswith(prefix)
            for prefix in prefixes
        ):

            result.extend(values)

    return result


EMAIL_PREFIXES = (
    "mail",
    "email",
    "eposta",
    "epostaadresi",
    "iletisim",
    "contact",
)


def parse_detail(
    html: str,
    item: dict[str, str],
    url: str,
) -> dict[str, str]:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    title = soup.select_one(
        ".page-title-heading h2, "
        ".ttm-service-description h4"
    )

    company_name = ascii_tr(
        title.text
        if title
        else item["company_name"]
    )

    info = detail_list_fields(soup)
    contact = contact_fields(soup)

    sector_values = values_for(
        info,
        (
            "faaliyet",
            "sektor",
            "uretim",
            "yatirimkonusu",
        ),
    )

    sector = (
        ascii_tr(
            sector_values[0]
        )
        if sector_values
        else ""
    )

    address_values = values_for(
        contact,
        ("adres",),
    )

    address = (
        ascii_tr(
            address_values[0]
        )
        if address_values
        else DEFAULT_ADDRESS
    )

    phone = unique_join(
        normalize_phone(value)
        for value in values_for(
            contact,
            ("telefon", "tel"),
        )
    )

    fax = unique_join(
        normalize_phone(value)
        for value in values_for(
            contact,
            ("faks", "fax", "gsm"),
        )
    )

    email = normalize_email(
        " ".join(
            values_for(
                contact,
                EMAIL_PREFIXES,
            )
        )
    )

    website = ""

    for value in values_for(
        info,
        (
            "web",
            "website",
            "internet",
        ),
    ):

        website = normalize_website(
            value,
            url,
        )

        if website:
            break

    return {
        "city": CITY,
        "osb_name": OSB_NAME,
        "sector": sector,
        "company_name": company_name,
        "address": address,
        "phone": phone,
        "fax": fax,
        "website": website,
        "email": email,
        "activity_subject": sector,
        "profile_url": url,
        "company_id": make_company_id(
            company_name,
            url,
        ),
    }



def find_company_email(
    session: requests.Session,
    website: str,
) -> str:

    if not website:
        return ""

    try:

        html, base_url = get_html(
            session,
            website,
        )

    except Exception:

        return ""

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    page_text = soup.get_text(
        " ",
        strip=True,
    )

    mailto_values = " ".join(
        link.get(
            "href",
            "",
        ).replace(
            "mailto:",
            "",
        )
        for link in soup.select(
            'a[href^="mailto:"]'
        )
    )

    email = normalize_email(
        page_text
        + " "
        + mailto_values
    )

    if email:
        return email

    for link in soup.select(
        "a[href]"
    ):

        label = ascii_tr(
            link.text
            + " "
            + link.get(
                "href",
                "",
            )
        ).casefold()

        if (
            "iletisim" not in label
            and "contact" not in label
        ):
            continue

        target = urljoin(
            base_url,
            link["href"],
        )

        if (
            urlparse(target).netloc
            != urlparse(
                base_url
            ).netloc
        ):
            continue

        try:

            html2, _ = get_html(
                session,
                target,
            )

            page = BeautifulSoup(
                html2,
                "html.parser",
            )

            email = normalize_email(
                page.get_text(
                    " ",
                    strip=True,
                )
            )

            if email:
                return email

        except Exception:
            pass

    return ""


def scrape_all() -> list[dict[str, str]]:

    session = build_session()

    links = collect_company_links(
        session
    )

    records = []

    for index, item in enumerate(
        links,
        start=1,
    ):

        print(
            f"[{index}/{len(links)}] "
            f"{item['company_name']}"
        )

        try:

            html, final_url = get_html(
                session,
                item["profile_url"],
            )

            record = parse_detail(
                html,
                item,
                final_url,
            )

            if (
                not record["email"]
                and record["website"]
            ):

                record["email"] = (
                    find_company_email(
                        session,
                        record["website"],
                    )
                )

            records.append(record)

            print(
                "OK "
                f"email={bool(record['email'])} "
                f"website={bool(record['website'])}"
            )

        except Exception as exc:

            print(
                "ERROR:",
                type(exc).__name__,
                exc,
            )

        time.sleep(
            random.uniform(
                0.2,
                0.5,
            )
        )

    # Remove duplicates using company_id
    unique_records = {
        record["company_id"]: record
        for record in records
    }

    records = list(
        unique_records.values()
    )

    print(
        f"Parsed companies: "
        f"{len(records)}"
    )

    print(
        "Companies with email: "
        f"{sum(bool(r['email']) for r in records)}"
    )

    return records


def record_to_row(
    record: dict[str, str],
) -> list[str]:

    return [
        record.get(
            column,
            "",
        )
        for column
        in SHEET_HEADER
    ]


def write_csv(
    records: list[dict[str, str]],
) -> Path:

    csv_path = (
        Path(__file__)
        .with_name(
            f"{TAB_NAME}.csv"
        )
    )

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            SHEET_HEADER
        )

        for record in records:

            writer.writerow(
                record_to_row(record)
            )

    print(
        f"CSV created: {csv_path}"
    )

    return csv_path



def sheets_client():

    credentials_path = os.getenv(
        "GOOGLE_CREDENTIALS_FILE"
    )

    spreadsheet_id = os.getenv(
        "SPREADSHEET_ID"
    )

    if not credentials_path:
        raise RuntimeError(
            "GOOGLE_CREDENTIALS_FILE "
            "environment variable is missing."
        )

    if not spreadsheet_id:
        raise RuntimeError(
            "SPREADSHEET_ID "
            "environment variable is missing."
        )

    credentials = (
        service_account
        .Credentials
        .from_service_account_file(
            credentials_path,
            scopes=[
                "https://www.googleapis.com/"
                "auth/spreadsheets"
            ],
        )
    )

    service = build(
        "sheets",
        "v4",
        credentials=credentials,
    )

    return (
        service,
        spreadsheet_id,
    )


def ensure_tab_header(
    service,
    spreadsheet_id: str,
):

    spreadsheet = (
        service
        .spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields="sheets.properties",
        )
        .execute()
    )

    titles = {
        sheet["properties"]["title"]
        for sheet
        in spreadsheet.get(
            "sheets",
            [],
        )
    }

    if TAB_NAME not in titles:

        (
            service
            .spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": [
                        {
                            "addSheet": {
                                "properties": {
                                    "title":
                                        TAB_NAME
                                }
                            }
                        }
                    ]
                },
            )
            .execute()
        )

    response = (
        service
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=f"{TAB_NAME}!A1:L1",
        )
        .execute()
    )

    if not response.get("values"):

        (
            service
            .spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=f"{TAB_NAME}!A1",
                valueInputOption="RAW",
                body={
                    "values": [
                        SHEET_HEADER
                    ]
                },
            )
            .execute()
        )


def write_records(
    service,
    spreadsheet_id: str,
    records: list[dict[str, str]],
):

    rows = [
        record_to_row(record)
        for record
        in records
    ]

    (
        service
        .spreadsheets()
        .values()
        .clear(
            spreadsheetId=spreadsheet_id,
            range=f"{TAB_NAME}!A2:L",
            body={},
        )
        .execute()
    )

    if rows:

        (
            service
            .spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=f"{TAB_NAME}!A2",
                valueInputOption="RAW",
                body={
                    "values": rows
                },
            )
            .execute()
        )

    print(
        f"Google Sheets updated: "
        f"{len(rows)} companies"
    )




def main():

    print(
        "\nOSB Company Scraper\n"
        "===================\n"
    )

    records = scrape_all()

    csv_path = write_csv(
        records
    )

    try:

        service, spreadsheet_id = (
            sheets_client()
        )

        ensure_tab_header(
            service,
            spreadsheet_id,
        )

        write_records(
            service,
            spreadsheet_id,
            records,
        )

    except (
        RuntimeError,
        FileNotFoundError,
        HttpError,
    ) as exc:

        print(
            "\nGoogle Sheets skipped:"
        )

        print(exc)

        print(
            "\nCSV data is still available:"
        )

        print(csv_path)

    print(
        "\nFinished."
    )


if __name__ == "__main__":
    main()