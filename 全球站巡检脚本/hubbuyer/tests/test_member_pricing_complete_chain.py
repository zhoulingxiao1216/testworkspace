# -*- coding: utf-8 -*-
import os
import sys
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from checker.api.member_pricing_complete_chain import (
    InspectionRecorder,
    flatten_check_fjx_list,
    price_of,
    run_check_fjx_assertions,
    _resolve_login_account,
)


class MemberPricingCompleteChainTest(unittest.TestCase):
    def test_flatten_check_fjx_list_supports_check_fjx_and_user_fjx(self):
        payload = {
            "code": 200,
            "data": {
                "check_data": [{"uuid": "JPT-CHK-002", "user_price": "2.00"}],
                "fjx_data": [
                    {
                        "fjx_config_data": [
                            {
                                "uuid": "JPT-FJX-001",
                                "pricing_source": "country_level",
                                "fee_info": {"user_price": "2.00"},
                            }
                        ]
                    }
                ],
                "user_fjx_data": [
                    {
                        "uuid": "JPT-FJX-016",
                        "pricing_source": "user_custom",
                        "fee_info": [{"user_price": "8.88"}],
                    }
                ],
            },
        }

        flat = flatten_check_fjx_list(payload)

        self.assertEqual(len(flat["checks"]), 1)
        self.assertEqual(len(flat["fjx"]), 1)
        self.assertEqual(len(flat["userFjx"]), 1)
        self.assertEqual(price_of(flat["userFjx"][0]), 8.88)

    def test_check_fjx_assertions_validate_sources_prices_and_forbidden_prices(self):
        flat = flatten_check_fjx_list(
            {
                "data": {
                    "check_data": [{"uuid": "JPT-CHK-002", "pricing_source": "country_level", "user_price": 2}],
                    "fjx_data": [
                        {
                            "fjx_config_data": [
                                {
                                    "uuid": "JPT-FJX-001",
                                    "pricing_source": "country_level",
                                    "fee_info": {"user_price": 2},
                                }
                            ]
                        }
                    ],
                    "user_fjx_data": [
                        {
                            "uuid": "JPT-FJX-016",
                            "pricing_source": "user_custom",
                            "fee_info": {"user_price": 8.88},
                        }
                    ],
                }
            }
        )
        recorder = InspectionRecorder()
        case = {
            "name": "JP user custom",
            "expected": {
                "visibleCheckUuids": ["JPT-CHK-002"],
                "visibleFjxUuids": ["JPT-FJX-001"],
                "visibleUserFjxUuids": ["JPT-FJX-016"],
                "pricingSources": {
                    "check:JPT-CHK-002": "country_level",
                    "fjx:JPT-FJX-001": "country_level",
                    "user_fjx:JPT-FJX-016": "user_custom",
                },
                "prices": {"user_fjx:JPT-FJX-016": 8.88},
                "forbiddenPrices": [99],
                "requirePricingSourceOnPricedItems": True,
            },
        }

        run_check_fjx_assertions(flat, case, recorder)

        result = recorder.to_result("会员价格体系附加项专项巡检")
        self.assertTrue(result["success"])
        self.assertIn("Failed=0", result["message"])

    def test_resolve_login_account_prefers_case_user(self):
        account = _resolve_login_account(
            {"user": {"account": "case@example.com", "password": "secret"}},
            "",
        )

        self.assertEqual(account["email"], "case@example.com")
        self.assertEqual(account["password"], "secret")


if __name__ == "__main__":
    unittest.main()
