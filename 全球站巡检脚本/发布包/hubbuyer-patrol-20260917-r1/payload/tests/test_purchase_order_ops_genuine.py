# -*- coding: utf-8 -*-
import os
import sys
import unittest
from unittest.mock import Mock, patch


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from checker.api.purchase_order_ops import (
    _detail_has_expected_genuine_qty,
    _find_detail_item,
    _is_genuine_fjx_sync_failure,
    _execute_genuine_step,
)


class PurchaseOrderGenuineTest(unittest.TestCase):
    def execute_responses(self, bodies, verified=(True, "quantity verified"), detail_ids="1"):
        responses = []
        for body in bodies:
            response = Mock(status_code=200)
            response.json.return_value = body
            responses.append(response)
        module = "checker.api.purchase_order_ops"
        with patch(module + ".requests.post", side_effect=responses) as post, \
             patch(module + ".time.sleep") as sleep, \
             patch(module + ".AssertionTool.verify_api_common", side_effect=lambda response, **kwargs: {"success": response.json().get("code") == 200, "message": "code mismatch"}), \
             patch(module + "._build_audit_headers", return_value={}), \
             patch(module + "._verify_genuine_written_after_fjx_sync_failure", return_value=verified):
            result = _execute_genuine_step(
                "test", "order-test", {"seller_open_id": "seller", "seller_name": "seller", "order_detail_ids": detail_ids},
                {"enabled": True, "url": "https://example.test/genuine"}, "genuine", {}, {},
            )
        return result, post, sleep

    def test_transient_failure_retries_same_payload_and_records_warning(self):
        result, post, sleep = self.execute_responses([
            {"code": 40000, "message": "正品更新附加项数量失败"}, {"code": 200},
        ])
        self.assertTrue(result["success"])
        self.assertIn("首次失败", result["message"])
        self.assertIn("重试1次成功", result["message"])
        self.assertEqual(post.call_args_list[0], post.call_args_list[1])
        sleep.assert_called_once_with(1.2)

    def test_persistent_failure_is_not_hidden_by_existing_quantity(self):
        result, post, sleep = self.execute_responses([
            {"code": 40000, "message": "正品更新附加项数量失败"},
            {"code": 40000, "message": "正品更新附加项数量失败"},
        ])
        self.assertFalse(result["success"])
        self.assertIn("重试1次仍失败", result["message"])
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once()

    def test_retry_success_requires_quantity_verification(self):
        result, _, _ = self.execute_responses([
            {"code": 40000, "message": "正品更新附加项数量失败"}, {"code": 200},
        ], verified=(False, "quantity mismatch"))
        self.assertFalse(result["success"])
        self.assertIn("quantity mismatch", result["message"])

    def test_other_failure_does_not_retry(self):
        result, post, sleep = self.execute_responses([{"code": 40000, "message": "未到货"}])
        self.assertFalse(result["success"])
        self.assertEqual(post.call_count, 1)
        sleep.assert_not_called()

    def test_successful_detail_is_not_replayed_for_other_details(self):
        result, post, sleep = self.execute_responses([
            {"code": 200}, {"code": 40000, "message": "正品更新附加项数量失败"}, {"code": 200},
        ], detail_ids="1,2")
        self.assertTrue(result["success"])
        self.assertEqual([call.kwargs["json"]["order_detail_id"] for call in post.call_args_list], [1, 2, 2])
        sleep.assert_called_once()

    def test_pending_quantity_is_excluded(self):
        item = {"arrive_qty": 5, "bad_qty": 1, "wait_qty": 2, "genuine_qty": 2}
        self.assertEqual(_detail_has_expected_genuine_qty(item), (True, 2, 2))

    def test_existing_genuine_quantity_cannot_hide_failed_request(self):
        response = Mock()
        response.json.return_value = {"code": 40000, "message": "正品更新附加项数量失败"}
        module = "checker.api.purchase_order_ops"
        with patch(module + ".requests.post", return_value=response), \
             patch(module + ".AssertionTool.verify_api_common", return_value={"success": False, "message": "code mismatch"}), \
             patch(module + "._build_audit_headers", return_value={}), \
             patch(module + "._verify_genuine_written_after_fjx_sync_failure", return_value=(True, "existing genuine quantity")):
            result = _execute_genuine_step(
                "test", "order-test", {"seller_open_id": "seller", "seller_name": "seller", "order_detail_ids": "1"},
                {"enabled": True, "url": "https://example.test/genuine"}, "genuine", {}, {},
            )
        self.assertFalse(result["success"])
        self.assertIn("existing genuine quantity", result["message"])

    def test_detects_genuine_fjx_sync_failure_message(self):
        body = {"code": 40000, "message": "正品更新附加项数量失败"}

        self.assertTrue(_is_genuine_fjx_sync_failure(body))

    def test_detail_has_expected_genuine_qty_when_arrived_minus_bad_is_written(self):
        item = {"arrive_qty": "2", "bad_qty": "0", "genuine_qty": "2"}

        self.assertEqual(_detail_has_expected_genuine_qty(item), (True, 2, 2))

    def test_detail_missing_expected_genuine_qty_is_not_recovered(self):
        item = {"arrive_qty": "2", "bad_qty": "0", "genuine_qty": "1"}

        self.assertEqual(_detail_has_expected_genuine_qty(item), (False, 1, 2))

    def test_find_detail_item_filters_by_seller_open_id(self):
        sellers = [
            {
                "seller_open_id": "seller-a",
                "detail_data": [{"id": 7630, "genuine_qty": "2"}],
            },
            {
                "seller_open_id": "seller-b",
                "detail_data": [{"id": 7630, "genuine_qty": "0"}],
            },
        ]

        item = _find_detail_item(sellers, "7630", seller_open_id="seller-a")

        self.assertEqual(item["genuine_qty"], "2")


if __name__ == "__main__":
    unittest.main()
