from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from utils.page_util import PageResponseModel
from utils.response_util import ResponseUtil
from config.get_db import get_db
from crawl.entity.vo.spider_vo import SpiderModel, SpiderPageQueryModel, SpiderConfigTestModel
from crawl.service.spider_service import SpiderService
from module_admin.service.login_service import LoginService
from module_admin.entity.vo.user_vo import CurrentUserModel


spiderController = APIRouter(prefix='/crawl/spider')


@spiderController.get('/list', response_model=PageResponseModel)
async def list_spider(
    request: Request,
    page_query: SpiderPageQueryModel = Depends(SpiderPageQueryModel.as_query),
    query_db: AsyncSession = Depends(get_db),
):
    page_result = await SpiderService.list(query_db, page_query)
    return ResponseUtil.success(model_content=page_result)


@spiderController.post('')
async def add_spider(
    request: Request,
    add_model: SpiderModel,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    # 设置配置人
    add_model.config_user = current_user.user.user_name if current_user and current_user.user else None
    result = await SpiderService.add(query_db, add_model)
    return ResponseUtil.success(msg=result.message, dict_content={'id': result.result})


@spiderController.put('')
async def update_spider(
    request: Request,
    edit_model: SpiderModel,
    query_db: AsyncSession = Depends(get_db),
):
    result = await SpiderService.update(query_db, edit_model)
    return ResponseUtil.success(msg=result.message)


@spiderController.delete('/{task_id}')
async def delete_spider(
    request: Request,
    task_id: int,
    query_db: AsyncSession = Depends(get_db),
):
    result = await SpiderService.delete(query_db, task_id)
    return ResponseUtil.success(msg=result.message)


@spiderController.put('/save-config/{task_id}')
async def save_spider_config(
    request: Request,
    task_id: int,
    config_data: dict,
    query_db: AsyncSession = Depends(get_db),
):
    result = await SpiderService.save_config(query_db, task_id, config_data)
    return ResponseUtil.success(msg=result.message)


@spiderController.put('/start/{task_id}')
async def start_spider(
    request: Request,
    task_id: int,
    query_db: AsyncSession = Depends(get_db),
):
    result = await SpiderService.start(query_db, task_id)
    return ResponseUtil.success(msg=result.message)


@spiderController.put('/stop/{task_id}')
async def stop_spider(
    request: Request,
    task_id: int,
    query_db: AsyncSession = Depends(get_db),
):
    result = await SpiderService.stop(query_db, task_id)
    return ResponseUtil.success(msg=result.message)


@spiderController.get('/{task_id}')
async def get_spider_detail(
    request: Request,
    task_id: int,
    query_db: AsyncSession = Depends(get_db),
):
    result = await SpiderService.get_detail(query_db, task_id)
    if result is None:
        return ResponseUtil.error(msg='任务不存在')
    return ResponseUtil.success(data=result)


@spiderController.post('/test-config')
async def test_spider_config(
    request: Request,
    test_model: SpiderConfigTestModel,
    query_db: AsyncSession = Depends(get_db),
):
    """
    测试爬虫配置是否正确
    """
    result = await SpiderService.test_config(query_db, test_model)
    return ResponseUtil.success(data=result.model_dump())