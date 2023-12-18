from be.model import store


class DBConn:
    def __init__(self):
        self.conn = store.get_db_conn()

    def user_id_exist(self, user_id):
        cursor = self.conn.cursor()
        sql = "SELECT * FROM user WHERE user_id = %s;"
        cursor.execute(sql, (user_id,))
        row = cursor.fetchone()
        if row is None:
            return False
        else:
            return True

    def book_id_exist(self, store_id, book_id):
        cursor = self.conn.cursor()

        sql = "SELECT * FROM store WHERE store_id = %s AND book_id = %s;"
        cursor.execute(sql, (store_id, book_id))
        row = cursor.fetchone()
        if row is None:
            return False
        else:
            return True

    def store_id_exist(self, store_id):
        cursor = self.conn.cursor()
        
        sql = "SELECT * FROM user_store WHERE store_id = %s;"
        cursor.execute(sql, store_id)
        row = cursor.fetchone()
        if row is None:
            return False
        else:
            return True