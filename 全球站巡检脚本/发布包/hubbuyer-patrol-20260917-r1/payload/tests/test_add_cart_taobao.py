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

    def test_missing_sku_does_not_substitute_another_product_variant(self):
        self.detail["productSkuInfos"][0]["skuId"] = 789
        with self.assertRaises(ValueError):
            self.refresh({"code": 200, "data": {"data": self.detail}})

    def test_wrong_product_is_rejected(self):
        self.detail["offerId"] = 999
        with self.assertRaises(ValueError):
            self.refresh({"code": 200, "data": {"data": self.detail}})

    def test_detail_failure_preserves_business_message(self):
        with self.assertRaisesRegex(ValueError, "unavailable"):
            self.refresh({"code": 40000, "message": "unavailable"})


if __name__ == "__main__":
    unittest.main()
