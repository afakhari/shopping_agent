"""Tehran-hour and indoor-location regressions for the challenge dataset."""
from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from apps.catalog.services.visit_context import indoor_address_hints, opening_status

TEHRAN = ZoneInfo("Asia/Tehran")


class TehranOpeningHoursTests(SimpleTestCase):
    def test_declared_business_shift_is_only_a_schedule_claim(self):
        weekly = {"mon": {"status": "declared", "shifts": [
            {"start_time": "09:00:00", "end_time": "17:00:00"}
        ]}}
        opened = opening_status(weekly, datetime(2026, 10, 19, 12, tzinfo=TEHRAN))
        closed = opening_status(weekly, datetime(2026, 10, 19, 19, tzinfo=TEHRAN))
        self.assertEqual(opened["status"], "open")
        self.assertEqual(closed["status"], "closed")
        self.assertIn("طبق برنامه", opened["label"])

    def test_overnight_shift_remains_open_early_next_day(self):
        weekly = {
            "mon": {"status": "declared", "shifts": [
                {"start_time": "20:00:00", "end_time": "02:00:00"}]},
            "tue": {"status": "closed"},
        }
        self.assertEqual(
            opening_status(weekly, datetime(2026, 10, 20, 1, tzinfo=TEHRAN))["status"],
            "open",
        )
        self.assertEqual(
            opening_status(weekly, datetime(2026, 10, 20, 3, tzinfo=TEHRAN))["status"],
            "closed",
        )

    def test_unknown_and_zero_length_placeholder_are_not_marked_closed(self):
        self.assertEqual(opening_status({})["status"], "unknown")
        self.assertEqual(opening_status({"tue": {"status": "unsupported"}})["status"], "unknown")
        placeholder = {"mon": {"status": "declared", "shifts": [
            {"start_time": "00:00:00", "end_time": "00:00:00"}
        ]}}
        self.assertEqual(
            opening_status(placeholder, datetime(2026, 10, 19, 12, tzinfo=TEHRAN))["status"],
            "unknown",
        )

    def test_explicit_holiday_closed_is_schedule_based(self):
        self.assertEqual(
            opening_status({"fri": {"status": "closed"}},
                           datetime(2026, 10, 23, 11, tzinfo=TEHRAN))["status"],
            "closed",
        )


class IndoorAddressHintsTests(SimpleTestCase):
    def test_only_existing_mall_floor_unit_appear(self):
        source = "تهران، خیابان نمونه، پاساژ پردیس، طبقه دوم، واحد ۲۱"
        self.assertEqual(indoor_address_hints(source), {
            "mall": "پاساژ پردیس", "floor": "طبقه دوم", "unit": "واحد ۲۱",
        })

    def test_no_floor_is_not_invented(self):
        self.assertEqual(indoor_address_hints("تهران، پاساژ نمونه"), {"mall": "پاساژ نمونه"})
        self.assertEqual(indoor_address_hints(None), {})

    def test_no_comma_before_floor_does_not_turn_floor_into_mall(self):
        result = indoor_address_hints("پاساژ نمونه طبقه اول واحد ۳")
        self.assertEqual(result["mall"], "پاساژ نمونه")
        self.assertEqual(result["floor"], "طبقه اول")
        self.assertEqual(result["unit"], "واحد ۳")
