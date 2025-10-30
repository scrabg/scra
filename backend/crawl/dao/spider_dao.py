from datetime import datetime
from sqlalchemy import and_, delete, select, update, true
from sqlalchemy.ext.asyncio import AsyncSession

from crawl.entity.do.spider_do import SpiderTask
from crawl.entity.vo.spider_vo import SpiderModel, SpiderPageQueryModel
from utils.page_util import PageUtil


class SpiderDao:
    """
    采集任务数据库操作层
    """

    @classmethod
    async def get_spider_list_dao(cls, db: AsyncSession, query_object: SpiderPageQueryModel, is_page: bool):
        """
        列表查询，支持分页

        :param db: orm对象
        :param query_object: 查询对象
        :param is_page: 是否分页
        :return: 分页数据或列表
        """
        conditions = []
        if query_object.id:
            conditions.append(SpiderTask.id == query_object.id)
        if query_object.domain:
            conditions.append(SpiderTask.domain.like(f"%{query_object.domain}%"))
        if query_object.site_name:
            conditions.append(SpiderTask.task_name.like(f"%{query_object.site_name}%"))
        if query_object.column_name:
            conditions.append(SpiderTask.column_name.like(f"%{query_object.column_name}%"))
        if query_object.status:
            conditions.append(SpiderTask.status == query_object.status)
        if query_object.config_user:
            conditions.append(SpiderTask.config_user == query_object.config_user)
        if query_object.begin_time and query_object.end_time:
            conditions.append(SpiderTask.updated_at.between(query_object.begin_time, query_object.end_time))

        query = select(SpiderTask).where(and_(*conditions) if conditions else true()).order_by(SpiderTask.id.desc())
        result = await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)
        return result

    @classmethod
    async def add_spider_dao(cls, db: AsyncSession, spider: SpiderModel):
        # 排除task_name_alias字段，因为SpiderTask模型中没有这个字段
        spider_data = spider.model_dump(exclude={'task_name_alias'})
        db_spider = SpiderTask(**spider_data)
        db.add(db_spider)
        await db.flush()
        return db_spider

    @classmethod
    async def edit_spider_dao(cls, db: AsyncSession, spider: dict):
        # 使用项目统一的批量update字典方式
        await db.execute(update(SpiderTask), [spider])

    @classmethod
    async def delete_spider_dao(cls, db: AsyncSession, task_id: int):
        await db.execute(delete(SpiderTask).where(SpiderTask.id.in_([task_id])))

    @classmethod
    async def start_spider_dao(cls, db: AsyncSession, task_id: int):
        await db.execute(
            update(SpiderTask)
            .where(SpiderTask.id == task_id)
            .values(status='running', crawl_start_at=datetime.now(), updated_at=datetime.now())
        )

    @classmethod
    async def stop_spider_dao(cls, db: AsyncSession, task_id: int):
        await db.execute(
            update(SpiderTask).where(SpiderTask.id == task_id).values(status='stopped', updated_at=datetime.now())
        )

    @classmethod
    async def save_config_dao(cls, db: AsyncSession, task_id: int, config_json: str):
        await db.execute(
            update(SpiderTask)
            .where(SpiderTask.id == task_id)
            .values(config=config_json, updated_at=datetime.now())
        )

    @classmethod
    async def get_spider_detail_dao(cls, db: AsyncSession, task_id: int):
        """
        获取单个任务详情
        
        :param db: orm对象
        :param task_id: 任务ID
        :return: 任务详情
        """
        query = select(SpiderTask).where(SpiderTask.id == task_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()