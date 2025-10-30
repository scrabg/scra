import request from '@/utils/request'

// 查询采集任务列表
export function listSpider(query) {
  return request({
    url: '/crawl/spider/list',
    method: 'get',
    params: query
  })
}

// 新增采集任务
export function addSpider(data) {
  return request({
    url: '/crawl/spider',
    method: 'post',
    data: data
  })
}

// 修改采集任务
export function updateSpider(data) {
  return request({
    url: '/crawl/spider',
    method: 'put',
    data: data
  })
}

// 删除采集任务
export function delSpider(id) {
  return request({
    url: '/crawl/spider/' + id,
    method: 'delete'
  })
}

// 启动采集任务
export function startSpider(id) {
  return request({
    url: '/crawl/spider/start/' + id,
    method: 'put'
  })
}

// 停止采集任务
export function stopSpider(id) {
  return request({
    url: '/crawl/spider/stop/' + id,
    method: 'put'
  })
}

// 保存采集任务配置
export function saveSpiderConfig(id, data) {
  return request({
    url: '/crawl/spider/save-config/' + id,
    method: 'put',
    data: data
  })
}

// 获取采集任务详情
export function getSpiderDetail(id) {
  return request({
    url: '/crawl/spider/' + id,
    method: 'get'
  })
}

// 测试爬虫配置
export function testSpiderConfig(data) {
  return request({
    url: '/crawl/spider/test-config',
    method: 'post',
    data: data
  })
}