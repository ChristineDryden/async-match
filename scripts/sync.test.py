import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.sync import matches_for_insert, page_reached_before_watermark, parse_match_time

WATERMARK = datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc)


def test_parse_match_time():
    dt = parse_match_time("2026-10-15T06:00:00.000Z")
    assert dt == WATERMARK


def test_inserts_from_watermark_inclusive():
    scraped = [
        {"id": "new", "date": "2026-10-15T07:00:00.000Z"},
        {"id": "same", "date": "2026-10-15T06:00:00.000Z"},
        {"id": "old", "date": "2026-10-15T05:00:00.000Z"},
    ]
    got = [m["id"] for m in matches_for_insert(scraped, WATERMARK)]
    assert got == ["new", "same"]


def test_empty_db_takes_all_valid():
    scraped = [
        {"id": "a", "date": "2026-10-15T07:00:00.000Z"},
        {"id": "b", "date": None},
    ]
    got = [m["id"] for m in matches_for_insert(scraped, None)]
    assert got == ["a"]


def test_stop_when_page_is_fully_older():
    page = [
        {"id": "1", "date": "2026-10-15T05:50:00.000Z"},
        {"id": "2", "date": "2026-10-15T05:40:00.000Z"},
    ]
    assert page_reached_before_watermark(page, WATERMARK) is True


def test_keep_going_if_page_still_overlaps_watermark():
    page = [
        {"id": "1", "date": "2026-10-15T06:10:00.000Z"},
        {"id": "2", "date": "2026-10-15T05:50:00.000Z"},
    ]
    assert page_reached_before_watermark(page, WATERMARK) is False


def test_no_stop_without_watermark():
    page = [{"id": "1", "date": "2020-01-01T00:00:00.000Z"}]
    assert page_reached_before_watermark(page, None) is False


if __name__ == "__main__":
    test_parse_match_time()
    test_inserts_from_watermark_inclusive()
    test_empty_db_takes_all_valid()
    test_stop_when_page_is_fully_older()
    test_keep_going_if_page_still_overlaps_watermark()
    test_no_stop_without_watermark()
    print("ok")
