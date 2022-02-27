from sqlalchemy import create_engine
import pymysql
import pandas as pd

# Connect to the database
DB_CONN = pymysql.connect(host='localhost',
                         user='root',
                         password='123456',
                         db='stockmarket')

cursor=DB_CONN.cursor()


def df_mysql_query(query):
    cursor.execute(query)
    columns = cursor.description
    quote_df = pd.DataFrame.from_dict({columns[index][0]: column for index, column in enumerate(value)} for value in cursor.fetchall())
    return quote_df


def df_mysql_query_from_list(stock_table_sql, date_list):
    select_str = f'select * from `{stock_table_sql}` where `date` in (%s)' % ','.join(['%s'] * len(date_list))
    cursor.execute(select_str, date_list)
    columns = cursor.description
    quote_df = pd.DataFrame.from_dict({columns[index][0]: column for index, column in enumerate(value)} for value in cursor.fetchall())
    return quote_df

DB_CONN_OPT = pymysql.connect(host='localhost',
                         user='root',
                         password='123456',
                         db='optionmarket')

cursor_opt = DB_CONN_OPT.cursor()


def df_mysql_opt_query(query):
    cursor_opt.execute(query)
    columns = cursor_opt.description
    quote_df = pd.DataFrame.from_dict({columns[index][0]: column for index, column in enumerate(value)} for value in cursor_opt.fetchall())
    return quote_df


engine = create_engine("mysql+pymysql://{user}:{pw}@localhost/{db}"
                       .format(user="root",
                               pw="123456",
                               db="optionmarket")
                       )
