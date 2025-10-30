from datetime import datetime
import json
import time
from sqlalchemy.ext.asyncio import AsyncSession

from crawl.dao.spider_dao import SpiderDao
from crawl.entity.vo.spider_vo import SpiderModel, SpiderPageQueryModel, SpiderConfigTestModel, SpiderConfigTestResultModel
from module_admin.entity.vo.common_vo import CrudResponseModel
from urllib.parse import urlparse
from utils.string_util import StringUtil


class SpiderService:
    """
    采集任务服务层（数据库版）
    前端提交字段别名：siteName->task_name, columnName->column_name(classd_name)
    """

    @classmethod
    async def save_config(cls, query_db: AsyncSession, task_id: int, config_data: dict) -> CrudResponseModel:
        try:
            # 将配置数据转换为JSON字符串
            config_json = json.dumps(config_data, ensure_ascii=False)
            await SpiderDao.save_config_dao(query_db, task_id, config_json)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='配置保存成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def list(cls, query_db: AsyncSession, query: SpiderPageQueryModel):
        page_obj = await SpiderDao.get_spider_list_dao(query_db, query, is_page=True)
        return page_obj

    @classmethod
    async def add(cls, query_db: AsyncSession, model: SpiderModel) -> CrudResponseModel:
        try:
            # 解析主域名
            if model.domain:
                domain = model.domain.strip()
                parsed = urlparse(domain if StringUtil.is_http(domain) else f'https://{domain}')
                host = parsed.hostname or domain
                model.main_host = host
            model.updated_at = datetime.now()
            db_obj = await SpiderDao.add_spider_dao(query_db, model)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='新增成功', result=db_obj.id)
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def update(cls, query_db: AsyncSession, model: SpiderModel) -> CrudResponseModel:
        try:
            edit_dict = model.model_dump(exclude_unset=True)
            # 解析主域名（若提供了 domain 更新）
            domain = edit_dict.get('domain')
            if domain:
                d = domain.strip()
                parsed = urlparse(d if StringUtil.is_http(d) else f'https://{d}')
                host = parsed.hostname or d
                edit_dict['main_host'] = host
            edit_dict['updated_at'] = datetime.now()
            await SpiderDao.edit_spider_dao(query_db, edit_dict)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='修改成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def delete(cls, query_db: AsyncSession, task_id: int) -> CrudResponseModel:
        try:
            await SpiderDao.delete_spider_dao(query_db, task_id)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='删除成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def start(cls, query_db: AsyncSession, task_id: int) -> CrudResponseModel:
        try:
            await SpiderDao.start_spider_dao(query_db, task_id)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='启动成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def stop(cls, query_db: AsyncSession, task_id: int) -> CrudResponseModel:
        try:
            await SpiderDao.stop_spider_dao(query_db, task_id)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='停止成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def get_detail(cls, query_db: AsyncSession, task_id: int):
        """
        获取任务详情
        
        :param query_db: 数据库会话
        :param task_id: 任务ID
        :return: 任务详情
        """
        spider_task = await SpiderDao.get_spider_detail_dao(query_db, task_id)
        if not spider_task:
            return None
        
        # 转换为字典格式
        result = {
            'id': spider_task.id,
            'task_name': spider_task.task_name,
            'domain': spider_task.domain,
            'main_host': spider_task.main_host,
            'column_name': spider_task.column_name,
            'status': spider_task.status,
            'config_user': spider_task.config_user,
            'updated_at': spider_task.updated_at,
            'crawl_start_at': spider_task.crawl_start_at,
            'config': spider_task.config
        }
        
        # 如果有配置数据，解析JSON
        if spider_task.config:
            try:
                result['config'] = json.loads(spider_task.config)
            except json.JSONDecodeError:
                result['config'] = None
        
        return result

    @classmethod
    async def test_config(cls, query_db: AsyncSession, test_model: SpiderConfigTestModel) -> SpiderConfigTestResultModel:
        """
        测试爬虫配置
        
        :param query_db: 数据库会话
        :param test_model: 测试模型
        :return: 测试结果
        """
        start_time = time.time()
        
        try:
            # 导入爬虫引擎
            from crawl.engine.spider_engine import SpiderEngine
            
            # 解析配置数据
            config_data = test_model.config_data
            
            # 构建完整的配置
            engine_config = {
                'task_id': test_model.task_id,
                'workflowSteps': config_data.get('workflowSteps', []),
                'headers': config_data.get('headers', {}),
                'cookies': config_data.get('cookies', {}),
                'proxy': config_data.get('proxy', {}),
                'delay': config_data.get('delay', 1)
            }
            
            # 创建爬虫引擎实例，传入配置
            engine = SpiderEngine(engine_config)
            
            # 执行测试
            result = engine.test_single_url(test_model.test_url)
            
            execution_time = time.time() - start_time
            
            # 检查测试结果
            if result.get('success', False):
                return SpiderConfigTestResultModel(
                    success=True,
                    message="配置测试成功",
                    extracted_data=result,
                    execution_time=execution_time
                )
            else:
                # 测试失败，但不是异常
                error_msg = result.get('error', '未知错误')
                status_code = result.get('status_code', 0)
                
                if status_code >= 400:
                    message = f"请求失败: HTTP {status_code}"
                else:
                    message = f"配置测试失败: {error_msg}"
                
                return SpiderConfigTestResultModel(
                    success=False,
                    message=message,
                    extracted_data=result,
                    error_details=error_msg,
                    execution_time=execution_time
                )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            return SpiderConfigTestResultModel(
                success=False,
                message="配置测试失败",
                extracted_data=None,
                error_details=str(e),
                execution_time=execution_time
            )