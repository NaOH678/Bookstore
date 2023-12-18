import logging
import os
import pymysql


class Store:

    # define a variable
    conn: pymysql.Connection
    def __init__(self, host, user, password, database):
        # self.database = os.path.join(db_path, "be.db")
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.init_tables()

    def init_tables(self):

        self.conn = self.get_db_conn()
        cursor = self.conn.cursor()

        # create user table
        """
        primary key : user_id

        """
        sql1 = (
            'CREATE TABLE user ('
            'user_id VARCHAR(300) PRIMARY KEY , password VARCHAR(300), '
            'balance INTEGER, token VARCHAR(500), terminal VARCHAR(500),'
            'INDEX index_user (user_id))'
        )

        # create user_store table   (relation)
        """
        primary key : user_id, store_id
        foreign key : user_id in user_table
        
        """

        sql2 = (
            'CREATE TABLE user_store ('
            'user_id VARCHAR(300), store_id VARCHAR(300) PRIMARY KEY,'
            'FOREIGN KEY (user_id) REFERENCES user(user_id),'
            'INDEX index_store (store_id))'
        )

        # create store table
        """
        primary key : store_id, book_id
        foreign key : store_id in user_store relation
        index on (store_id, book_id), title, tags, author, book_intro

        """
        sql3 = (
            'CREATE TABLE store ('
            'store_id VARCHAR(300), book_id VARCHAR(300), title VARCHAR(100), price INTEGER, '
            'tags VARCHAR(100), author VARCHAR(100),'
            'book_intro VARCHAR(2000),stock_level INTEGER,'
            'PRIMARY KEY (store_id, book_id),'
            'FOREIGN KEY (store_id) REFERENCES user_store(store_id),'
            'INDEX index_store_book (store_id, book_id),' # 加一个复合索引
            'FULLTEXT INDEX index_title(title),'
            'FULLTEXT INDEX index_tags(tags),'
            'FULLTEXT INDEX index_author(author),'
            'FULLTEXT INDEX index_book_intro(book_intro))'
        )

        # create new_order which contains basic information 

        sql4 = (
            'CREATE TABLE new_order ('
            'order_id VARCHAR(300) PRIMARY KEY , user_id VARCHAR(300), store_id VARCHAR(300), '
            'time TIMESTAMP, status INTEGER,'
            'FOREIGN KEY (user_id) REFERENCES user(user_id), '
            'FOREIGN KEY (store_id) REFERENCES user_store(store_id),'
            'INDEX index_order (order_id))'
        )

        # create order table which contains details about order

        sql5 = (
            'CREATE TABLE orders ('
            'order_id VARCHAR(300), book_id VARCHAR(300), count INTEGER, price INTEGER,'
            'FOREIGN KEY (order_id) REFERENCES new_order(order_id),'
            'PRIMARY KEY (order_id, book_id), '
            'INDEX index_order_book (order_id, book_id))'
        )

        try:
            cursor.execute(sql1)
            cursor.execute(sql2)
            cursor.execute(sql3)
            cursor.execute(sql4)
            cursor.execute(sql5)
            
        except pymysql.Error as e:
            logging.error(e)
            self.rollback()

    def get_db_conn(self) -> pymysql.Connection:
        return pymysql.connect(host=self.host, 
                               user=self.user, 
                               password=self.password, 
                               database=self.database)


database_instance: Store = None


def init_database(host, user, password, database):
    global database_instance
    database_instance = Store(host, user, password, database)


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()
