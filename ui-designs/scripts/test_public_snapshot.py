"""Publication boundary regression checks; no real private data in these fixtures."""
import unittest
from prepare_snapshot import KEYS, public_snapshot


class PublicSnapshotTests(unittest.TestCase):
    def test_publication_drops_account_and_sizing_fields(self):
        source = dict.fromkeys(KEYS)
        source.update({
            "positions": [{"sym": "PRIVATE_EXAMPLE", "shares": 123}],
            "capital": 7654321,
            "holdings": ["PRIVATE_EXAMPLE"],
            "details": {"PUBLIC_CO": {
                "score": 70, "private_note": "never publish",
                "plan": {"entry_price": 100, "stop_loss_price": 90,
                         "shares_total": 123, "capital_at_risk": 1230}}},
            "ai_picks": {"picks": [{"plan": {"entry_price": 100, "shares_total": 123}}]},
            "paper": {"equity": 100000, "ledger": [{"notes": "not required"}]},
            "ohlc": {"PUBLIC_CO": list(range(100))},
            "closes": {"PUBLIC_CO": list(range(200))},
        })
        result = public_snapshot(source)
        self.assertEqual(result["positions"], [])
        self.assertNotIn("capital", result)
        self.assertNotIn("holdings", result)
        self.assertNotIn("private_note", result["details"]["PUBLIC_CO"])
        self.assertEqual(result["details"]["PUBLIC_CO"]["plan"], {"entry_price": 100, "stop_loss_price": 90})
        self.assertEqual(result["ai_picks"]["picks"][0]["plan"], {"entry_price": 100})
        self.assertNotIn("ledger", result["paper"])
        self.assertEqual(len(result["ohlc"]["PUBLIC_CO"]), 55)
        self.assertEqual(len(result["closes"]["PUBLIC_CO"]), 120)
        self.assertEqual(source["capital"], 7654321)  # Source remains untouched.


if __name__ == "__main__":
    unittest.main()
