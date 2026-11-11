"""Client for interacting with the Socrata NYC Open Data 311 API."""

import logging
from typing import Any, Dict, Iterator, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from extract_load.config import SocrataConfig

logger = logging.getLogger(__name__)

SELECTED_COLUMNS = [
    "unique_key",
    "created_date",
    "closed_date",
    "due_date",
    "agency",
    "agency_name",
    "complaint_type",
    "descriptor",
    "status",
    "resolution_description",
    "borough",
    "incident_zip",
    "latitude",
    "longitude",
    "open_data_channel_type",
]


class SocrataAPIError(Exception):
    """Raised when Socrata API returns an error or non-200 status."""
    pass


class SocrataClient:
    """HTTP client for querying NYC 311 service request records via Socrata SODA API."""

    def __init__(self, config: SocrataConfig):
        self.endpoint = config.endpoint
        self.timeout = config.timeout
        self.session = requests.Session()

        # Configure retry strategy for transient network and rate-limit errors
        retry_strategy = Retry(
            total=config.max_retries,
            backoff_factor=config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch_page(
        self,
        watermark: Optional[str] = None,
        start_date: Optional[str] = None,
        limit: int = 5000,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Fetch a single page of service requests.

        Args:
            watermark: ISO timestamp string; records strictly newer than this will be fetched.
            start_date: ISO timestamp string fallback if watermark is not set.
            limit: Maximum records to return in this page.
            offset: Offset for pagination.

        Returns:
            List of record dictionaries.
        """
        params: Dict[str, Any] = {
            "$select": ",".join(SELECTED_COLUMNS),
            "$order": "created_date ASC, unique_key ASC",
            "$limit": limit,
            "$offset": offset,
        }

        # Build filter clause
        if watermark:
            params["$where"] = f"created_date > '{watermark}'"
        elif start_date:
            params["$where"] = f"created_date >= '{start_date}'"

        try:
            resp = self.session.get(self.endpoint, params=params, timeout=self.timeout)
        except requests.RequestException as e:
            raise SocrataAPIError(f"Network error querying Socrata API: {e}") from e

        if resp.status_code != 200:
            raise SocrataAPIError(
                f"Socrata API returned HTTP {resp.status_code}: {resp.text}"
            )

        data = resp.json()
        if not isinstance(data, list):
            raise SocrataAPIError(
                f"Unexpected response payload type: expected list, got {type(data)}"
            )

        return data

    def paginate_records(
        self,
        watermark: Optional[str] = None,
        start_date: Optional[str] = None,
        batch_size: int = 5000,
        max_records: Optional[int] = None,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Yield pages of records until no more records are available or max_records reached.

        Args:
            watermark: Incremental watermark for created_date.
            start_date: Fallback starting date if watermark is absent.
            batch_size: Number of records per page.
            max_records: Maximum total records to yield across all pages.
        """
        offset = 0
        total_fetched = 0

        while True:
            fetch_limit = batch_size
            if max_records is not None:
                remaining = max_records - total_fetched
                if remaining <= 0:
                    break
                fetch_limit = min(batch_size, remaining)

            page = self.fetch_page(
                watermark=watermark,
                start_date=start_date,
                limit=fetch_limit,
                offset=offset,
            )

            if not page:
                break

            yield page

            page_len = len(page)
            total_fetched += page_len
            offset += page_len

            if page_len < fetch_limit:
                # Last page reached
                break
