from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from backend import workflow as W


class DashboardTests(unittest.TestCase):
    def test_pending_and_imported_reference_states(self):
        W.references.clear()
        with patch.object(W, "load_masterplan", return_value=None):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=120).run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Masterplan geometry pending" in w.value for w in app.warning))
            app.get("segmented_control")[0].set_value("Masterplan").run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.metric), 0)
            app.get("segmented_control")[0].set_value("Existing").run()
            self.assertFalse(app.exception)
            self.assertTrue(len(app.metric))

        def imported(existing):
            plan = deepcopy(existing)
            plan["reference"] = dict(name="Test-only imported reference", status="indicative",
                                     source="Unit test; not planning data", date="2026-11-13")
            point = plan["centreline"].interpolate(plan["centreline"].length / 2)
            plan["committed"] = pd.DataFrame([dict(x=point.x, y=point.y, species="Test tree",
                                                   size_class="small", planting_year=2026)])
            return plan

        with patch.object(W, "load_masterplan", side_effect=imported):
            W.references.clear()
            app.get("segmented_control")[0].set_value("Masterplan").run()
            self.assertFalse(app.exception)
            self.assertFalse(any("geometry pending" in w.value for w in app.warning))
            app.get("segmented_control")[0].set_value("Green Spine").run()
            self.assertFalse(app.exception)
        W.references.clear()
        W.site.clear()


if __name__ == "__main__":
    unittest.main()
