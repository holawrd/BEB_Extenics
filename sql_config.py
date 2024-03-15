from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from datetime import datetime

db_name = "BasicElementBase"
username = "root"
password = "Yang806699784"
host = "localhost"

engine = create_engine(f'mysql+pymysql://{username}:{password}@{host}/{db_name}', echo=False, future=True)

session_factory = sessionmaker(bind=engine)
db_session = scoped_session(session_factory)

Base = declarative_base()

#用户信息
class User(Base):
    __tablename__ = 'User'
    id = Column(Integer, primary_key=True)
    username = Column(String(1000), nullable=True)
    password = Column(String(1000), nullable=True)
    name = Column(String(1000), nullable=True)
    # 1 正常 0 禁用(禁止登录)
    state = Column(String(1000), nullable=True, default='1')


# 基元库
class BasEle(Base):
    __tablename__ = 'BasEle'
    id = Column(Integer, primary_key=True)
    # 名称
    name = Column(String(1000), nullable=True)
    # 类别
    class_ = Column(String(1000), nullable=True)
    # 描述信息
    info_text = Column(String(1000), nullable=True)
    # 时间
    time_ = Column(String(1000), nullable=True, default=datetime.now().strftime("%Y-%m-%d %H:%M"))



# 基元信息
class Info(Base):
    __tablename__ = 'Info'

    id = Column(Integer, primary_key=True)
    # 类型
    class_ = Column(String(1000), nullable=True)
    # 符号
    symbol = Column(String(1000), nullable=True)
    # 对象
    obj_ = Column(String(1000), nullable=True)
    # 目标对象
    info_id = Column(String(1000), nullable=True)
    # 基元库分类id
    info_class_id = Column(String(1000), nullable=True)


# 基元管理
class InfoId(Base):
    __tablename__ = 'InfoId'
    id = Column(Integer, primary_key=True)
    info_id = Column(String(1000), nullable=True)
    # 特征
    chara = Column(String(1000), nullable=True)
    # 量值
    value = Column(String(1000), nullable=True)


if __name__ == '__main__':
    print("基元库表格已建立")
    # 创建数据库
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # 创建 root root 账户
    with db_session():
        to_root = User(username="root", password="root")
        db_session.add(to_root)
        db_session.commit()
