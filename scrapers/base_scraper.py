import html as html_lib
import random
import re
import time

import requests


class BaseScraper:
    """
    Base class containing common functionality
    used by all OSB scrapers.
    """

    REQUEST_TIMEOUT = 40

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    )

    TURKISH_TRANSLATION = str.maketrans(
        "çğıöşüÇĞİÖŞÜ",
        "cgiosuCGIOSU",
    )

    def __init__(self):
        self.session = self.build_session()

    def build_session(self):
        """
        Creates a reusable HTTP session.
        """

        session = requests.Session()

        session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
                "Accept": (
                    "text/html,"
                    "application/xhtml+xml,"
                    "application/xml;q=0.9,"
                    "*/*;q=0.8"
                ),
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
            }
        )

        return session

    @staticmethod
    def clean_text(value):
        """
        Removes unnecessary whitespace and HTML entities.
        """

        text = "" if value is None else str(value)

        text = (
            html_lib.unescape(text)
            .replace("\xa0", " ")
            .replace("\u00ad", "")
        )

        return re.sub(r"\s+", " ", text).strip(
            " -|\t\r\n"
        )

    def ascii_tr(self, value):
        """
        Converts Turkish characters to ASCII equivalents.
        """

        return self.clean_text(value).translate(
            self.TURKISH_TRANSLATION
        )

    def access_blocked(self, html):
        """
        Detects common anti-bot / challenge pages.
        """

        text = self.ascii_tr(html).casefold()

        keywords = (
            "cf-chl-",
            "challenge-platform",
            "verify you are human",
            "insan oldugunuzu dogrulayin",
            "just a moment...",
        )

        return any(
            keyword in text
            for keyword in keywords
        )

    def get_html(self, url):
        """
        Downloads a page using retry logic.
        """

        last_error = None

        for attempt in range(4):

            try:
                response = self.session.get(
                    url,
                    timeout=self.REQUEST_TIMEOUT,
                    allow_redirects=True,
                )

                response.raise_for_status()

                response.encoding = (
                    response.apparent_encoding
                    or "utf-8"
                )

                if (
                    self.access_blocked(response.text)
                    or len(response.text) < 700
                ):
                    raise RuntimeError(
                        "Page blocked or response too short."
                    )

                return response.text, response.url

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

                    print(
                        f"Request failed. "
                        f"Retrying in {wait_time:.1f}s..."
                    )

                    time.sleep(wait_time)

        raise RuntimeError(
            f"Could not fetch {url}: {last_error}"
        )

    @staticmethod
    def wait_between_requests(
        minimum=0.2,
        maximum=0.5,
    ):
        """
        Adds a small delay between requests.
        """

        time.sleep(
            random.uniform(
                minimum,
                maximum,
            )
        )