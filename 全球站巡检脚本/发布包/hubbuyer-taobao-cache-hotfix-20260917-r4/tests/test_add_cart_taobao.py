import copy
import unittest
from unittest.mock import Mock, patch

from checker.api.add_cart import refresh_taobao_payload


class TaobaoPayloadTests(unittest.TestCase):
    def setUp(self):
        self.payload = {"item_id": "123", "product_index_uuid": "expired", "goods_info": [{"sku_id": "456", "spec_id": "old", "quantity": 2}]}
        self.detail = {"offerId": 123, "product_index_uuid": "current", "productSkuInfos": [{"skuId": 456, "specId": "new"}]}

    def refresh(self, body):
        response = Mock()
        response.json.return_value = body
        with patch("checker.api.add_cart.requests.get", return_value=response):
            return refresh_taobao_payload(self.payload, "https://example.test", {})

    def test_refresh_preserves_sku_quantity_and_source_configuration(self):
        original = copy.deepcopy(self.payload)
        result = self.refresh({"code": 200, "data": {"data": self.detail}})
        self.assertEqual(result["product_index_uuid"], "current")
        self.assertEqual(result["goods_info"], [{"sku_id": 456, "spec_id": "new", "quantity": 2}])
        self.assertEqual(self.payload, original)

    def test_refresh_bypasses_language_specific_cache_and_keeps_headers(self):
        response = Mock()
        response.json.return_value = {"code": 200, "data": {"data": self.detail}}
        headers = {"language": "korean"}
        with patch("checker.api.add_cart.requests.get", return_value=response) as get:
            refresh_taobao_payload(self.payload, "https://example.test", headers)
        self.assertEqual(get.call_args.kwargs["params"], {"item_id": "123", "site": "b2b", "cache": 0})
        self.assertEqual(get.call_args.kwargs["headers"], headers)

    def test_missing_spec_is_not_reported_as_missing_sku(self):
        for spec in (None, "", " "):
            with self.subTest(spec=spec):
                self.detail["productSkuInfos"][0]["specId"] = spec
                with self.assertRaisesRegex(ValueError, "SKU缺少specId"):
                    self.refresh({"code": 200, "data": {"data": self.detail}})

    def test_empty_sku_list_remains_a_failure_after_refresh(self):
        self.detail["productSkuInfos"] = []
        with self.assertRaisesRegex(ValueError, "cache=0 sku_count=0"):
            self.refresh({"code": 200, "data": {"data": self.detail}})

    def test_missing_sku_does_not_substitute_another_product_variant(self):
        self.detail["productSkuInfos"][0]["skuId"] = 789
        with self.assertRaises(ValueError):
            self.refresh({"code": 200, "data": {"data": self.detail}})

    def test_wrong_product_is_rejected(self):
        self.detail["offerId"] = 999
        with self.assertRaises(ValueError):
            self.refresh({"code": 200, "data": {"data": self.detail}})

    def test_index_item_id_is_accepted_when_offer_id_is_absent(self):
        del self.detail["offerId"]
        self.detail["product_index_item_id"] = "123"
        result = self.refresh({"code": 200, "data": {"data": self.detail}})
        self.assertEqual(result["item_id"], "123")

    def test_snake_case_offer_id_is_accepted(self):
        self.detail["offerId"] = None
        self.detail["offer_id"] = "123"
        self.refresh({"code": 200, "data": {"data": self.detail}})

    def test_conflicting_ids_are_rejected_even_with_matching_index(self):
        self.detail["offerId"] = "999"
        self.detail["product_index_item_id"] = "123"
        with self.assertRaisesRegex(ValueError, "requested=123.*999"):
            self.refresh({"code": 200, "data": {"data": self.detail}})

    def test_missing_all_product_ids_is_not_allowed(self):
        del self.detail["offerId"]
        with self.assertRaisesRegex(ValueError, "缺少可核验商品ID"):
            self.refresh({"code": 200, "data": {"data": self.detail}})

    def test_string_ids_are_trimmed(self):
        self.detail["offerId"] = " 123 "
        self.refresh({"code": 200, "data": {"data": self.detail}})

    def test_detail_failure_preserves_business_message(self):
        with self.assertRaisesRegex(ValueError, "unavailable"):
            self.refresh({"code": 40000, "message": "unavailable"})


if __name__ == "__main__":
    unittest.main()
