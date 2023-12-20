import pytest
import uuid
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer


class TestSearchBook:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.seller_id = "test_payment_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_payment_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_payment_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.seller_id
        gen_book = GenBook(self.seller_id, self.store_id)
        ok, buy_book_id_list = gen_book.gen(
            non_exist_book_id=False, low_stock_level=False, max_book_count=5
        )
        self.buy_book_info_list = gen_book.buy_book_info_list
        b = register_new_buyer(self.buyer_id, self.password)
        self.buyer = b
        assert ok

    def test_ok_no_store(self):
        code = self.buyer.search_book("title", "test")
        assert code == 200

    def test_ok_store(self):
        code = self.buyer.search_book("title", "test", self.store_id)
        assert code == 200

    def test_not_exist_store(self):
        self.store_id = self.store_id + "_x"
        code = self.buyer.search_book("title", "test", self.store_id)
        assert code != 200

