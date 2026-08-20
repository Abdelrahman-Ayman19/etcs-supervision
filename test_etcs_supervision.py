# the file name must start with test!!

import unittest
import numpy as np
from etcs_supervision import SupervisionConfig, emergency_brake_curve, find_violations, permitted_speed, read_run_csv, write_run_csv, simulate_run
import os
import tempfile


class TestBrackingAndPermission(unittest.TestCase):  # the test class have to start with Test!! and must have: unittest.TestCase
    def setUp(self): #setUp builds the test state for every single testcase so tests can't contaminate each other
        self.cfg = SupervisionConfig(eoa_m=1000.0, decel_ms2=0.5, reaction_s=3.0)
    
    def test_speed_is_zero_at_eoa(self):  # the test functions have to start with test!!
        self.assertAlmostEqual(float(emergency_brake_curve(1000.0, self.cfg)), 0.0)

    def test_negative_decel_rejected(self):
        with self.assertRaises(ValueError):   # the test passes because a ValueError is raised in the file SupervisionConfig is imported from
            SupervisionConfig(decel_ms2=-2.0)  

    def test_is_speed_right(self):
        self.assertAlmostEqual(float(emergency_brake_curve(100.0, self.cfg)), 30.0)
    
    def test_curve_decrease(self):
        self.assertGreater(float(emergency_brake_curve(100.0,self.cfg)),
                            float(emergency_brake_curve(300.0,self.cfg)))
        self.assertGreater(float(emergency_brake_curve(300.0,self.cfg)),
                            float(emergency_brake_curve(500.0,self.cfg)))
        self.assertGreater(float(emergency_brake_curve(500.0,self.cfg)),
                            float(emergency_brake_curve(900.0,self.cfg)))
    
    def test_after_eoa(self):
        self.assertAlmostEqual(float(emergency_brake_curve(1500.0, self.cfg)), 0.0)

    def test_reac_is_zero(self):
        self.cfg_2 = SupervisionConfig(eoa_m=1000.0, decel_ms2=0.5, reaction_s=0.0)
        self.assertAlmostEqual(float(emergency_brake_curve(500.0, self.cfg_2)), float(permitted_speed(500.0, self.cfg_2)))

    def test_per_smaller_emerg(self):
        self.assertGreater(float(emergency_brake_curve(500.0, self.cfg)), float(permitted_speed(500.0, self.cfg)))

class TestViolationDection(unittest.TestCase):
    def setUp(self):
        self.distance = np.array([0.0, 10.0, 20.0, 30.0, 40.0, 50.0])
        self.limit = np.full(6, 20.0)

    def test_no_violation_run(self):
        speed_ok = np.full(6, 19.5)
        self.assertFalse(find_violations(self.distance, speed_ok, self.limit))  # an empty list is a boolean False
        # or self.assertEqual(len(find_violations(distance, speed_ok, limit)), 0.0)
        # or self.assertEqual(find_violations(distance, speed_ok, limit), [])

    def test_single_violation_window(self):
        speed = np.array([19.0, 19.0, 22.0, 25.0, 19.0, 19.0])
        violations = find_violations(self.distance, speed, self.limit)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].start_m, 20.0)
        self.assertEqual(violations[0].end_m, 30.0)
        self.assertAlmostEqual(violations[0].max_excess_ms, 5.0)
        self.assertEqual(violations[0].at_m, 30.0)

    def test_two_separate_violations(self):
        speed = np.array([25.0, 19.0, 19.0, 22.0, 19.0, 19.0])
        self.assertEqual(len(find_violations(self.distance, speed, self.limit)), 2)

    def test_violation_open_at_the_end(self):
        speed = np.array([19.0, 19.0, 19.0, 19.0, 21.0, 23.0])
        violations = find_violations(self.distance, speed, self.limit)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].end_m, 50.0)

    def test_tolerance_suppresses_small_excess(self):
        speed = np.full(6, 20.5)
        self.assertEqual(find_violations(self.distance, speed, self.limit, tolerance_ms=1.0), [])

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            find_violations(self.distance, np.zeros(5), self.limit)

class TestCsv(unittest.TestCase):
    def test_csv_roundtrip_keeps_values(self):
        distance = np.array([0.0, 10.0, 20.0, 30.0])
        speed = np.array([19.0, 22.0, 25.0, 19.0])
        time = np.arange(len(speed)) * 0.2  # 0.2 steps: 0.0, 0.2, 0.4, ...

        with tempfile.TemporaryDirectory() as tmp:   # creates a throwaway directory and deletes it (and everything in it) when the with block exits. 
            path = os.path.join(tmp, "run.csv")
            write_run_csv(path, time, distance, speed)
            t2, d2, v2 = read_run_csv(path)
        
        np.testing.assert_allclose(distance, d2, atol=1e-3)   # atol is the tolerance
        np.testing.assert_allclose(speed, v2, atol=1e-3)  

    def test_empty_csv_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "empty.csv")
            with open(path, "w", newline="", encoding="utf-8") as fh:
                fh.write("time_s, distance_m, speed_ms \n")
            with self.assertRaises(ValueError):    # this csv has a header but no data. so  if not rows: raise ValueError(f"{path} enthaelt keine Daten") raises a ValueError
                read_run_csv(path) 

class TestSim(unittest.TestCase):
    def setUp(self):
        self.cfg = SupervisionConfig()

    def test_simulated_run_is_plausible(self):
        time, distance, speed = simulate_run(self.cfg, brake_at_m=600.0)
        self.assertTrue(np.all(np.diff(distance) >= 0.0))   # distance only increase
        self.assertTrue(np.all(speed >= 0.0))
        self.assertAlmostEqual(speed[-1], 0.0)  # last speed is zero

    def test_late_braking_cause_violation(self):
        time, distance, speed = simulate_run(self.cfg, brake_at_m= 1600.0)  # eoa is 2000 so 1600 is mostly too late
        limit = permitted_speed(distance, self.cfg)
        self.assertTrue(find_violations(distance, speed, limit))  # there should be a violations

    def test_early_braking_cause_no_violations(self):
        time, distance, speed = simulate_run(self.cfg, brake_at_m= 600.0, brake_decel_ms2= 0.8)
        limit = permitted_speed(distance, self.cfg)
        self.assertEqual(find_violations(distance, speed, limit), [])




if __name__ == "__main__":
    unittest.main(verbosity=2)