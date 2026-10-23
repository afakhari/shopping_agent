"""No dataset or network needed for hard-filter probe regressions."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from retrieval_benchmark import hard_filter_errors


class RetrievalProbeContracts(unittest.TestCase):
    def test_rejects_budget_and_credit_violations(self):
        case = {"hard_filters": {"max_price_toman": "100", "must_have_in_person_credit": "true"}}
        offers = [{"best_offer": {"id": "o", "shop": {"id": "s"},
                                  "price_toman": "101", "in_person_credit_eligible": False}}]
        self.assertEqual(len(hard_filter_errors(case, offers)), 2)

    def test_accepts_valid_registered_offer(self):
        case = {"hard_filters": {"max_price_toman": "100", "must_have_in_person_credit": "true"}}
        offers = [{"best_offer": {"id": "o", "shop": {"id": "s"},
                                  "price_toman": "100", "in_person_credit_eligible": True}}]
        self.assertEqual(hard_filter_errors(case, offers), [])

    def test_requires_distance_when_radius_selected(self):
        case = {"hard_filters": {"radius_m": 1000}}
        offers = [{"best_offer": {"id": "o", "shop": {"id": "s", "distance_m": None}}}]
        self.assertIn("location radius violation", hard_filter_errors(case, offers))


if __name__ == "__main__":
    unittest.main()
