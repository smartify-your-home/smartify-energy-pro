"""Offline tests for PV surfaces drawn in the editor (geometry, validation, migration)."""
import importlib.util
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1] / "custom_components/smartify_energy/pv_layout.py"
spec = importlib.util.spec_from_file_location("pv_layout_test", file)
pv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pv)

LAT, LON = 47.98, 13.25  # Straßwalchen area
M_LAT = 1 / 111_320  # ~1 m in degrees latitude
M_LON = M_LAT / 0.6692  # ~1 m in degrees longitude at 48°


def pt(east_m, north_m):
    return [LAT + north_m * M_LAT, LON + east_m * M_LON]


# Rectangle 10 m (east-west) × 6 m (north-south); edge 0 = south side (west→east)
RECT = [pt(0, 0), pt(10, 0), pt(10, 6), pt(0, 6)]


class GeometryTests(unittest.TestCase):
    def test_outward_normal_of_marked_eave(self):
        self.assertAlmostEqual(pv.area_outward_azimuth(RECT, 0), 180, delta=0.5)  # south side
        self.assertAlmostEqual(pv.area_outward_azimuth(RECT, 1), 90, delta=0.5)   # east side
        self.assertAlmostEqual(pv.area_outward_azimuth(RECT, 2), 0, delta=0.5)    # north side
        self.assertAlmostEqual(pv.area_outward_azimuth(RECT, 3), 270, delta=0.5)  # west side
        self.assertAlmostEqual(pv.area_outward_azimuth(RECT, 0, flip=True), 0, delta=0.5)

    def test_orientation_independent_of_drawing_direction(self):
        ccw = list(reversed(RECT))  # edge 2 is now the south side drawn east→west
        self.assertAlmostEqual(pv.area_outward_azimuth(ccw, 2), 180, delta=0.5)

    def test_rotated_roof(self):
        # Edge running south-west → north-east, polygon to the north-west: faces south-east (135°)
        roof = [pt(0, 0), pt(7.07, 7.07), pt(2.83, 11.31), pt(-4.24, 4.24)]
        self.assertAlmostEqual(pv.area_outward_azimuth(roof, 0), 135, delta=0.5)

    def test_area_and_default_edge(self):
        self.assertAlmostEqual(pv.projected_area_m2(RECT), 60, delta=0.5)
        self.assertEqual(pv.default_edge(RECT), 0)  # long edge facing south

    def test_line_defaults_to_southern_normal_and_flips(self):
        facade = [pt(0, 0), pt(10, 0)]
        self.assertAlmostEqual(pv.line_azimuth(facade), 180, delta=0.5)
        self.assertAlmostEqual(pv.line_azimuth(facade, flip=True), 0, delta=0.5)

    def test_tile_grid_centres_point(self):
        x, y = pv.tile_xy(LAT, LON, 19)
        grid = pv.tile_grid(LAT, LON, 19, 5)
        self.assertEqual(len(grid), 25)
        self.assertIn((int(x), int(y)), grid)
        self.assertEqual(grid[12], (int(x), int(y)))


class ValidationTests(unittest.TestCase):
    def base(self, **kw):
        return {"id": "a1", "name": "Süd", "kind": "area", "points": RECT, "edge": 0,
                "tilt": 35, "input": "kwp", "kwp": 3.04, **kw}

    def test_area_surface_is_normalized(self):
        s = pv.normalize_surface(self.base())
        self.assertAlmostEqual(s["azimuth"], 180, delta=0.5)
        self.assertAlmostEqual(s["area_m2"], 60, delta=0.5)
        self.assertEqual(pv.effective_kwp(s), 3.04)

    def test_client_azimuth_is_ignored_for_drawn_surfaces(self):
        s = pv.normalize_surface(self.base(azimuth=42))
        self.assertAlmostEqual(s["azimuth"], 180, delta=0.5)

    def test_modules_times_watt_peak(self):
        s = pv.normalize_surface(self.base(input="modules", modules=8, module_wp=380))
        self.assertAlmostEqual(pv.effective_kwp(s), 3.04)
        self.assertEqual(pv.model_surfaces([s])[0]["kwp"], 3.04)

    def test_invalid_values_are_rejected(self):
        for bad in (self.base(tilt=95), self.base(kwp=0), self.base(points=RECT[:2]),
                    self.base(input="modules", modules=2.5, module_wp=400),
                    self.base(points=[RECT[0], RECT[0], RECT[1]]), self.base(id="x y"),
                    self.base(kind="line", points=RECT[:3])):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                pv.normalize_surface(bad)

    def test_closing_click_on_start_point_is_not_a_corner(self):
        closing = [*RECT, pt(0.05, 0.1)]  # 11 cm from the first point
        s = pv.normalize_surface(self.base(points=closing, edge=4))
        self.assertEqual(len(s["points"]), 4)
        self.assertEqual(s["edge"], 0)  # edge 4 no longer exists → default (south)
        self.assertAlmostEqual(s["azimuth"], 180, delta=0.5)
        far = [*RECT, pt(-1, 3)]  # a real fifth corner stays
        self.assertEqual(len(pv.normalize_surface(self.base(points=far))["points"]), 5)

    def test_max_four_and_unique_ids(self):
        many = [self.base(id=f"s{i}") for i in range(5)]
        with self.assertRaises(ValueError):
            pv.normalize_surfaces(many)
        with self.assertRaises(ValueError):
            pv.normalize_surfaces([self.base(), self.base()])
        self.assertEqual(pv.normalize_surfaces([]), [])

    def test_manual_surface_keeps_entered_azimuth(self):
        s = pv.normalize_surface({"id": "m", "kind": "manual", "tilt": 90, "azimuth": 265,
                                  "input": "kwp", "kwp": 1.14})
        self.assertEqual((s["azimuth"], s["points"]), (265, []))


class MigrationTests(unittest.TestCase):
    LEGACY = {"solar_1_kwp": 3.04, "solar_1_tilt": 90, "solar_1_azimuth": 190,
              "solar_2_kwp": 0, "solar_3_kwp": 2.66, "solar_3_tilt": 35, "solar_3_azimuth": 265}

    def test_legacy_fields_become_manual_surfaces(self):
        surfaces = pv.surfaces_from_config(self.LEGACY)
        self.assertEqual([(s["kind"], s["kwp"], s["tilt"], s["azimuth"]) for s in surfaces],
                         [("manual", 3.04, 90, 190), ("manual", 2.66, 35, 265)])
        self.assertEqual(pv.model_surfaces(surfaces),
                         [{"kwp": 3.04, "tilt": 90, "azimuth": 190}, {"kwp": 2.66, "tilt": 35, "azimuth": 265}])

    def test_stored_surfaces_win_over_legacy_fields(self):
        stored = [pv.normalize_surface({"id": "a", "kind": "area", "points": RECT, "tilt": 30,
                                        "input": "kwp", "kwp": 5})]
        cfg = {**self.LEGACY, pv.CONF_SOLAR_SURFACES: stored}
        self.assertEqual([s["id"] for s in pv.surfaces_from_config(cfg)], ["a"])
        self.assertEqual(pv.surfaces_from_config({**self.LEGACY, pv.CONF_SOLAR_SURFACES: []}), [])

    def test_mirror_keeps_downgrade_working_and_clears_unused_slots(self):
        stored = [pv.normalize_surface({"id": "a", "kind": "manual", "tilt": 30, "azimuth": 200,
                                        "input": "modules", "modules": 10, "module_wp": 400})]
        mirror = pv.legacy_mirror(stored)
        self.assertEqual((mirror["solar_1_kwp"], mirror["solar_1_tilt"], mirror["solar_1_azimuth"]), (4.0, 30, 200))
        self.assertEqual([mirror[f"solar_{i}_kwp"] for i in (2, 3, 4)], [0.0, 0.0, 0.0])
        self.assertEqual(len(pv.legacy_surfaces(mirror)), 1)


if __name__ == "__main__":
    unittest.main()
