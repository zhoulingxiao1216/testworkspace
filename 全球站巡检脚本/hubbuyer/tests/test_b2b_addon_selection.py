# -*- coding: utf-8 -*-
import os
import sys
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from checker.api.B2B_Addon import _configured_runtime_selection


class B2BAddonSelectionTest(unittest.TestCase):
    def test_configured_selection_keeps_only_runtime_available_uuids(self):
        check_items = [
            {"uuid": "OLD-CHECK", "status": 200},
            {"uuid": "JPT-CHK-002", "status": 200},
        ]
        groups = [
            {
                "fjx_config_data": [
                    {"uuid": "F25-0617-7670", "status": 200},
                    {"uuid": "JPT-FJX-017", "status": 200},
                    {"uuid": "HIDDEN-FJX", "status": 100},
                ]
            }
        ]
        user_fjx_items = [{"uuid": "USER-FJX-001", "status": 200}]
        config = {
            "check_config_uuid": ["MISSING-CHECK", "JPT-CHK-002"],
            "fjx_config_uuid_arr": [
                "HIDDEN-FJX",
                "F25-0617-7670",
                "F25-0617-7670",
                "MISSING-FJX",
                "JPT-FJX-017",
            ],
            "user_fjx_config_uuid_arr": ["USER-FJX-001", "MISSING-USER-FJX"],
        }

        check_uuid, selected_fjx, selected_user_fjx = _configured_runtime_selection(
            config,
            check_items,
            groups,
            user_fjx_items,
        )

        self.assertEqual(check_uuid, "JPT-CHK-002")
        self.assertEqual(selected_fjx, ["F25-0617-7670", "JPT-FJX-017"])
        self.assertEqual(selected_user_fjx, ["USER-FJX-001"])

    def test_configured_selection_falls_back_to_first_check(self):
        check_uuid, selected_fjx, selected_user_fjx = _configured_runtime_selection(
            {"check_config_uuid": ["MISSING-CHECK"]},
            [{"uuid": "JPT-CHK-002", "status": 200}],
            [],
            [],
        )

        self.assertEqual(check_uuid, "JPT-CHK-002")
        self.assertEqual(selected_fjx, [])
        self.assertEqual(selected_user_fjx, [])


if __name__ == "__main__":
    unittest.main()
