from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel
from pydantic import ConfigDict
from module_admin.annotation.pydantic_annotation import as_query


class SpiderModel(BaseModel):
    """
    采集任务模型
    与前端字段保持一致：id, taskName, domain, mainHost, configUser, updatedAt, crawlStartAt, status
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: Optional[int] = None
    # 网站名称 -> 任务名称，兼容历史别名 taskName
    task_name: str = Field(default="", alias="siteName")
    task_name_alias: Optional[str] = Field(default=None, alias="taskName")
    # 栏目名称 -> classd_name
    column_name: Optional[str] = Field(default=None, alias="columnName")
    domain: Optional[str] = None
    main_host: Optional[str] = Field(default=None, alias="mainHost")
    config_user: Optional[str] = Field(default=None, alias="configUser")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")
    crawl_start_at: Optional[datetime] = Field(default=None, alias="crawlStartAt")
    status: Optional[str] = None
    config: Optional[str] = None

@as_query
class SpiderPageQueryModel(BaseModel):
    """
    采集任务分页查询模型
    queryParams: pageNum, pageSize, id, siteName, columnName, domain, status, configUser
    以及可选的日期范围: beginTime, endTime
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    page_num: int = Field(default=1, alias="pageNum")
    page_size: int = Field(default=10, alias="pageSize")

    id: Optional[int] = None
    site_name: Optional[str] = Field(default=None, alias="siteName")
    column_name: Optional[str] = Field(default=None, alias="columnName")
    domain: Optional[str] = None
    status: Optional[str] = None
    config_user: Optional[str] = Field(default=None, alias="configUser")

    begin_time: Optional[datetime] = Field(default=None, alias="beginTime")
    end_time: Optional[datetime] = Field(default=None, alias="endTime")


class SpiderConfigTestModel(BaseModel):
    """
    爬虫配置测试模型
    用于测试爬虫配置是否正确
    """
    
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    task_id: int = Field(alias="taskId")
    test_url: str = Field(alias="testUrl")
    config_data: dict = Field(alias="configData")


class SpiderConfigTestResultModel(BaseModel):
    """
    爬虫配置测试结果模型
    """
    
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    success: bool
    message: str
    extracted_data: Optional[dict] = Field(default=None, alias="extractedData")
    error_details: Optional[str] = Field(default=None, alias="errorDetails")
    execution_time: Optional[float] = Field(default=None, alias="executionTime")