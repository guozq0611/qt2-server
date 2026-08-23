from sqlalchemy import create_engine

from core.setting.setting import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

_db_engine = None


def get_db_engine(database_name=''):
    global _db_engine
    if _db_engine is not None:
        return _db_engine

    if database_name is None or database_name == '':
        database_name = MYSQL_DATABASE

    db_link = f'''mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{database_name}'''
    _db_engine = create_engine(db_link, echo=False, max_overflow=10, pool_size=50, pool_reset_on_return=None)
    return _db_engine
