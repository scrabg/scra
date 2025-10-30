#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫执行引擎
基于 detail.vue 界面配置的爬虫执行引擎，支持多步骤工作流
"""

import json
import requests
import time
from typing import Dict, List, Any, Optional, Union, Callable
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
import traceback
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue, Empty


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class SpiderRequest:
    """爬虫请求对象"""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    timeout: int = 120
    retry_count: int = 0
    retry_delay: int = 1
    step_id: int = 0
    parent_url: str = ""
    depth: int = 0


@dataclass
class SpiderResponse:
    """爬虫响应对象"""
    url: str
    status_code: int
    content: str
    headers: Dict[str, str]
    response_time: float
    error: Optional[str] = None
    step_id: int = 0
    parent_url: str = ""
    depth: int = 0


@dataclass
class ExtractedData:
    """提取的数据对象"""
    url: str
    data: Dict[str, Any]
    step_id: int
    timestamp: datetime = field(default_factory=datetime.now)


class SpiderEngine:
    """爬虫执行引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.task_info = config.get("taskInfo", {})
        self.workflow_steps = config.get("workflowSteps", [])
        
        # 运行状态
        self.is_running = False
        self.is_paused = False
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.extracted_data = []
        
        # 请求队列和结果队列
        self.request_queue = Queue()
        self.response_queue = Queue()
        self.data_queue = Queue()
        
        # 保存所有请求和响应的历史记录
        self.request_history = []
        self.response_history = []
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=self.task_info.get("concurrency", 1))
        
        # 会话管理
        self.session = requests.Session()
        self._setup_session()
        
        # 自定义代码执行环境
        self.custom_code_globals = {
            'requests': requests,
            'BeautifulSoup': BeautifulSoup,
            're': re,
            'urljoin': urljoin,
            'urlparse': urlparse,
            'json': json,
            'time': time,
            'datetime': datetime
        }
        
        # 编译自定义代码
        self._compile_custom_codes()
    
    def _setup_session(self):
        """设置会话"""
        # 设置默认请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 设置连接池
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def _compile_custom_codes(self):
        """编译所有步骤中的自定义代码"""
        for step in self.workflow_steps:
            config = step.get("config", {})
            custom_code = config.get("nextRequestCustomCode", "")
            
            if custom_code:
                try:
                    # 编译代码
                    compiled_code = compile(custom_code, f'<step_{step.get("id", 0)}>', 'exec')
                    
                    # 执行代码以获取函数
                    exec_globals = self.custom_code_globals.copy()
                    exec(compiled_code, exec_globals)
                    
                    # 保存编译后的函数
                    config["_compiled_functions"] = {
                        'process_next_requests': exec_globals.get('process_next_requests'),
                        'extract_data': exec_globals.get('extract_data')
                    }
                    
                    logger.info(f"步骤 {step.get('id')} 自定义代码编译成功")
                    
                except Exception as e:
                    logger.error(f"步骤 {step.get('id')} 自定义代码编译失败: {e}")
                    config["_compiled_functions"] = {}
    
    def start(self, start_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """启动爬虫"""
        if self.is_running:
            return {"success": False, "message": "爬虫已在运行中"}
        
        logger.info("启动爬虫引擎...")
        self.is_running = True
        self.is_paused = False
        
        # 重置统计信息
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.extracted_data = []
        
        try:
            # 添加起始URL到队列
            if not start_urls:
                base_url = self.task_info.get("baseUrl", "")
                if base_url:
                    start_urls = [base_url]
                else:
                    return {"success": False, "message": "未配置起始URL"}
            
            for url in start_urls:
                initial_request = SpiderRequest(
                    url=url,
                    method="GET",
                    step_id=0,
                    depth=0
                )
                self.request_queue.put(initial_request)
            
            # 启动工作线程
            self._start_worker_threads()
            
            # 主循环
            self._main_loop()
            
            return {
                "success": True,
                "message": "爬虫执行完成",
                "stats": self._get_stats()
            }
            
        except Exception as e:
            logger.error(f"爬虫执行异常: {e}")
            return {"success": False, "message": f"爬虫执行异常: {str(e)}"}
        finally:
            self.is_running = False
    
    def _start_worker_threads(self):
        """启动工作线程"""
        # 启动请求处理线程
        for i in range(self.task_info.get("concurrency", 1)):
            thread = threading.Thread(target=self._request_worker, daemon=True)
            thread.start()
        
        # 启动响应处理线程
        response_thread = threading.Thread(target=self._response_worker, daemon=True)
        response_thread.start()
    
    def _main_loop(self):
        """主循环"""
        request_interval = self.task_info.get("requestInterval", 1)
        max_idle_time = 30  # 最大空闲时间（秒）
        idle_start_time = None
        
        while self.is_running:
            if self.is_paused:
                time.sleep(1)
                continue
            
            # 检查是否有活动
            has_activity = (
                not self.request_queue.empty() or
                not self.response_queue.empty() or
                not self.data_queue.empty()
            )
            
            if has_activity:
                idle_start_time = None
                time.sleep(request_interval)
            else:
                # 开始计算空闲时间
                if idle_start_time is None:
                    idle_start_time = time.time()
                elif time.time() - idle_start_time > max_idle_time:
                    logger.info("达到最大空闲时间，停止爬虫")
                    break
                
                time.sleep(1)
        
        logger.info("爬虫主循环结束")
    
    def _request_worker(self):
        """请求处理工作线程"""
        while self.is_running:
            try:
                # 从队列获取请求
                request = self.request_queue.get(timeout=5)
                
                if not self.is_running or self.is_paused:
                    continue
                
                # 执行请求
                response = self._execute_request(request)
                
                # 将响应放入响应队列
                self.response_queue.put(response)
                
                self.request_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"请求处理异常: {e}")
    
    def _response_worker(self):
        """响应处理工作线程"""
        while self.is_running:
            try:
                # 从队列获取响应
                response = self.response_queue.get(timeout=5)
                
                if not self.is_running:
                    continue
                
                # 处理响应
                self._process_response(response)
                
                self.response_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"响应处理异常: {e}")
    
    def _execute_request(self, request: SpiderRequest) -> SpiderResponse:
        """执行HTTP请求"""
        start_time = time.time()
        self.total_requests += 1
        
        # 保存请求到历史记录
        self.request_history.append(request)
        
        try:
            logger.info(f"请求: {request.method} {request.url}")
            
            # 构建请求参数
            kwargs = {
                'timeout': request.timeout,
                'headers': request.headers,
                'params': request.params,
                'proxies': {'http': 'http://t19508772035876:dfnat553@o483.kdltps.com:15818/',
                                'https': 'http://t19508772035876:dfnat553@o483.kdltps.com:15818/'}
            }
            
            if request.method.upper() == 'POST' and request.body:
                try:
                    # 尝试解析为JSON
                    json_body = json.loads(request.body)
                    kwargs['json'] = json_body
                except json.JSONDecodeError:
                    kwargs['data'] = request.body
            
            # 发送请求
            if request.method.upper() == 'GET':
                response = self.session.get(request.url, **kwargs)
            elif request.method.upper() == 'POST':
                response = self.session.post(request.url, **kwargs)
            else:
                raise ValueError(f"不支持的请求方法: {request.method}")
            print(response)
            response_time = time.time() - start_time
            
            # 检查响应状态
            if response.status_code >= 400:
                self.failed_requests += 1
                return SpiderResponse(
                    url=request.url,
                    status_code=response.status_code,
                    content="",
                    headers=dict(response.headers),
                    response_time=response_time,
                    error=f"HTTP {response.status_code}",
                    step_id=request.step_id,
                    parent_url=request.parent_url,
                    depth=request.depth
                )
            
            self.successful_requests += 1
            
            return SpiderResponse(
                url=request.url,
                status_code=response.status_code,
                content=response.text,
                headers=dict(response.headers),
                response_time=response_time,
                step_id=request.step_id,
                parent_url=request.parent_url,
                depth=request.depth
            )
            
        except Exception as e:
            self.failed_requests += 1
            response_time = time.time() - start_time
            
            logger.error(f"请求失败 {request.url}: {e}")
            
            return SpiderResponse(
                url=request.url,
                status_code=0,
                content="",
                headers={},
                response_time=response_time,
                error=str(e),
                step_id=request.step_id,
                parent_url=request.parent_url,
                depth=request.depth
            )
    
    def _process_response(self, response: SpiderResponse):
        """处理响应"""
        if response.error:
            logger.warning(f"跳过错误响应: {response.url} - {response.error}")
            return
        
        logger.info(f"处理响应: {response.url} (状态码: {response.status_code})")
        
        # 保存响应到历史记录
        self.response_history.append(response)
        
        # 查找对应的工作流步骤
        current_step = None
        next_step = None
        
        for i, step in enumerate(self.workflow_steps):
            if step.get("id") == response.step_id:
                current_step = step
                if i + 1 < len(self.workflow_steps):
                    next_step = self.workflow_steps[i + 1]
                break
        
        if not current_step:
            # 如果没有找到对应步骤，使用第一个步骤
            current_step = self.workflow_steps[0] if self.workflow_steps else None
            next_step = self.workflow_steps[1] if len(self.workflow_steps) > 1 else None
        
        if not current_step:
            logger.warning("未找到对应的工作流步骤")
            return
        
        # 根据步骤类型处理
        step_type = current_step.get("type")
        
        if step_type == "request":
            self._process_request_step(response, current_step, next_step)
        elif step_type == "link_extraction":
            self._process_link_extraction_step(response, current_step, next_step)
        elif step_type == "data_extraction":
            self._process_data_extraction_step(response, current_step, next_step)
    
    def _process_request_step(self, response: SpiderResponse, current_step: Dict, next_step: Optional[Dict]):
        """处理请求步骤"""
        # 请求步骤主要是获取页面内容，直接进入下一步
        if next_step:
            self._execute_next_step(response, next_step)
    
    def _process_link_extraction_step(self, response: SpiderResponse, current_step: Dict, next_step: Optional[Dict]):
        """处理链接提取步骤"""
        config = current_step.get("config", {})
        
        # 先执行链接提取规则（如果有）
        link_extraction_rules = config.get("linkExtractionRules", [])
        extracted_links = {}
        
        if link_extraction_rules:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for rule in link_extraction_rules:
                field_name = rule.get("fieldName")
                extract_type = rule.get("extractType")
                expression = rule.get("expression")
                data_type = rule.get("dataType", "text")
                multiple = rule.get("multiple", False)
                
                if not field_name or not extract_type or not expression:
                    continue
                
                try:
                    values = []
                    
                    if extract_type == "css":
                        elements = soup.select(expression)
                        for element in elements:
                            if data_type == "text":
                                value = element.get_text().strip()
                            elif data_type == "html":
                                value = str(element)
                            elif data_type == "attr":
                                attr_name = rule.get("attrName", "href")
                                value = element.get(attr_name, "")
                            else:
                                value = element.get_text().strip()
                            
                            if value:
                                values.append(value)
                    
                    elif extract_type == "xpath":
                        try:
                            from lxml import html
                            tree = html.fromstring(response.content)
                            elements = tree.xpath(expression)
                            for element in elements:
                                if hasattr(element, 'text'):
                                    value = element.text or ""
                                else:
                                    value = str(element)
                                if value:
                                    values.append(value)
                        except ImportError:
                            logger.warning("XPath提取需要安装lxml库")
                    
                    # 保存提取结果
                    if multiple:
                        extracted_links[field_name] = values
                    else:
                        extracted_links[field_name] = values[0] if values else None
                        
                except Exception as e:
                    logger.error(f"链接提取字段 {field_name} 异常: {e}")
            
            # 如果提取到了链接数据，保存到数据队列
            if extracted_links:
                # 执行ZIP操作
                zipped_data = self._zip_extracted_fields(extracted_links)
                
                data_obj = ExtractedData(
                    url=response.url,
                    data={"zipped_data": zipped_data},
                    step_id=current_step.get("id", 0)
                )
                self.extracted_data.append(data_obj)
                self.data_queue.put(data_obj)
                logger.info(f"链接提取数据: {response.url} -> {list(extracted_links.keys())}")
        
        # 执行自定义代码提取链接
        compiled_functions = config.get("_compiled_functions", {})
        process_next_requests = compiled_functions.get("process_next_requests")
        
        if process_next_requests:
            try:
                next_requests = process_next_requests(response.content, response.url)
                
                if isinstance(next_requests, list):
                    for req_data in next_requests:
                        if isinstance(req_data, dict) and req_data.get("url"):
                            new_request = SpiderRequest(
                                url=req_data["url"],
                                method=req_data.get("method", "GET"),
                                headers=req_data.get("headers", {}),
                                params=req_data.get("params", {}),
                                body=req_data.get("body", ""),
                                timeout=current_step.get("timeout", 120),
                                retry_count=current_step.get("retryCount", 0),
                                retry_delay=current_step.get("retryDelay", 1),
                                step_id=next_step.get("id", 0) if next_step else 0,
                                parent_url=response.url,
                                depth=response.depth + 1
                            )
                            self.request_queue.put(new_request)
                            logger.info(f"添加新请求: {new_request.url}")
                
            except Exception as e:
                logger.error(f"链接提取自定义代码执行失败: {e}")
        
        # 如果没有下一步，但有自定义代码提取数据
        extract_data = compiled_functions.get("extract_data")
        if extract_data:
            try:
                extracted = extract_data(response.content, response.url)
                if isinstance(extracted, dict) and extracted:
                    data_obj = ExtractedData(
                        url=response.url,
                        data=extracted,
                        step_id=current_step.get("id", 0)
                    )
                    self.extracted_data.append(data_obj)
                    self.data_queue.put(data_obj)
                    logger.info(f"提取数据: {response.url} -> {list(extracted.keys())}")
            except Exception as e:
                logger.error(f"数据提取自定义代码执行失败: {e}")
    
    def _process_data_extraction_step(self, response: SpiderResponse, current_step: Dict, next_step: Optional[Dict]):
        """处理数据提取步骤"""
        config = current_step.get("config", {})
        extraction_rules = config.get("extractionRules", [])
        
        if not extraction_rules:
            logger.warning("数据提取步骤未配置提取规则")
            return
        
        extracted_data = {}
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for rule in extraction_rules:
            field_name = rule.get("fieldName")
            extract_type = rule.get("extractType")
            expression = rule.get("expression")
            data_type = rule.get("dataType", "text")
            required = rule.get("required", False)
            
            if not field_name or not extract_type or not expression:
                continue
            
            try:
                value = None
                
                if extract_type == "css":
                    elements = soup.select(expression)
                    if elements:
                        if data_type == "text":
                            value = elements[0].get_text().strip()
                        elif data_type == "html":
                            value = str(elements[0])
                        elif data_type == "attr":
                            attr_name = rule.get("attrName", "href")
                            value = elements[0].get(attr_name, "")
                
                elif extract_type == "xpath":
                    # 简单的XPath支持（需要lxml库）
                    try:
                        from lxml import html
                        tree = html.fromstring(response.content)
                        elements = tree.xpath(expression)
                        if elements:
                            if hasattr(elements[0], 'text'):
                                value = elements[0].text or ""
                            else:
                                value = str(elements[0])
                    except ImportError:
                        logger.warning("XPath提取需要安装lxml库")
                
                elif extract_type == "regex":
                    matches = re.findall(expression, response.content)
                    if matches:
                        value = matches[0] if isinstance(matches[0], str) else matches[0][0]
                
                # 数据类型转换
                if value is not None:
                    if data_type == "number":
                        try:
                            value = float(str(value)) if '.' in str(value) else int(str(value))
                        except ValueError:
                            value = 0
                    elif data_type == "boolean":
                        value = bool(value and str(value).lower() not in ['false', '0', 'no', 'off'])
                
                extracted_data[field_name] = value
                
                if value is not None:
                    logger.debug(f"提取字段 {field_name}: {value}")
                elif required:
                    logger.warning(f"必填字段 {field_name} 提取失败")
                
            except Exception as e:
                logger.error(f"字段 {field_name} 提取异常: {e}")
                if required:
                    extracted_data[field_name] = None
        
        # 保存提取的数据
        if extracted_data:
            data_obj = ExtractedData(
                url=response.url,
                data=extracted_data,
                step_id=current_step.get("id", 0)
            )
            self.extracted_data.append(data_obj)
            self.data_queue.put(data_obj)
            logger.info(f"提取数据: {response.url} -> {list(extracted_data.keys())}")
        
        # 执行下一级请求（如果有自定义代码）
        compiled_functions = config.get("_compiled_functions", {})
        process_next_requests = compiled_functions.get("process_next_requests")
        
        if process_next_requests:
            try:
                next_requests = process_next_requests(response.content, response.url, extracted_data)
                
                if isinstance(next_requests, list):
                    for req_data in next_requests:
                        if isinstance(req_data, dict) and req_data.get("url"):
                            new_request = SpiderRequest(
                                url=req_data["url"],
                                method=req_data.get("method", "GET"),
                                headers=req_data.get("headers", {}),
                                params=req_data.get("params", {}),
                                body=req_data.get("body", ""),
                                timeout=current_step.get("timeout", 120),
                                retry_count=current_step.get("retryCount", 0),
                                retry_delay=current_step.get("retryDelay", 1),
                                step_id=current_step.get("id", 0),  # 继续使用当前步骤ID
                                parent_url=response.url,
                                depth=response.depth + 1
                            )
                            self.request_queue.put(new_request)
                            logger.info(f"添加新请求: {new_request.url}")
                
            except Exception as e:
                logger.error(f"数据提取自定义代码执行失败: {e}")
    
    def _execute_next_step(self, response: SpiderResponse, next_step: Dict):
        """执行下一步"""
        if not next_step:
            return
        
        # 创建新请求进入下一步
        new_request = SpiderRequest(
            url=response.url,
            method="GET",
            step_id=next_step.get("id", 0),
            parent_url=response.parent_url,
            depth=response.depth,
            timeout=next_step.get("timeout", 120),
            retry_count=next_step.get("retryCount", 0),
            retry_delay=next_step.get("retryDelay", 1)
        )
        
        # 不重新请求，直接处理当前响应
        new_response = SpiderResponse(
            url=response.url,
            status_code=response.status_code,
            content=response.content,
            headers=response.headers,
            response_time=response.response_time,
            step_id=next_step.get("id", 0),
            parent_url=response.parent_url,
            depth=response.depth
        )
        
        self.response_queue.put(new_response)
    
    def pause(self):
        """暂停爬虫"""
        self.is_paused = True
        logger.info("爬虫已暂停")
    
    def resume(self):
        """恢复爬虫"""
        self.is_paused = False
        logger.info("爬虫已恢复")
    
    def stop(self):
        """停止爬虫"""
        self.is_running = False
        logger.info("爬虫已停止")
    
    def _get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / max(self.total_requests, 1) * 100,
            "extracted_data_count": len(self.extracted_data),
            "is_running": self.is_running,
            "is_paused": self.is_paused
        }
    
    def get_extracted_data(self) -> List[Dict[str, Any]]:
        """获取提取的数据"""
        return [
            {
                "url": data.url,
                "data": data.data,
                "step_id": data.step_id,
                "timestamp": data.timestamp.isoformat()
            }
            for data in self.extracted_data
        ]
    
    def test_single_url(self, url: str) -> dict:
        """
        测试单个URL的配置 - 支持新的三步骤工作流程逻辑
        
        步骤1：请求配置 - 只负责发起HTTP请求
        步骤2：链接提取 - 解析响应内容并生成下一步请求参数  
        步骤3：数据提取 - 只解析内容不发起请求
        
        Args:
            url: 要测试的URL
            
        Returns:
            dict: 提取的数据结果
        """
        try:
            results = {}
            current_response = None
            
            # 按步骤顺序执行工作流
            for i, step in enumerate(self.workflow_steps):
                step_id = step.get('id', i + 1)
                step_type = step.get('type')
                step_name = step.get('name', f'Step {step_id}')
                
                if step_type == 'request':
                    # 步骤1：请求配置 - 只负责发起HTTP请求
                    config = step.get('config', {})
                    request_url = config.get('url', url)  # 如果配置了URL则使用配置的，否则使用传入的URL
                    
                    # 处理headers - 支持headersJson字段（JSON字符串）和headers字段（对象）
                    headers = {}
                    if config.get('headersJson'):
                        try:
                            headers = json.loads(config.get('headersJson'))
                        except json.JSONDecodeError:
                            return {
                                'error': f'headersJson格式错误: 无法解析JSON',
                                'success': False
                            }
                    elif config.get('headers'):
                        headers = config.get('headers', {})
                    
                    test_request = SpiderRequest(
                        url=request_url,
                        method=config.get('method', 'GET'),
                        headers=headers,
                        params=config.get('params', {}),
                        body=config.get('body', ''),
                        timeout=config.get('timeout', 120),
                        step_id=step_id,
                        depth=0
                    )
                    
                    # 执行请求
                    current_response = self._execute_request(test_request)
                    
                    # 检查是否有错误
                    if current_response.error:
                        return {
                            'error': current_response.error,
                            'url': request_url,
                            'status_code': current_response.status_code,
                            'success': False
                        }
                    
                    # 检查HTTP状态码
                    if current_response.status_code >= 400:
                        return {
                            'error': f'HTTP {current_response.status_code}',
                            'url': request_url,
                            'status_code': current_response.status_code,
                            'success': False,
                            'content_length': len(current_response.content)
                        }
                    
                    results[f'step_{step_id}'] = {
                        'type': step_type,
                        'name': step_name,
                        'result': {
                            'message': f'请求成功执行',
                            'url': request_url,
                            'status_code': current_response.status_code,
                            'content_length': len(current_response.content),
                            'response_time': current_response.response_time
                        }
                    }
                    
                elif step_type == 'link_extraction':
                    # 步骤2：链接提取 - 解析响应内容并生成下一步请求参数
                    if current_response is None:
                        # 如果没有前置请求步骤，直接发起请求获取响应内容
                        test_request = SpiderRequest(
                            url=url,
                            method='GET',
                            headers=self.config.get('headers', {}),
                            timeout=step.get('timeout', 120),
                            step_id=step_id,
                            depth=0
                        )
                        
                        # 执行请求
                        current_response = self._execute_request(test_request)
                        
                        # 检查是否有错误
                        if current_response.error:
                            results[f'step_{step_id}'] = {
                                'type': step_type,
                                'name': step_name,
                                'result': {'error': current_response.error}
                            }
                            continue
                        
                        # 检查HTTP状态码
                        if current_response.status_code >= 400:
                            results[f'step_{step_id}'] = {
                                'type': step_type,
                                'name': step_name,
                                'result': {'error': f'HTTP {current_response.status_code}'}
                            }
                            continue
                    
                    # 执行链接提取
                    step_result = self._execute_step(step, current_response, current_response.url)
                    results[f'step_{step_id}'] = {
                        'type': step_type,
                        'name': step_name,
                        'result': step_result
                    }
                    
                    # 如果有自定义代码，生成下一步请求参数（但不执行请求）
                    custom_code = step.get('config', {}).get('nextRequestCustomCode', '') or step.get('customCode', '')
                    if custom_code:
                        try:
                            # 编译自定义代码
                            compiled_functions = step.get('_compiled_functions', {})
                            if not compiled_functions:
                                exec_globals = {}
                                exec(custom_code, exec_globals)
                                compiled_functions = {
                                    'process_next_requests': exec_globals.get('process_next_requests')
                                }
                                step['_compiled_functions'] = compiled_functions
                            
                            process_next_requests = compiled_functions.get('process_next_requests')
                            if process_next_requests:
                                next_requests = process_next_requests(current_response.content, current_response.url)
                                
                                # 将生成的请求参数添加到结果中
                                if isinstance(next_requests, list) and next_requests:
                                    results[f'step_{step_id}']['result']['generated_requests'] = next_requests[:3]  # 限制显示前3个
                                    
                                    # 为下一步数据提取准备响应内容
                                    # 这里我们选择第一个生成的请求进行实际请求，为数据提取步骤提供内容
                                    if next_requests:
                                        first_request = next_requests[0]
                                        if isinstance(first_request, dict) and 'url' in first_request:
                                            next_request = SpiderRequest(
                                                url=first_request['url'],
                                                method=first_request.get('method', 'GET'),
                                                step_id=first_request.get('step_id', step_id + 1),
                                                parent_url=current_response.url,
                                                depth=current_response.depth + 1
                                            )
                                            
                                            # 执行请求以获取下一步的响应内容
                                            next_response = self._execute_request(next_request)
                                            if not next_response.error and next_response.status_code < 400:
                                                current_response = next_response  # 更新当前响应为下一步使用
                                                
                        except Exception as e:
                            logger.error(f"Error executing custom code for step {step_id}: {str(e)}")
                            results[f'step_{step_id}']['result']['custom_code_error'] = str(e)
                    
                elif step_type == 'data_extraction':
                    # 步骤3：数据提取 - 只解析内容不发起请求
                    if current_response is None:
                        results[f'step_{step_id}'] = {
                            'type': step_type,
                            'name': step_name,
                            'result': {'error': '没有可用的响应内容进行数据提取'}
                        }
                        continue
                    
                    # 执行数据提取
                    step_result = self._execute_step(step, current_response, current_response.url)
                    results[f'step_{step_id}'] = {
                        'type': step_type,
                        'name': step_name,
                        'result': step_result
                    }
                
                else:
                    # 其他类型的步骤
                    if current_response:
                        step_result = self._execute_step(step, current_response, current_response.url)
                        results[f'step_{step_id}'] = {
                            'type': step_type,
                            'name': step_name,
                            'result': step_result
                        }
            
            return {
                'url': url,
                'status_code': current_response.status_code if current_response else 0,
                'content_length': len(current_response.content) if current_response else 0,
                'steps_results': results,
                'success': True
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'url': url,
                'success': False
            }

    def _execute_step(self, step: dict, response: SpiderResponse, current_url: str) -> dict:
        """执行单个步骤并返回结果"""
        step_type = step.get('type')
        
        if step_type == 'data_extraction':
            # 支持两种配置格式：config.extractionRules 和 dataExtractionRules
            config = step.get('config', {})
            if not config.get('extractionRules') and step.get('dataExtractionRules'):
                config = {'extractionRules': step.get('dataExtractionRules')}
            return self._test_data_extraction(response, config)
        elif step_type == 'link_extraction':
            # 支持两种配置格式：config.extractionRules 和 linkExtractionRules
            config = step.get('config', {})
            if not config.get('extractionRules') and step.get('linkExtractionRules'):
                config = {'extractionRules': step.get('linkExtractionRules')}
            return self._test_link_extraction(response, config)
        else:
            return {'message': f'Step type {step_type} executed'}
    
    def _test_data_extraction(self, response: SpiderResponse, config: dict) -> dict:
        """测试数据提取"""
        extraction_rules = config.get('extractionRules', [])
        extracted_data = {}
        
        if not extraction_rules:
            return {'warning': 'No extraction rules configured'}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for rule in extraction_rules:
            # 支持两种字段名格式：fieldName 和 field
            field_name = rule.get('fieldName') or rule.get('field')
            # 支持两种提取类型格式：extractType 和 type
            extract_type = rule.get('extractType') or rule.get('type')
            # 支持两种表达式格式：expression 和 selector
            expression = rule.get('expression') or rule.get('selector')
            data_type = rule.get('dataType', 'text')
            
            if not field_name or not extract_type or not expression:
                continue
            
            try:
                value = None
                
                if extract_type == 'css':
                    elements = soup.select(expression)
                    if elements:
                        if data_type == 'text' or rule.get('attribute') == 'text':
                            value = elements[0].get_text().strip()
                        elif data_type == 'html':
                            value = str(elements[0])
                        elif data_type == 'attr' or rule.get('attribute'):
                            attr_name = rule.get('attrName') or rule.get('attribute', 'href')
                            value = elements[0].get(attr_name, '')
                
                elif extract_type == 'xpath':
                    # 使用lxml处理XPath
                    try:
                        from lxml import html
                        tree = html.fromstring(response.content)
                        elements = tree.xpath(expression)
                        if elements:
                            if rule.get('attribute') == 'text' or data_type == 'text':
                                if hasattr(elements[0], 'text_content'):
                                    value = elements[0].text_content().strip()
                                else:
                                    value = str(elements[0]).strip()
                            elif rule.get('attribute'):
                                attr_name = rule.get('attribute')
                                if hasattr(elements[0], 'get'):
                                    value = elements[0].get(attr_name, '')
                                else:
                                    value = str(elements[0])
                            else:
                                value = str(elements[0]).strip()
                    except ImportError:
                        # 如果没有lxml，跳过XPath处理
                        value = f'XPath requires lxml library'
                
                elif extract_type == 'regex':
                    matches = re.findall(expression, response.content)
                    if matches:
                        value = matches[0] if isinstance(matches[0], str) else matches[0][0]
                
                extracted_data[field_name] = value
                
            except Exception as e:
                extracted_data[field_name] = f'Error: {str(e)}'
        
        return extracted_data
    
    def _test_link_extraction(self, response: SpiderResponse, config: dict) -> dict:
        """测试链接提取"""
        # 支持两种字段名格式：linkExtractionRules（前端使用）和 extractionRules（后端兼容）
        extraction_rules = config.get('linkExtractionRules', config.get('extractionRules', []))
        extracted_data = {}
        
        if not extraction_rules:
            return {'warning': 'No link extraction configuration found'}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 按字段分组提取数据
        field_data = {}
        
        for rule in extraction_rules:
            # 支持两种字段名格式：fieldName 和 field
            field_name = rule.get('fieldName') or rule.get('field')
            # 支持两种提取类型格式：extractType 和 type
            extract_type = rule.get('extractType') or rule.get('type')
            # 支持两种表达式格式：expression 和 selector
            expression = rule.get('expression') or rule.get('selector')
            
            if not field_name or not extract_type or not expression:
                continue
            
            try:
                values = []
                
                if extract_type == 'css':
                    elements = soup.select(expression)
                    for elem in elements:
                        if rule.get('attribute') == 'text':
                            value = elem.get_text().strip()
                        elif rule.get('attribute'):
                            attr_name = rule.get('attribute')
                            value = elem.get(attr_name, '')
                        else:
                            value = elem.get_text().strip()
                        
                        if value:
                            values.append(value)
                
                elif extract_type == 'xpath':
                    try:
                        from lxml import html
                        tree = html.fromstring(response.content)
                        elements = tree.xpath(expression)
                        
                        for elem in elements:
                            if rule.get('attribute') == 'text':
                                if hasattr(elem, 'text_content'):
                                    value = elem.text_content().strip()
                                else:
                                    value = str(elem).strip()
                            elif rule.get('attribute'):
                                attr_name = rule.get('attribute')
                                if hasattr(elem, 'get'):
                                    value = elem.get(attr_name, '')
                                else:
                                    value = str(elem)
                            else:
                                if hasattr(elem, 'text_content'):
                                    value = elem.text_content().strip()
                                else:
                                    value = str(elem).strip()
                            
                            if value:
                                values.append(value)
                                
                    except ImportError:
                        values = ['XPath requires lxml library']
                
                field_data[field_name] = values
                
            except Exception as e:
                field_data[field_name] = [f'Error: {str(e)}']
        
        # 创建压缩数据结构
        if field_data:
            # 获取最短的列表长度
            min_length = min(len(values) for values in field_data.values() if values)
            
            zipped_data = []
            for i in range(min_length):
                item = {}
                for field_name, values in field_data.items():
                    if i < len(values):
                        item[field_name] = values[i]
                zipped_data.append(item)
            
            extracted_data = {
                'extracted_links_count': len(zipped_data),
                'zipped_data': zipped_data,
                'extraction_method': 'linkExtractionRules'
            }
        
        return extracted_data
    
    def _test_link_extraction_custom_code(self, response: SpiderResponse, config: dict) -> dict:
        """使用自定义代码测试链接提取"""
        compiled_functions = config.get('_compiled_functions', {})
        process_next_requests = compiled_functions.get('process_next_requests')
        
        if process_next_requests:
            try:
                next_requests = process_next_requests(response.content, response.url)
                
                if isinstance(next_requests, list):
                    return {
                        'extracted_links_count': len(next_requests),
                        'links': [req.get('url', 'No URL') for req in next_requests if isinstance(req, dict)][:10],
                        'extraction_method': 'custom_code'
                    }
                else:
                    return {'warning': 'Custom code did not return a list'}
                    
            except Exception as e:
                return {'error': f'Custom code execution failed: {str(e)}'}
        
        return {'warning': 'No link extraction configuration found'}
    
    def _zip_extracted_fields(self, extracted_data: dict) -> list:
        """
        将提取的字段进行ZIP操作，组合成一组一组的数据
        
        Args:
            extracted_data: 提取的数据字典，格式如 {'link': [...], 'title': [...]}
            
        Returns:
            list: ZIP后的数据列表，每个元素是一个字典包含所有字段的对应值
        """
        if not extracted_data:
            return []
        
        # 获取所有字段名
        field_names = list(extracted_data.keys())
        if not field_names:
            return []
        
        # 获取所有字段的值列表
        field_values = [extracted_data[field] for field in field_names]
        
        # 使用zip将对应位置的值组合在一起
        zipped_results = []
        for values in zip(*field_values):
            item = {}
            for i, field_name in enumerate(field_names):
                item[field_name] = values[i]
            zipped_results.append(item)
        
        return zipped_results

    def export_data(self, format_type: str = "json") -> str:
        """导出数据"""
        data = self.get_extracted_data()
        
        if format_type == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format_type == "csv":
            if not data:
                return ""
            
            import csv
            import io
            
            output = io.StringIO()
            if data:
                # 获取所有字段名
                all_fields = set()
                for item in data:
                    all_fields.update(item["data"].keys())
                
                fieldnames = ["url", "step_id", "timestamp"] + sorted(all_fields)
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for item in data:
                    row = {
                        "url": item["url"],
                        "step_id": item["step_id"],
                        "timestamp": item["timestamp"]
                    }
                    row.update(item["data"])
                    writer.writerow(row)
            
            return output.getvalue()
        else:
            raise ValueError(f"不支持的导出格式: {format_type}")


def main():
    """主函数 - 示例用法"""
    # 示例配置
    config = {
        "taskInfo": {
            "name": "测试爬虫",
            "baseUrl": "https://httpbin.org",
            "requestInterval": 2,
            "concurrency": 1
        },
        "workflowSteps": [
            {
                "id": 1,
                "type": "request",
                "timeout": 120,
                "config": {
                    "url": "https://httpbin.org/html",
                    "method": "GET"
                }
            },
            {
                "id": 2,
                "type": "data_extraction",
                "timeout": 120,
                "config": {
                    "extractionRules": [
                        {
                            "fieldName": "title",
                            "extractType": "css",
                            "expression": "title",
                            "dataType": "text",
                            "required": True
                        }
                    ]
                }
            }
        ]
    }
    
    # 创建爬虫引擎
    engine = SpiderEngine(config)
    
    # 启动爬虫
    result = engine.start()
    
    print("执行结果:", result)
    print("统计信息:", engine._get_stats())
    print("提取的数据:", engine.get_extracted_data())


if __name__ == "__main__":
    main()