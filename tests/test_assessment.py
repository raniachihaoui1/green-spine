import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import LineString, Point, Polygon, box, mapping

from backend import parameters as P
from backend.bomenkaart import baseline_cover_pct
from backend.feasibility import rooting_space, rootable_ground
from backend.metrics.heat import heat_stress
from backend.metrics.water import water_retention
from backend.model import (canopy_accounting, crown_radius, diversity_check, run_option,
                           _species_candidates, survival_share)
from backend.scenarios import load_masterplan, comparison_table, REQUIRED_LAYERS
from backend.view import _model_layers, _model_bounds
from backend.rendering import _surface, scene_package


def site():
    return dict(corridor=box(0, 0, 100, 100), centreline=LineString([(0, 50), (100, 50)]),
                bld_union=Polygon(), buildings=[], road=Polygon(), water=Polygon(),
                utilities=Polygon(), underground=Polygon(), unpaved=Polygon(), wet_zone=Polygon(),
                soil_zones=[], canopy_removals=Polygon(),
                existing=pd.DataFrame(columns=["x", "y", "r", "cover", "in_corridor"]))


def plants():
    return pd.DataFrame([dict(species="A", common_name="A", genus="A", family="A",
                              size_class="small", soil_moisture="dry")])


class FeasibilityTests(unittest.TestCase):
    def test_paved_small_tree_requires_engineering(self):
        L = site()
        root, error = rooting_space(20, 20, "small", True, L, rootable_ground(L), True)
        self.assertIsNone(error)
        self.assertTrue(root["engineered"])
        self.assertEqual(root["depth_evidence"], "assumed")
        self.assertEqual(root["feasibility"], "conditional")
        self.assertIsNone(rooting_space(20, 20, "small", True, L, rootable_ground(L), False)[0])

    def test_insufficient_measured_depth_is_not_relaxed(self):
        L = site()
        L["soil_zones"] = [(L["corridor"], {"usable_depth_m": 0.8, "source": "test survey"})]
        self.assertEqual(rooting_space(20, 20, "small", True, L, rootable_ground(L), True)[1],
                         "Insufficient usable rooting depth")

    def test_species_threshold_and_moisture_are_hard_constraints(self):
        self.assertEqual(_species_candidates(plants(), {"A": 0.2}, "small", "dry"), [])
        self.assertEqual(_species_candidates(plants(), {}, "small", "dry"), [])
        self.assertEqual(_species_candidates(plants(), {"A": 0.9}, "small", "wet"), [])

    def test_paved_candidates_are_conditional_and_roots_do_not_overlap(self):
        grid = pd.DataFrame(dict(x=[20.0, 30.0], y=[20.0, 20.0], soil=P.SOIL_PAVED,
                                 paved=True, heat=1.0, dist_canopy=P.GAP_CAP, moisture="dry",
                                 borehole="test", borehole_dist_m=10.0))
        with patch("backend.model.soil_context", return_value={"table": {"test": {"A": 0.9}}}):
            trees = run_option(site(), grid, plants(), dict(heat=1, soil=0, gap=0), 2, enforce=False).trees
        self.assertEqual(len(trees), 2)
        self.assertTrue(trees.engineered.all())
        self.assertTrue(trees.phase.str.startswith("Conditional").all())
        zones = [shapely.from_wkt(g) for g in trees.root_zone_wkt]
        self.assertEqual(zones[0].intersection(zones[1]).area, 0)

    def test_incompatible_candidate_is_rejected_with_reason(self):
        grid = pd.DataFrame(dict(x=[20.0], y=[20.0], soil=P.SOIL_PAVED, paved=True,
                                 heat=1.0, dist_canopy=P.GAP_CAP, moisture="dry",
                                 borehole="test", borehole_dist_m=10.0))
        with patch("backend.model.soil_context", return_value={"table": {"test": {"A": 0.2}}}):
            result = run_option(site(), grid, plants(), dict(heat=1, soil=0, gap=0), 1, enforce=False)
        self.assertTrue(result.trees.empty)
        self.assertIn("compatible", result.rejections[0]["reason"])

    def test_one_tree_cannot_pass_diversity(self):
        self.assertFalse(diversity_check(plants())["ok"])


class MetricTests(unittest.TestCase):
    def test_raster_weights_boundary_intersections(self):
        raster = dict(cover=np.array([[100.0, 0.0]]), cell=10.0, x0=0.0, y0=10.0)
        self.assertAlmostEqual(baseline_cover_pct(raster, box(5, 0, 20, 10)), 100 / 3)

    def test_canopy_counts_documented_loss_not_current_road_overlap(self):
        L = site()
        L["corridor"] = box(0, 0, 10, 10)
        L["raster"] = dict(cover=np.array([[100.0]]), cell=10.0, x0=0.0, y0=10.0)
        L["road"] = L["corridor"]
        self.assertEqual(canopy_accounting(pd.DataFrame(), L, P.DEFAULT_YEAR)["lost_m2"], 0)
        L["canopy_removals"] = box(0, 0, 5, 10)
        self.assertEqual(canopy_accounting(pd.DataFrame(), L, P.DEFAULT_YEAR)["lost_m2"], 50)

    def test_new_crowns_do_not_double_count_existing_canopy(self):
        L = site()
        L["corridor"] = box(0, 0, 10, 10)
        L["raster"] = dict(cover=np.array([[100.0]]), cell=10.0, x0=0.0, y0=10.0)
        tree = pd.DataFrame([dict(x=5, y=5, size_class="small")])
        self.assertAlmostEqual(canopy_accounting(tree, L, P.DEFAULT_YEAR)["total_m2"], 100)

    def test_committed_trees_are_absent_before_planting(self):
        L = site()
        L["committed"] = pd.DataFrame([dict(x=50, y=50, size_class="small", planting_year=P.BASE_YEAR + 5)])
        self.assertEqual(canopy_accounting(pd.DataFrame(), L, P.BASE_YEAR)["total_m2"], 0)
        self.assertGreater(canopy_accounting(pd.DataFrame(), L, P.BASE_YEAR + 5)["total_m2"], 0)

    def test_roof_retention_cannot_exceed_its_rainfall(self):
        L = site()
        L["corridor"] = box(0, 0, 10, 10)
        with patch.object(P, "DESIGN_RAIN_MM", 10), patch.object(P, "CANOPY_GREEN_FRACTION", 1):
            result = water_retention(pd.DataFrame(), L, P.DEFAULT_YEAR, canopies=L["corridor"])
        self.assertAlmostEqual(result["roofs_m3"], 1)
        self.assertAlmostEqual(result["kept_m3"] + result["runoff_m3"], result["storm_m3"])

    def test_water_overlaps_and_fractional_roofs_conserve_rainfall(self):
        L = site()
        L["unpaved"] = L["corridor"]
        roof = box(0, 0, 80, 100)
        with patch.object(P, "CANOPY_RAIN_FACTOR", 0.5):
            result = water_retention(pd.DataFrame(), L, P.DEFAULT_YEAR, canopies=roof, pergola=roof)
        self.assertLessEqual(result["kept_m3"], result["storm_m3"])
        self.assertAlmostEqual(sum(result[k] for k in ("soak_m3", "crowns_m3", "roofs_m3", "runoff_m3")),
                               result["storm_m3"])

    def test_green_over_a_basement_is_unsealed_but_not_assumed_infiltrating(self):
        L = site()
        L["unpaved"] = L["underground"] = L["corridor"]
        result = water_retention(pd.DataFrame(), L, P.DEFAULT_YEAR)
        self.assertEqual(result["unsealed_pct"], 100)
        self.assertEqual(result["soak_m3"], 0)

    def test_zero_and_partial_sun_factors_are_respected(self):
        L = site()
        position = dict(alt=90.0, az=0.0)
        for factor in (0.0, 0.5, 1.0):
            with self.subTest(factor=factor), patch.object(P, "PERGOLA_SUN_FACTOR", factor), \
                 patch("backend.metrics.heat.check_position", return_value=position):
                self.assertAlmostEqual(heat_stress(pd.DataFrame(), L, P.DEFAULT_YEAR,
                                                  pergola=L["corridor"])["shaded_pct"], factor * 100)

    def test_growth_and_survival_have_distinct_meanings(self):
        self.assertEqual(crown_radius(["small"], P.BASE_YEAR)[0], P.PLANTING_RADIUS)
        self.assertGreater(crown_radius(["small"], P.BASE_YEAR + 10)[0], P.PLANTING_RADIUS)
        self.assertLess(crown_radius(["small"], P.BASE_YEAR + 100)[0], P.TREE_CLASSES["small"]["r_mature"])
        t = pd.DataFrame([dict(size_class="small", engineered=True)])
        self.assertEqual(survival_share(t, P.BASE_YEAR), 1)
        self.assertAlmostEqual(survival_share(t, P.BASE_YEAR + P.SURVIVAL_HORIZON_YEARS), P.SURVIVAL_ENGINEERED_SOIL)

    def test_map_crown_height_matches_shadow_envelope(self):
        d = pd.DataFrame([dict(lon=5.48, lat=51.44, r=4.5, scale=[1, 1, 1], label="Test")])
        layer = _model_layers(d, "large_tree", [0, 100, 0])[0]
        row = layer.data[0]
        low, high = _model_bounds("large_tree", "foliage")
        self.assertAlmostEqual(low[1] * row["scale"][1] + row["z"], P.CROWN_BASE * 4.5)
        self.assertAlmostEqual(high[1] * row["scale"][1] + row["z"], P.CROWN_TOP * 4.5)

    def test_render_triangulation_preserves_concavity_and_holes(self):
        footprint = Polygon([(0, 0), (10, 0), (10, 4), (4, 4), (4, 10), (0, 10)],
                            holes=[[(1, 1), (1, 2), (2, 2), (2, 1)]])
        triangles = [Polygon(t) for s in _surface(footprint, (0, 0)) for t in s["triangles"]]
        self.assertAlmostEqual(shapely.union_all(triangles).symmetric_difference(footprint).area, 0)
        self.assertTrue(all(t.exterior.is_ccw for t in triangles))

    def test_render_merges_overlapping_coplanar_building_parts(self):
        L = site()
        L["reference"] = {"source": "Test"}
        L["buildings"] = [(box(0, 0, 10, 10), 10), (box(5, 0, 15, 10), 10)]
        scene = scene_package(L, pd.DataFrame(), P.DEFAULT_YEAR, None, None,
                              {"bands": pd.DataFrame()}, "Test")
        roofs = [s for s in scene["surfaces"] if s["material"] == "building"]
        self.assertEqual(len(roofs), 1)
        self.assertAlmostEqual(sum(Polygon(t).area for t in roofs[0]["triangles"]), 150)


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.L = site()
        self.L["corridor"] = box(160000, 380000, 160100, 380100)
        self.L["centreline"] = LineString([(160000, 380050), (160100, 380050)])
        self.meta = dict(crs="EPSG:28992", name="Test reference", date="2026-01-01",
                         status="documented", source="Unit test, not planning data", layers={})
        for name in REQUIRED_LAYERS:
            features = []
            if name == "centreline":
                features = [dict(type="Feature", geometry=mapping(self.L["centreline"]), properties={})]
            (self.root / f"{name}.geojson").write_text(json.dumps(dict(type="FeatureCollection", features=features)))
            self.meta["layers"][name] = dict(file=f"{name}.geojson", source="Unit test")

    def save(self):
        (self.root / "scenario.json").write_text(json.dumps(self.meta))

    def test_missing_manifest_does_not_invent_a_masterplan(self):
        self.assertIsNone(load_masterplan(self.L, self.root))
        row = dict(canopy_pct=10, shade_3pm_pct=20, rain_kept_pct=10, unsealed_pct=20)
        table = comparison_table(row, None, row)
        self.assertTrue(table["Masterplan"].isna().all())
        self.assertTrue(table["Added Green Spine value"].isna().all())

    def test_complete_reference_keeps_boundary_without_generated_shelters(self):
        self.save()
        plan = load_masterplan(self.L, self.root)
        self.assertTrue(plan["corridor"].equals(self.L["corridor"]))
        self.assertTrue(plan["canopies"].is_empty)
        self.assertTrue(plan["pergola"].is_empty)
        self.assertNotIn("reference", self.L)

    def test_partial_or_wrong_crs_reference_is_rejected(self):
        del self.meta["layers"]["canopy_removals"]
        self.save()
        with self.assertRaisesRegex(ValueError, "needs layers"):
            load_masterplan(self.L, self.root)
        self.meta["crs"] = "EPSG:4326"
        self.save()
        with self.assertRaisesRegex(ValueError, "28992"):
            load_masterplan(self.L, self.root)

    def test_invalid_height_or_geographic_coordinates_rejected(self):
        for geometry, height in ((box(160000, 380000, 160010, 380010), 0),
                                  (box(5, 51, 6, 52), 20)):
            with self.subTest(height=height):
                (self.root / "buildings.geojson").write_text(json.dumps(dict(type="FeatureCollection", features=[
                    dict(type="Feature", geometry=mapping(geometry), properties={"height": height})])))
                self.save()
                with self.assertRaises(ValueError):
                    load_masterplan(self.L, self.root)


if __name__ == "__main__":
    unittest.main()
