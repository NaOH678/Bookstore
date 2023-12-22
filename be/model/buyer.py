import uuid
import json
import logging
from be.model import db_conn
from be.model import error
import pymysql
from datetime import datetime
from unittest.mock import patch


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(
        self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""

        cursor = self.conn.cursor()
        
        if not self.user_id_exist(user_id):
            return error.error_non_exist_user_id(user_id) + (order_id,)
        if not self.store_id_exist(store_id):
            return error.error_non_exist_store_id(store_id) + (order_id,)
        uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

        sql_get_book = ('SELECT book_id, stock_level, price FROM store '
                         'WHERE store_id = %s AND book_id = %s')

        sql_update_stock = ('UPDATE store SET stock_level = stock_level - %s '
                            'WHERE store_id = %s and book_id = %s and stock_level >= %s')

        sql_insert_order = ('INSERT INTO new_order(order_id, user_id, store_id, time, status) '
                            'VALUES (%s, %s, %s, %s, %s)')

        sql_insert_detail = ('INSERT INTO orders(order_id, book_id, count, price) '
                             'VALUES (%s, %s, %s, %s)')
        try:
            cursor.execute("START TRANSACTION")
            cursor.execute(sql_insert_order, (uid, user_id, store_id, datetime.now(), 0))

            for book_id, count in id_and_count:
                cursor.execute(sql_get_book, (store_id, book_id))

            
                row = cursor.fetchone()
                if row is None:
                    self.conn.rollback()
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = row[1]
                price = row[2]

                if stock_level < count:
                    self.conn.rollback()
                    return error.error_stock_level_low(book_id) + (order_id,)

                cursor.execute(sql_update_stock, (count, store_id, book_id, count))

                cursor.execute(sql_insert_detail, (uid, book_id, count, price))

            # with patch.object(cursor, 'execute', side_effect=pymysql.Error("Mocked error")):
            #     cursor.execute("SELECT * FROM your_table")

            self.conn.commit()
            order_id = uid

        # except pymysql.Error as e:
        #     self.conn.rollback()
        #     logging.info("528, {}".format(str(e)))
        #     return 528, "{}".format(str(e)), ""
        except Exception as e:
            self.conn.rollback()
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""
        
        return 200, "ok", order_id
                

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):

        cursor = self.conn.cursor()

        sql_get_order_id = 'SELECT user_id, store_id FROM new_order WHERE order_id = %s AND status = %s'

        cursor.execute(sql_get_order_id, (order_id, 0))
        row = cursor.fetchone()
        if row is None:
            return error.error_invalid_order_id(order_id)

        buyer_id = row[0]
        store_id = row[1]

        sql_get_user = 'SELECT balance, password FROM user WHERE user_id = %s'
        cursor.execute(sql_get_user, (buyer_id,))
        row = cursor.fetchone()

        balance = row[0]

        if not password == row[1]:
            return error.error_authorization_fail()

        sql_get_seller = 'SELECT user_id, store_id FROM user_store WHERE store_id = %s'
        cursor.execute(sql_get_seller, (store_id,))
        row = cursor.fetchone()

        seller_id = row[0]

        # 得到orders中所有对应订单的项
        sql_get_all_orders = 'SELECT count, price FROM orders WHERE order_id = %s'

        cursor.execute("START TRANSACTION")
        # 买家付钱
        sql_pay = 'UPDATE user SET balance = balance - %s WHERE user_id = %s AND balance >= %s'

        # 卖家收钱
        sql_get_money = 'UPDATE user SET balance = balance + %s WHERE user_id = %s'

        # 更新订单状态
        sql_update_status = 'UPDATE new_order SET status = %s WHERE order_id = %s'

        try:
            cursor.execute(sql_get_all_orders, (order_id,))

            total_price = 0
            for row in cursor:
                count = row[0]
                price = row[1]
                total_price = total_price + price * count

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            # 
            cursor.execute(sql_pay, (total_price, user_id, total_price))
            if cursor.rowcount == 0:
                self.conn.rollback()
                return error.error_not_sufficient_funds(order_id)

            cursor.execute(sql_get_money, (total_price, seller_id))

            # 更新订单状态
            cursor.execute(sql_update_status, (1, order_id))

            self.conn.commit()

        # except pymysql.Error as e:
        #     self.conn.rollback()
        #     return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))
        # finally:
        #     cursor.close()
        return 200, "ok"


    def add_funds(self, user_id, password, add_value) -> (int, str):
        cursor = self.conn.cursor()

        sql_password = 'SELECT password from user where user_id = %s'

        sql_change = 'UPDATE user SET balance = balance + %s WHERE user_id = %s'
        try:
            cursor.execute(sql_password, (user_id,))

            row = cursor.fetchone()
            if row is None:
                return error.error_non_exist_user_id(user_id)

            if row[0] != password:
                return error.error_authorization_fail()

            cursor.execute("START TRANSACTION")
            cursor.execute(sql_change, (add_value, user_id))

            self.conn.commit()
        # except pymysql.Error as e:
        #     self.conn.rollback()
        #     return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))
        # finally:
        #     cursor.close()
        return 200, "ok"
    


    def cancel_order(self, user_id, password, order_id) -> (int, str):
        cursor = self.conn.cursor()

        sql_password = 'SELECT password FROM user WHERE user_id = %s'
        sql_get_order = ('SELECT user_id, status, store_id FROM new_order WHERE order_id = %s')
        sql_update_status = 'UPDATE new_order SET status = %s WHERE order_id = %s'
        sql_get_books = 'SELECT book_id, count, price FROM orders WHERE order_id = %s'
        sql_get_seller = 'SELECT user_id FROM user_store WHERE store_id = %s'
        sql_update_money = 'UPDATE user SET balance = balance + %s WHERE user_id = %s'
        sql_update_stock = 'UPDATE store SET stock_level = stock_level + %s WHERE store_id = %s AND book_id = %s'

        cursor.execute(sql_password, (user_id,))

        row = cursor.fetchone()
        if row is None:
            return error.error_authorization_fail()

        if row[0] != password:
            return error.error_authorization_fail()

        cursor.execute(sql_get_order, (order_id,))
        row = cursor.fetchone()
        if row is None:
            return error.error_invalid_order_id(order_id)

        status = row[1]
        store_id = row[2]

        try:

            cursor.execute("START TRANSACTION")

            if status == -1:
                return error.error_invalid_order_id(order_id)
            elif status == 2:
                return error.error_order_delivered(order_id)
            elif status == 3:
                return error.error_order_was_received(order_id)

            cursor.execute(sql_get_books, (order_id,))
            book_info = []
            row = cursor.fetchall()
            for each_book in row:
                tmp = {"book_id": each_book[0], "count": each_book[1], "price": each_book[2]}
                book_info.append(tmp)

            cursor.execute(sql_get_seller, (store_id,))
            row = cursor.fetchone()
            seller_id = row[0]

            total_price = 0
            for each_book in book_info:
                cursor.execute(sql_update_stock, (each_book['count'], store_id, each_book['book_id']))
                total_price += each_book['count'] * each_book['price']

            if status == 1:
                cursor.execute(sql_update_money, (total_price, user_id))
                cursor.execute(sql_update_money, (-total_price, seller_id))

            cursor.execute(sql_update_status, (-1, order_id))
            self.conn.commit()
        # except pymysql.Error as e:
        #     self.conn.rollback()
        #     return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))
        # finally:
        #     cursor.close()
        return 200, "ok"

    def receive_order(self, user_id, password, order_id) -> (int, str):
        cursor = self.conn.cursor()

        sql_password = 'SELECT password from user where user_id = %s'
        sql_get_order = 'SELECT user_id, status from new_order where order_id = %s'
        sql_update_status = 'UPDATE new_order SET status = %s WHERE order_id = %s'

        cursor.execute(sql_password, (user_id,))

        row = cursor.fetchone()
        if row is None:
            return error.error_authorization_fail()

        if row[0] != password:
            return error.error_authorization_fail()

        cursor.execute(sql_get_order, (order_id,))
        row = cursor.fetchone()
        if row is None:
            return error.error_invalid_order_id(order_id)

        status = row[1]

        if status == -1:
            return error.error_invalid_order_id(order_id)
        elif status == 0:
            return error.error_order_not_paid(order_id)
        elif status == 1:
            return error.error_order_not_delivered(order_id)

        try:
            cursor.execute("START TRANSACTION")
            cursor.execute(sql_update_status, (3, order_id))

            self.conn.commit()
        # except pymysql.Error as e:
        #     self.conn.rollback()
        #     return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))
        # finally:
        #     cursor.close()
        return 200, "ok"

    def search_book(self, keywords, method: str = 'title', store_id: str = None, skip: int = 0):
        valid_method = ['title', 'tags', 'author', 'book_intro']
        limit = 20
        if method not in valid_method:
            return error.error_invalid_search_method(method)

        if store_id is not None and not self.store_id_exist(store_id):
            return error.error_non_exist_store_id(store_id)

        sql_search = 'SELECT book_id FROM store WHERE %s like %s '
        if store_id is not None:
            sql_search += 'AND store_id = %s'

        sql_search += ' LIMIT %s, %s'

        cursor = self.conn.cursor()

        try:
            if store_id is not None:
                cursor.execute(sql_search, (method, keywords, store_id, skip * limit, limit))
            else:
                cursor.execute(sql_search, (method, keywords, skip * limit, limit))
        # except pymysql.Error as e:
        #     self.conn.rollback()
        #     return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))
        # finally:
        #     cursor.close()
        return 200, "ok"

    def search_order(self, user_id: str, password: str):
        cursor = self.conn.cursor()
        sql_get_user = 'SELECT password FROM user WHERE user_id = %s'
        cursor.execute(sql_get_user, (user_id,))
        row = cursor.fetchone()

        if row is None:
            return error.error_non_exist_user_id(user_id)

        if not password == row[0]:
            return error.error_authorization_fail()

        sql_get_order = ('SELECT * FROM new_order LEFT JOIN orders ON new_order.order_id = orders.order_id '
                         'WHERE new_order.user_id = %s  ')
        try:
            cursor.execute(sql_get_order, (user_id,))

            row = cursor.fetchall()
        # except pymysql.Error as e:
        #     self.conn.rollback()
        #     return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))
        # finally:
        #     cursor.close()
        return 200, "ok"
