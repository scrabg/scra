from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, String, Text
from config.database import Base
from config.env import DataBaseConfig
from utils.common_util import SqlalchemyUtil


class SpiderTask(Base):
    """
    采集任务表
    """

    __tablename__ = 'spider_task'
    __table_args__ = {'comment': '采集任务表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键')
    task_name = Column(String(200), nullable=True, server_default="''", comment='任务名称')
    domain = Column(
        String(255),
        nullable=True,
        server_default=SqlalchemyUtil.get_server_default_null(DataBaseConfig.db_type),
        comment='域名',
    )
    config_user = Column(
        String(64),
        nullable=True,
        server_default=SqlalchemyUtil.get_server_default_null(DataBaseConfig.db_type),
        comment='配置人',
    )
    status = Column(
        String(20),
        nullable=True,
        server_default=SqlalchemyUtil.get_server_default_null(DataBaseConfig.db_type),
        comment='任务状态',
    )
    # 栏目名称（Python属性为 column_name，数据库列名为 classd_name）
    column_name = Column(
        'classd_name',
        String(255),
        nullable=True,
        server_default=SqlalchemyUtil.get_server_default_null(DataBaseConfig.db_type),
        comment='栏目名称',
    )
    main_host = Column(
        String(255),
        nullable=True,
        server_default=SqlalchemyUtil.get_server_default_null(DataBaseConfig.db_type),
        comment='主域名',
    )
    updated_at = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')
    crawl_start_at = Column(DateTime, nullable=True, comment='采集启动时间')
    config = Column(
        Text,
        nullable=True,
        server_default=SqlalchemyUtil.get_server_default_null(DataBaseConfig.db_type),
        comment='任务配置JSON',
    )