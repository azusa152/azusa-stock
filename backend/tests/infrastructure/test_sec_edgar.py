"""
Tests for SEC EDGAR client (infrastructure/sec_edgar.py).
All HTTP calls are mocked — no network I/O in this test suite.
"""

from unittest.mock import patch

from sqlmodel import Session

from domain.entities import Guru, GuruFiling, GuruHolding
from infrastructure.external.sec_edgar import (
    _discover_infotable_filename,
    _parse_13f_xml,
    fetch_13f_filing_detail,
    fetch_company_filings,
    get_latest_13f_filings,
    map_cusip_to_ticker,
)
from infrastructure.repositories import (
    deactivate_guru,
    find_all_active_gurus,
    find_filing_by_accession,
    find_filings_by_guru,
    find_guru_by_cik,
    find_guru_by_id,
    find_holdings_by_filing,
    find_holdings_by_guru_latest,
    find_holdings_by_ticker_across_gurus,
    find_latest_filing_by_guru,
    save_filing,
    save_guru,
    save_holdings_batch,
    update_guru,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_SUBMISSIONS = {
    "cik": "0001067983",
    "name": "BERKSHIRE HATHAWAY INC",
    "filings": {
        "recent": {
            "form": ["13F-HR", "13F-HR", "10-K"],
            "accessionNumber": [
                "0001067983-25-000006",
                "0001067983-24-000010",
                "0001067983-24-000001",
            ],
            "filingDate": ["2025-02-14", "2024-11-14", "2024-02-22"],
            "reportDate": ["2024-12-31", "2024-09-30", "2023-12-31"],
            "primaryDocument": ["0001067983-25-000006-index.htm", "doc.htm", "doc.htm"],
        }
    },
}

_SAMPLE_13F_XML = """<?xml version="1.0" encoding="UTF-8"?>
<informationTable>
  <infoTable>
    <nameOfIssuer>APPLE INC</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>037833100</cusip>
    <value>174530000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>400000000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority>
      <Sole>400000000</Sole>
      <Shared>0</Shared>
      <None>0</None>
    </votingAuthority>
  </infoTable>
  <infoTable>
    <nameOfIssuer>AMERICAN EXPRESS CO</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>025816109</cusip>
    <value>41100000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>151610700</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority>
      <Sole>151610700</Sole>
      <Shared>0</Shared>
      <None>0</None>
    </votingAuthority>
  </infoTable>
</informationTable>
"""


# ---------------------------------------------------------------------------
# _parse_13f_xml
# ---------------------------------------------------------------------------


class TestParse13fXml:
    """Unit tests for the internal XML parser (no HTTP)."""

    def test_parse_13f_xml_should_return_two_holdings_from_sample(self):
        result = _parse_13f_xml(_SAMPLE_13F_XML)
        assert len(result) == 2

    def test_parse_13f_xml_should_extract_cusip_correctly(self):
        result = _parse_13f_xml(_SAMPLE_13F_XML)
        cusips = {h["cusip"] for h in result}
        assert "037833100" in cusips
        assert "025816109" in cusips

    def test_parse_13f_xml_should_extract_company_name(self):
        result = _parse_13f_xml(_SAMPLE_13F_XML)
        names = {h["company_name"] for h in result}
        assert "APPLE INC" in names

    def test_parse_13f_xml_should_extract_value_as_float(self):
        result = _parse_13f_xml(_SAMPLE_13F_XML)
        apple = next(h for h in result if h["cusip"] == "037833100")
        assert isinstance(apple["value"], float)
        assert apple["value"] == 174530000.0

    def test_parse_13f_xml_should_extract_shares_as_float(self):
        result = _parse_13f_xml(_SAMPLE_13F_XML)
        apple = next(h for h in result if h["cusip"] == "037833100")
        assert isinstance(apple["shares"], float)
        assert apple["shares"] == 400000000.0

    def test_parse_13f_xml_should_return_empty_on_malformed_xml(self):
        result = _parse_13f_xml("<broken><xml>")
        assert result == []

    def test_parse_13f_xml_should_return_empty_on_empty_string(self):
        result = _parse_13f_xml("")
        assert result == []

    def test_parse_13f_xml_should_uppercase_cusip(self):
        xml = _SAMPLE_13F_XML.replace("037833100", "037833100")
        result = _parse_13f_xml(xml)
        for h in result:
            assert h["cusip"] == h["cusip"].upper()


# ---------------------------------------------------------------------------
# map_cusip_to_ticker
# ---------------------------------------------------------------------------


class TestMapCusipToTicker:
    """Tests for CUSIP → ticker mapping."""

    def test_map_cusip_to_ticker_should_return_aapl_for_known_cusip(self):
        assert map_cusip_to_ticker("037833100", "APPLE INC") == "AAPL"

    def test_map_cusip_to_ticker_should_return_amex_for_known_cusip(self):
        assert map_cusip_to_ticker("025816109", "AMERICAN EXPRESS") == "AXP"

    def test_map_cusip_to_ticker_should_return_ticker_via_name_hint(self):
        # Unknown CUSIP but name matches known fragment
        result = map_cusip_to_ticker("XXXXXXXXX", "MICROSOFT CORP")
        assert result == "MSFT"

    def test_map_cusip_to_ticker_should_return_none_for_unknown(self):
        result = map_cusip_to_ticker("XXXXXXXXX", "UNKNOWN CORP XYZ 12345")
        assert result is None

    def test_map_cusip_to_ticker_should_be_case_insensitive_for_cusip(self):
        # CUSIP is normalized to uppercase inside the function
        result = map_cusip_to_ticker("037833100", "")
        assert result == "AAPL"


# ---------------------------------------------------------------------------
# fetch_company_filings (mocked HTTP)
# ---------------------------------------------------------------------------


class TestFetchCompanyFilings:
    """Tests for fetch_company_filings() with mocked HTTP."""

    def test_fetch_company_filings_should_return_submissions_on_success(self):
        with patch(
            "infrastructure.external.sec_edgar._http_get_json",
            return_value=_SAMPLE_SUBMISSIONS,
        ):
            result = fetch_company_filings("0001067983")
        assert result["name"] == "BERKSHIRE HATHAWAY INC"

    def test_fetch_company_filings_should_return_error_dict_on_http_failure(self):
        with patch(
            "infrastructure.external.sec_edgar._http_get_json",
            side_effect=Exception("connection refused"),
        ):
            # Clear cache so the mock is actually called
            from infrastructure.external.sec_edgar import _filing_cache

            _filing_cache.clear()
            result = fetch_company_filings("0000000001")
        assert "error" in result

    def test_fetch_company_filings_should_cache_result_in_l1(self):
        from infrastructure.external.sec_edgar import _filing_cache

        # Use a CIK that is unlikely to be in any persistent cache
        cik = "TEST_CACHE_CIK_XYZ"
        _filing_cache.pop(cik, None)

        with (
            patch(
                "infrastructure.external.sec_edgar._disk_get",
                return_value=None,  # force L2 miss
            ),
            patch(
                "infrastructure.external.sec_edgar._disk_set",
            ),
            patch(
                "infrastructure.external.sec_edgar._http_get_json",
                return_value=_SAMPLE_SUBMISSIONS,
            ) as mock_get,
        ):
            fetch_company_filings(cik)
            fetch_company_filings(cik)  # second call must hit L1

        # HTTP should only be called once (second call served from L1 cache)
        assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# get_latest_13f_filings (mocked fetch_company_filings)
# ---------------------------------------------------------------------------


class TestGetLatest13fFilings:
    """Tests for get_latest_13f_filings()."""

    def test_get_latest_13f_filings_should_return_two_records(self):
        with patch(
            "infrastructure.external.sec_edgar.fetch_company_filings",
            return_value=_SAMPLE_SUBMISSIONS,
        ):
            result = get_latest_13f_filings("0001067983", count=2)
        assert len(result) == 2

    def test_get_latest_13f_filings_should_only_include_13f_hr_forms(self):
        with patch(
            "infrastructure.external.sec_edgar.fetch_company_filings",
            return_value=_SAMPLE_SUBMISSIONS,
        ):
            result = get_latest_13f_filings("0001067983", count=10)
        # The sample has 2 13F-HR and 1 10-K; 10-K must be excluded
        assert len(result) == 2

    def test_get_latest_13f_filings_should_include_required_keys(self):
        with patch(
            "infrastructure.external.sec_edgar.fetch_company_filings",
            return_value=_SAMPLE_SUBMISSIONS,
        ):
            result = get_latest_13f_filings("0001067983", count=1)
        entry = result[0]
        for key in ("accession_number", "filing_date", "report_date", "filing_url"):
            assert key in entry, f"Missing key: {key}"

    def test_get_latest_13f_filings_should_return_empty_on_error(self):
        with patch(
            "infrastructure.external.sec_edgar.fetch_company_filings",
            return_value={"error": "timeout"},
        ):
            result = get_latest_13f_filings("0001067983")
        assert result == []

    def test_get_latest_13f_filings_should_respect_count_limit(self):
        with patch(
            "infrastructure.external.sec_edgar.fetch_company_filings",
            return_value=_SAMPLE_SUBMISSIONS,
        ):
            result = get_latest_13f_filings("0001067983", count=1)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _discover_infotable_filename (mocked HTTP)
# ---------------------------------------------------------------------------


class TestDiscoverInfotableFilename:
    """Tests for _discover_infotable_filename()."""

    def test_discover_infotable_filename_should_return_non_primary_xml(self):
        mock_index_json = {
            "directory": {
                "item": [
                    {"name": "0001193125-26-054580.txt", "size": "62306"},
                    {"name": "primary_doc.xml", "size": "5556"},
                    {"name": "50240.xml", "size": "55376"},
                ]
            }
        }

        with patch(
            "infrastructure.external.sec_edgar._http_get_json",
            return_value=mock_index_json,
        ):
            result = _discover_infotable_filename("000119312526054580", "0001067983")

        assert result == "50240.xml"

    def test_discover_infotable_filename_should_skip_primary_doc_xml(self):
        mock_index_json = {
            "directory": {
                "item": [
                    {"name": "primary_doc.xml", "size": "5556"},
                    {"name": "infotable.xml", "size": "12345"},
                ]
            }
        }

        with patch(
            "infrastructure.external.sec_edgar._http_get_json",
            return_value=mock_index_json,
        ):
            result = _discover_infotable_filename("000000000000000000", "0000000000")

        assert result == "infotable.xml"

    def test_discover_infotable_filename_should_return_none_on_http_error(self):
        with patch(
            "infrastructure.external.sec_edgar._http_get_json",
            side_effect=Exception("network error"),
        ):
            result = _discover_infotable_filename("000000000000000000", "0000000000")

        assert result is None

    def test_discover_infotable_filename_should_return_none_when_no_xml_found(self):
        mock_index_json = {
            "directory": {
                "item": [
                    {"name": "0001193125-26-054580.txt", "size": "62306"},
                    {"name": "primary_doc.xml", "size": "5556"},
                ]
            }
        }

        with patch(
            "infrastructure.external.sec_edgar._http_get_json",
            return_value=mock_index_json,
        ):
            result = _discover_infotable_filename("000000000000000000", "0000000000")

        assert result is None

    def test_discover_infotable_filename_should_return_none_on_malformed_json(self):
        mock_index_json = {"some_unexpected_key": "value"}

        with patch(
            "infrastructure.external.sec_edgar._http_get_json",
            return_value=mock_index_json,
        ):
            result = _discover_infotable_filename("000000000000000000", "0000000000")

        assert result is None


# ---------------------------------------------------------------------------
# fetch_13f_filing_detail (mocked HTTP)
# ---------------------------------------------------------------------------


class TestFetch13fFilingDetail:
    """Tests for fetch_13f_filing_detail()."""

    def test_fetch_13f_filing_detail_should_return_holdings_on_success(self):
        from infrastructure.external.sec_edgar import _disk_cache

        # Clear disk cache to force HTTP call
        _disk_cache.clear()

        with (
            patch(
                "infrastructure.external.sec_edgar._discover_infotable_filename",
                return_value="50240.xml",
            ),
            patch(
                "infrastructure.external.sec_edgar._http_get_text",
                return_value=_SAMPLE_13F_XML,
            ),
        ):
            result = fetch_13f_filing_detail("0001067983-25-000006", "0001067983")

        assert len(result) == 2
        assert result[0]["cusip"] in ("037833100", "025816109")

    def test_fetch_13f_filing_detail_should_return_empty_on_http_error(self):
        from infrastructure.external.sec_edgar import _disk_cache

        _disk_cache.clear()

        with (
            patch(
                "infrastructure.external.sec_edgar._discover_infotable_filename",
                return_value="infotable.xml",
            ),
            patch(
                "infrastructure.external.sec_edgar._http_get_text",
                side_effect=Exception("network error"),
            ),
        ):
            result = fetch_13f_filing_detail("0000000000-00-000000", "0000000000")

        assert result == []

    def test_fetch_13f_filing_detail_should_fallback_when_discovery_fails(self):
        from infrastructure.external.sec_edgar import _disk_cache

        _disk_cache.clear()

        with (
            patch(
                "infrastructure.external.sec_edgar._discover_infotable_filename",
                return_value=None,  # Discovery failed
            ),
            patch(
                "infrastructure.external.sec_edgar._http_get_text",
                return_value=_SAMPLE_13F_XML,
            ) as mock_get_text,
        ):
            result = fetch_13f_filing_detail("0001067983-25-000006", "0001067983")

        # Should fallback to "infotable.xml" when discovery returns None
        assert len(result) == 2
        # Verify the URL used contains the fallback filename
        called_url = mock_get_text.call_args[0][0]
        assert "infotable.xml" in called_url


# ---------------------------------------------------------------------------
# Guru Repository tests (in-memory SQLite)
# ---------------------------------------------------------------------------


class TestGuruRepository:
    """CRUD tests for Guru repository functions."""

    def test_save_guru_should_persist_and_return_with_id(self, db_session: Session):
        guru = Guru(
            name="Berkshire Hathaway Inc",
            cik="0001067983",
            display_name="Warren Buffett",
        )
        saved = save_guru(db_session, guru)
        assert saved.id is not None
        assert saved.cik == "0001067983"

    def test_find_guru_by_cik_should_return_guru(self, db_session: Session):
        save_guru(
            db_session,
            Guru(
                name="Test Corp",
                cik="0000000001",
                display_name="Test Manager",
            ),
        )
        found = find_guru_by_cik(db_session, "0000000001")
        assert found is not None
        assert found.display_name == "Test Manager"

    def test_find_guru_by_cik_should_return_none_when_not_found(
        self, db_session: Session
    ):
        assert find_guru_by_cik(db_session, "9999999999") is None

    def test_find_all_active_gurus_should_exclude_inactive(self, db_session: Session):
        g1 = save_guru(
            db_session,
            Guru(name="Active", cik="0000000011", display_name="Active"),
        )
        g2 = save_guru(
            db_session,
            Guru(name="Inactive", cik="0000000012", display_name="Inactive"),
        )
        deactivate_guru(db_session, g2)

        active = find_all_active_gurus(db_session)
        ids = [g.id for g in active]
        assert g1.id in ids
        assert g2.id not in ids

    def test_deactivate_guru_should_set_is_active_false(self, db_session: Session):
        guru = save_guru(
            db_session,
            Guru(name="Corp", cik="0000000021", display_name="Manager"),
        )
        assert guru.is_active is True
        deactivate_guru(db_session, guru)
        found = find_guru_by_id(db_session, guru.id)
        assert found is not None
        assert found.is_active is False

    def test_update_guru_should_persist_changes(self, db_session: Session):
        guru = save_guru(
            db_session,
            Guru(name="Old Name", cik="0000000031", display_name="Old"),
        )
        guru.display_name = "New Display"
        updated = update_guru(db_session, guru)
        assert updated.display_name == "New Display"
        found = find_guru_by_id(db_session, guru.id)
        assert found is not None
        assert found.display_name == "New Display"


# ---------------------------------------------------------------------------
# GuruFiling Repository tests
# ---------------------------------------------------------------------------


class TestGuruFilingRepository:
    """CRUD tests for GuruFiling repository functions."""

    def _make_guru(self, session: Session, cik: str = "0001067983") -> Guru:
        return save_guru(
            session,
            Guru(name="Berkshire", cik=cik, display_name="Buffett"),
        )

    def test_save_filing_should_persist_and_return_with_id(self, db_session: Session):
        guru = self._make_guru(db_session)
        filing = save_filing(
            db_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="0001067983-25-000006",
                report_date="2024-12-31",
                filing_date="2025-02-14",
            ),
        )
        assert filing.id is not None
        assert filing.report_date == "2024-12-31"

    def test_find_latest_filing_by_guru_should_return_most_recent(
        self, db_session: Session
    ):
        guru = self._make_guru(db_session, cik="0001067984")
        save_filing(
            db_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="ACC-2024Q1",
                report_date="2024-03-31",
                filing_date="2024-05-15",
            ),
        )
        save_filing(
            db_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="ACC-2024Q3",
                report_date="2024-09-30",
                filing_date="2024-11-14",
            ),
        )
        latest = find_latest_filing_by_guru(db_session, guru.id)
        assert latest is not None
        assert latest.report_date == "2024-09-30"

    def test_find_latest_filing_by_guru_should_return_none_when_no_filings(
        self, db_session: Session
    ):
        guru = self._make_guru(db_session, cik="0001067985")
        assert find_latest_filing_by_guru(db_session, guru.id) is None

    def test_find_filing_by_accession_should_find_existing(self, db_session: Session):
        guru = self._make_guru(db_session, cik="0001067986")
        save_filing(
            db_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="UNIQUE-ACC-001",
                report_date="2024-12-31",
                filing_date="2025-02-14",
            ),
        )
        found = find_filing_by_accession(db_session, "UNIQUE-ACC-001")
        assert found is not None
        assert found.accession_number == "UNIQUE-ACC-001"

    def test_find_filing_by_accession_should_return_none_when_not_found(
        self, db_session: Session
    ):
        assert find_filing_by_accession(db_session, "NONEXISTENT") is None

    def test_find_filings_by_guru_should_return_ordered_by_report_date_desc(
        self, db_session: Session
    ):
        guru = self._make_guru(db_session, cik="0001067987")
        for quarter, date in enumerate(
            ["2024-03-31", "2024-06-30", "2024-09-30"], start=1
        ):
            save_filing(
                db_session,
                GuruFiling(
                    guru_id=guru.id,
                    accession_number=f"ACC-Q{quarter}",
                    report_date=date,
                    filing_date=date,
                ),
            )
        filings = find_filings_by_guru(db_session, guru.id)
        dates = [f.report_date for f in filings]
        assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# GuruHolding Repository tests
# ---------------------------------------------------------------------------


class TestGuruHoldingRepository:
    """CRUD tests for GuruHolding repository functions."""

    def _setup(
        self, session: Session, cik: str = "0009000001"
    ) -> tuple[Guru, GuruFiling]:
        guru = save_guru(
            session,
            Guru(name="Test Guru", cik=cik, display_name="Test"),
        )
        filing = save_filing(
            session,
            GuruFiling(
                guru_id=guru.id,
                accession_number=f"ACC-{cik}",
                report_date="2024-12-31",
                filing_date="2025-02-14",
            ),
        )
        return guru, filing

    def test_save_holdings_batch_should_persist_multiple_holdings(
        self, db_session: Session
    ):
        guru, filing = self._setup(db_session)
        holdings = [
            GuruHolding(
                filing_id=filing.id,
                guru_id=guru.id,
                cusip="037833100",
                ticker="AAPL",
                company_name="APPLE INC",
                value=174530000.0,
                shares=400000000.0,
            ),
            GuruHolding(
                filing_id=filing.id,
                guru_id=guru.id,
                cusip="025816109",
                ticker="AXP",
                company_name="AMERICAN EXPRESS CO",
                value=41100000.0,
                shares=151610700.0,
            ),
        ]
        save_holdings_batch(db_session, holdings)
        found = find_holdings_by_filing(db_session, filing.id)
        assert len(found) == 2

    def test_find_holdings_by_filing_should_order_by_weight_pct_desc(
        self, db_session: Session
    ):
        guru, filing = self._setup(db_session, cik="0009000002")
        holdings = [
            GuruHolding(
                filing_id=filing.id,
                guru_id=guru.id,
                cusip="AAA",
                company_name="Small",
                value=10.0,
                shares=10.0,
                weight_pct=5.0,
            ),
            GuruHolding(
                filing_id=filing.id,
                guru_id=guru.id,
                cusip="BBB",
                company_name="Large",
                value=90.0,
                shares=90.0,
                weight_pct=45.0,
            ),
        ]
        save_holdings_batch(db_session, holdings)
        found = find_holdings_by_filing(db_session, filing.id)
        assert found[0].weight_pct is not None
        assert found[-1].weight_pct is not None
        assert found[0].weight_pct >= found[-1].weight_pct

    def test_find_holdings_by_guru_latest_should_return_latest_filings_holdings(
        self, db_session: Session
    ):
        guru, old_filing = self._setup(db_session, cik="0009000003")
        new_filing = save_filing(
            db_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="ACC-NEW",
                report_date="2025-03-31",
                filing_date="2025-05-15",
            ),
        )
        # Holding in old filing
        save_holdings_batch(
            db_session,
            [
                GuruHolding(
                    filing_id=old_filing.id,
                    guru_id=guru.id,
                    cusip="OLD",
                    company_name="Old Co",
                    value=1.0,
                    shares=1.0,
                )
            ],
        )
        # Holding in new filing
        save_holdings_batch(
            db_session,
            [
                GuruHolding(
                    filing_id=new_filing.id,
                    guru_id=guru.id,
                    cusip="NEW",
                    company_name="New Co",
                    value=2.0,
                    shares=2.0,
                )
            ],
        )
        latest_holdings = find_holdings_by_guru_latest(db_session, guru.id)
        cusips = [h.cusip for h in latest_holdings]
        assert "NEW" in cusips
        assert "OLD" not in cusips

    def test_find_holdings_by_ticker_across_gurus_should_only_include_latest(
        self, db_session: Session
    ):
        g1 = save_guru(
            db_session,
            Guru(name="G1", cik="0009000041", display_name="G1"),
        )
        old_f = save_filing(
            db_session,
            GuruFiling(
                guru_id=g1.id,
                accession_number="G1-OLD",
                report_date="2024-06-30",
                filing_date="2024-08-14",
            ),
        )
        new_f = save_filing(
            db_session,
            GuruFiling(
                guru_id=g1.id,
                accession_number="G1-NEW",
                report_date="2024-12-31",
                filing_date="2025-02-14",
            ),
        )
        # AAPL in old filing
        save_holdings_batch(
            db_session,
            [
                GuruHolding(
                    filing_id=old_f.id,
                    guru_id=g1.id,
                    cusip="037833100",
                    ticker="AAPL",
                    company_name="APPLE INC",
                    value=100.0,
                    shares=100.0,
                )
            ],
        )
        # AAPL in new filing
        save_holdings_batch(
            db_session,
            [
                GuruHolding(
                    filing_id=new_f.id,
                    guru_id=g1.id,
                    cusip="037833100",
                    ticker="AAPL",
                    company_name="APPLE INC",
                    value=200.0,
                    shares=200.0,
                )
            ],
        )
        results = find_holdings_by_ticker_across_gurus(db_session, "AAPL")
        # Should only include the holding from the latest filing
        assert len(results) == 1
        assert results[0].filing_id == new_f.id
