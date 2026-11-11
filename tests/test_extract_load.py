"""Unit tests for extract_load module using standard library unittest."""

import sys
import unittest
import uuid
from unittest.mock import MagicMock, patch

try:
    import psycopg2
except ImportError:
    sys.modules["psycopg2"] = MagicMock()
    sys.modules["psycopg2.extras"] = MagicMock()

from extract_load.client import SocrataClient, SocrataConfig
from extract_load.config import DatabaseConfig
from extract_load.db import PostgresLoader


class TestExtractLoad(unittest.TestCase):

    def test_socrata_client_fetch_page_params(self):
        cfg = SocrataConfig(
            endpoint="https://example.com/api",
        )
        client = SocrataClient(cfg)

        with patch.object(client.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{"unique_key": "12345"}]
            mock_get.return_value = mock_response

            # Fetch with watermark
            records = client.fetch_page(watermark="2026-10-01T00:00:00", limit=10, offset=20)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["unique_key"], "12345")

            _, kwargs = mock_get.call_args
            params = kwargs["params"]
            self.assertEqual(params["$limit"], 10)
            self.assertEqual(params["$offset"], 20)
            self.assertEqual(params["$where"], "created_date > '2026-10-01T00:00:00'")
            self.assertIn("$order", params)
            self.assertIn("$select", params)

    def test_postgres_loader_upsert_batch(self):
        db_cfg = DatabaseConfig(
            host="localhost",
            port=5432,
            user="postgres",
            password="",
            database="nyc311",
        )
        loader = PostgresLoader(db_cfg)

        records = [
            {
                "unique_key": "1001",
                "created_date": "2026-10-01T12:00:00.000",
                "agency": "NYPD",
                "complaint_type": "Noise",
            },
            {
                # Missing unique_key - should be skipped
                "agency": "DOT",
                "complaint_type": "Pothole",
            },
            {
                "unique_key": "1002",
                "created_date": "2026-10-01T13:00:00.000",
                "agency": "DEP",
                "complaint_type": "Water Quality",
            },
        ]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch.object(loader, "get_connection") as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = mock_conn

            with patch("extract_load.db.execute_values") as mock_execute_values:
                upserted = loader.upsert_batch(records, str(uuid.uuid4()))
                self.assertEqual(upserted, 2)
                self.assertTrue(mock_execute_values.called)
                # Verify rows passed to execute_values
                called_args = mock_execute_values.call_args[0]
                passed_rows = called_args[2]
                self.assertEqual(len(passed_rows), 2)
                self.assertEqual(passed_rows[0][0], "1001")
                self.assertEqual(passed_rows[1][0], "1002")


if __name__ == "__main__":
    unittest.main()
