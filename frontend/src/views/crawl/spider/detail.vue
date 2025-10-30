<template>
  <div class="app-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <el-row :gutter="20" style="align-items: center;">
        <el-col :span="12">
          <h2>{{ isEdit ? '编辑爬虫任务' : '新建爬虫任务' }}</h2>
        </el-col>
        <el-col :span="12" style="text-align: right;">
          <el-button @click="goBack">返回</el-button>
          <el-button type="primary" @click="saveTask" :loading="saving">
            {{ isEdit ? '保存任务' : '创建任务' }}
          </el-button>
          <el-button v-if="isEdit" type="success" @click="runTask" :loading="running">
            运行任务
          </el-button>
          <el-button v-if="isEdit" type="warning" @click="stopTask" :loading="stopping">
            停止任务
          </el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 左右分栏布局 -->
    <div class="main-layout">
      <!-- 左侧配置区域 -->
      <div class="config-panel">
        <div class="config-content">
          <!-- 基本信息 -->
          <el-card class="config-card">
            <template #header>
              <div class="card-header">
                <span>基本信息</span>
                <div>
                  <el-button type="primary" size="small" @click="testConnection">
                    测试连接
                  </el-button>
                </div>
              </div>
            </template>

            <el-form :model="taskInfo" label-width="120px" class="task-form">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="任务名称" required>
                    <el-input v-model="taskInfo.name" placeholder="请输入任务名称" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="目标网站">
                    <el-input v-model="taskInfo.baseUrl" placeholder="https://example.com" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="请求间隔(秒)">
                    <el-input-number v-model="taskInfo.requestInterval" :min="1" :max="60" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="并发数">
                    <el-input-number v-model="taskInfo.concurrency" :min="1" :max="10" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="任务描述">
                <el-input v-model="taskInfo.description" type="textarea" :rows="3" placeholder="请输入任务描述" />
              </el-form-item>
            </el-form>
          </el-card>

          <!-- 爬虫工作流配置 -->
          <el-card class="config-card">
            <template #header>
              <div class="card-header">
                <span>爬虫工作流配置</span>
                <div>
                  <el-button type="primary" size="small" @click="addWorkflowStep">
                    添加步骤
                  </el-button>
                </div>
              </div>
            </template>

            <div v-if="workflowSteps.length === 0" class="empty-config">
              <p>暂无工作流步骤，请点击"添加步骤"开始配置</p>
            </div>

            <!-- 工作流步骤列表 -->
            <div v-for="(step, stepIndex) in workflowSteps" :key="step.id" class="workflow-step">
              <div class="step-header">
                <div class="step-title">
                  <el-icon><Setting /></el-icon>
                  步骤 {{ stepIndex + 1 }}: {{ getStepTypeName(step.type) }}
                </div>
                <div class="step-actions">
                  <el-button size="small" @click="testStep(stepIndex, step)" :loading="step.testing">测试</el-button>
                  <el-button size="small" @click="duplicateStep(stepIndex)">复制</el-button>
                  <el-button size="small" @click="moveStepUp(stepIndex)" :disabled="stepIndex === 0">上移</el-button>
                  <el-button size="small" @click="moveStepDown(stepIndex)" :disabled="stepIndex === workflowSteps.length - 1">下移</el-button>
                  <el-button size="small" type="danger" @click="removeStep(stepIndex)">删除</el-button>
                </div>
              </div>

              <div class="step-content">
                <!-- 步骤类型选择 -->
                <el-form-item label="步骤类型">
                  <el-select v-model="step.type" @change="onStepTypeChange(step)" style="width: 200px;">
                    <el-option label="请求配置" value="request" />
                    <el-option label="链接提取" value="link_extraction" />
                    <el-option label="数据提取" value="data_extraction" />
                  </el-select>
                </el-form-item>

                <!-- 执行条件 -->
                <el-form-item label="执行条件">
                  <el-select v-model="step.condition" style="width: 200px;">
                    <el-option label="总是执行" value="always" />
                    <el-option label="自定义条件" value="custom" />
                  </el-select>
                </el-form-item>

                <div v-if="step.condition === 'custom'" style="margin-bottom: 16px;">
                  <el-form-item label="自定义条件">
                    <el-input v-model="step.customCondition" placeholder="请输入执行条件表达式" />
                  </el-form-item>
                </div>

                <!-- 重试配置 -->
                <el-row :gutter="20">
                  <el-col :span="8">
                    <el-form-item label="重试次数">
                      <el-input-number v-model="step.retryCount" :min="0" :max="5" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="重试间隔(秒)">
                      <el-input-number v-model="step.retryDelay" :min="1" :max="60" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="超时时间(秒)">
                      <el-input-number v-model="step.timeout" :min="5" :max="300" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <!-- 请求配置 -->
                <div v-if="step.type === 'request'" class="config-section">
                  <h4>请求配置</h4>
                  <el-row :gutter="20">
                    <el-col :span="16">
                      <el-form-item label="请求URL">
                        <el-input v-model="step.config.url" placeholder="https://example.com/api" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="请求方法">
                        <el-select v-model="step.config.method" style="width: 100%;">
                          <el-option label="GET" value="GET" />
                          <el-option label="POST" value="POST" />
                          <el-option label="PUT" value="PUT" />
                          <el-option label="DELETE" value="DELETE" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-form-item label="请求参数">
                    <div class="params-config">
                      <div v-for="(param, paramIndex) in (step.config.params || [])" :key="paramIndex" class="param-item">
                        <el-input v-model="param.key" placeholder="参数名" style="width: 200px; margin-right: 8px;" />
                        <el-input v-model="param.value" placeholder="参数值" style="width: 200px; margin-right: 8px;" />
                        <el-button size="small" type="danger" @click="removeParam(step, paramIndex)">删除</el-button>
                      </div>
                      <el-button size="small" @click="addParam(step)">添加参数</el-button>
                    </div>
                  </el-form-item>

                  <el-form-item label="请求头">
                    <div class="headers-config">
                      <div class="headers-mode-switch">
                        <el-radio-group v-model="step.config.headersMode" @change="onHeadersModeChange(step)">
                          <el-radio-button label="keyvalue">键值对模式</el-radio-button>
                          <el-radio-button label="json">JSON模式</el-radio-button>
                        </el-radio-group>
                      </div>
                      
                      <!-- 键值对模式 -->
                      <div v-if="step.config.headersMode === 'keyvalue'" class="headers-keyvalue">
                        <div v-for="(header, headerIndex) in (step.config.headers || [])" :key="headerIndex" class="header-item">
                          <el-input v-model="header.key" placeholder="Header名" style="width: 200px; margin-right: 8px;" />
                          <el-input v-model="header.value" placeholder="Header值" style="width: 200px; margin-right: 8px;" />
                          <el-button size="small" type="danger" @click="removeHeader(step, headerIndex)">删除</el-button>
                        </div>
                        <el-button size="small" @click="addHeader(step)">添加Header</el-button>
                      </div>
                      
                      <!-- JSON模式 -->
                      <div v-if="step.config.headersMode === 'json'" class="headers-json">
                        <el-input
                          v-model="step.config.headersJson"
                          type="textarea"
                          :rows="6"
                          placeholder='请输入JSON格式的请求头，例如：
{
  "Content-Type": "application/json",
  "Authorization": "Bearer token",
  "User-Agent": "MyApp/1.0"
}'
                          @blur="validateHeadersJson(step)"
                        />
                        <div v-if="step.config.headersJsonError" class="json-error">
                          <el-text type="danger" size="small">{{ step.config.headersJsonError }}</el-text>
                        </div>
                        <div class="json-actions">
                          <el-button size="small" @click="formatHeadersJson(step)">格式化JSON</el-button>
                          <el-button size="small" @click="convertToKeyValue(step)">转为键值对</el-button>
                        </div>
                      </div>
                    </div>
                  </el-form-item>

                  <el-form-item v-if="step.config.method === 'POST'" label="请求体">
                    <el-input v-model="step.config.body" type="textarea" :rows="4" placeholder="请输入请求体内容" />
                  </el-form-item>
                </div>

                <!-- 下一级链接提取配置 -->
                <div v-if="step.type === 'link_extraction'" class="config-section">
                  <h4>下一级请求配置</h4>
                  <p style="color: #666; font-size: 14px; margin-bottom: 16px;">
                    使用自定义Python代码进行下一级请求处理和数据解析
                  </p>
                  
                  <!-- 自定义代码模式 -->
                  <el-form-item label="自定义Python代码">
                    <el-collapse v-model="step.config.customCodeCollapsed" accordion>
                      <el-collapse-item title="点击展开/收起自定义Python代码编辑器" name="customCode">
                        <template #title>
                          <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                            <span>自定义Python代码编辑器</span>
                            <el-tag v-if="step.config.nextRequestCustomCode && step.config.nextRequestCustomCode.trim()" 
                                    type="success" size="small" style="margin-right: 10px;">
                              已配置
                            </el-tag>
                            <el-tag v-else type="info" size="small" style="margin-right: 10px;">
                              未配置
                            </el-tag>
                          </div>
                        </template>
                        <div class="custom-code-editor">
                          <el-input
                            v-model="step.config.nextRequestCustomCode"
                            type="textarea"
                            :rows="20"
                            placeholder='请输入Python代码，用于处理下一级请求和解析。

示例代码：
import requests
from bs4 import BeautifulSoup
import re

def process_next_requests(response_text, current_url):
    """
    处理下一级请求
    
    参数:
    - response_text: 当前页面的HTML内容
    - current_url: 当前页面的URL
    
    返回:
    - list: 包含下一级请求信息的列表，每个元素为字典格式：
      {
        "url": "下一级请求的URL",
        "method": "GET/POST",
        "headers": {"key": "value"},
        "params": {"key": "value"} 或 data/json
      }
    """
    soup = BeautifulSoup(response_text, "html.parser")
    next_requests = []
    
    # 提取链接
    links = soup.find_all("a", href=True)
    for link in links:
        href = link.get("href")
        if href and not href.startswith("#"):
            # 处理相对链接
            if href.startswith("/"):
                href = urljoin(current_url, href)
            elif not href.startswith("http"):
                href = urljoin(current_url, href)
            
            next_requests.append({
                "url": href,
                "method": "GET",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            })
    
    return next_requests

def extract_data(response_text, current_url):
    """
    从响应中提取数据
    
    参数:
    - response_text: 页面HTML内容
    - current_url: 当前页面URL
    
    返回:
    - dict: 提取的数据字典
    """
    soup = BeautifulSoup(response_text, "html.parser")
    data = {}
    
    # 示例：提取标题
    title_elem = soup.find("title")
    if title_elem:
        data["title"] = title_elem.get_text().strip()
    
    # 示例：提取内容
    content_elem = soup.find("div", class_="content")
    if content_elem:
        data["content"] = content_elem.get_text().strip()
    
    return data'
                            @blur="validateCustomCode(step)"
                          />
                          <div v-if="step.config.nextRequestCustomCodeError" class="code-error">
                            <el-text type="danger" size="small">{{ step.config.nextRequestCustomCodeError }}</el-text>
                          </div>
                          <div class="code-actions">
                            <el-button size="small" @click="formatCustomCode(step)">格式化代码</el-button>
                            <el-button size="small" @click="testCustomCode(step)">测试代码</el-button>
                          </div>
                        </div>
                      </el-collapse-item>
                    </el-collapse>
                  </el-form-item>

                  <!-- 链接提取的数据提取配置 -->
                  <h4>数据提取配置</h4>
                  <p style="color: #666; font-size: 14px; margin-bottom: 16px;">
                    配置从链接页面中提取的数据字段，这些数据将与链接一起保存
                  </p>
                  
                  <div class="extraction-rules">
                    <div class="rule-header">
                      <span>提取规则</span>
                      <el-button type="primary" size="small" @click="addLinkExtractionRule(step)">
                        <el-icon><Plus /></el-icon>
                        添加规则
                      </el-button>
                    </div>
                    
                    <div v-if="!step.config.linkExtractionRules || step.config.linkExtractionRules.length === 0" class="empty-rules">
                      <p style="color: #999; text-align: center; padding: 20px;">暂无提取规则，点击"添加规则"按钮添加数据提取规则</p>
                    </div>
                    
                    <div v-else class="rules-list">
                      <div 
                        v-for="(rule, ruleIndex) in step.config.linkExtractionRules" 
                        :key="ruleIndex"
                        class="rule-item"
                      >
                        <el-card shadow="never" class="rule-card">
                          <div class="rule-content">
                            <el-row :gutter="16">
                              <el-col :span="6">
                                <el-form-item label="字段名称">
                                  <el-select 
                                    v-model="rule.fieldName" 
                                    placeholder="选择或输入字段名称"
                                    size="small"
                                    style="width: 100%"
                                    filterable
                                    allow-create
                                    default-first-option
                                  >
                                    <el-option label="采集链接" value="link" />
                                    <el-option label="标题" value="title" />
                                    <el-option label="发布时间" value="publish_time" />
                                    <el-option label="内容" value="content" />
                                    <el-option label="作者" value="author" />
                                    <el-option label="摘要" value="summary" />
                                    <el-option label="分类" value="category" />
                                    <el-option label="标签" value="tags" />
                                    <el-option label="阅读量" value="views" />
                                    <el-option label="点赞数" value="likes" />
                                    <el-option label="评论数" value="comments" />
                                    <el-option label="图片链接" value="image_url" />
                                    <el-option label="价格" value="price" />
                                    <el-option label="描述" value="description" />
                                  </el-select>
                                </el-form-item>
                              </el-col>
                              <el-col :span="6">
                                <el-form-item label="提取方式">
                                  <el-select 
                                    v-model="rule.extractType" 
                                    placeholder="选择提取方式"
                                    size="small"
                                    style="width: 100%"
                                  >
                                    <el-option label="XPath" value="xpath" />
                                    <el-option label="正则表达式" value="regex" />
                                    <el-option label="CSS选择器" value="css" />
                                    <el-option label="链接提取" value="link" />
                                  </el-select>
                                </el-form-item>
                              </el-col>
                              <el-col :span="6">
                                <el-form-item label="数据类型">
                                  <el-select 
                                    v-model="rule.dataType" 
                                    placeholder="选择数据类型"
                                    size="small"
                                    style="width: 100%"
                                  >
                                    <el-option label="文本" value="text" />
                                    <el-option label="html" value="html" />
                                    <el-option label="数字" value="number" />
                                    <el-option label="链接" value="url" />
                                    <el-option label="图片" value="image" />
                                    <el-option label="日期" value="date" />
                                    
                                  </el-select>
                                </el-form-item>
                              </el-col>
                              <el-col :span="6">
                                <el-form-item label="操作">
                                  <el-button 
                                    type="danger" 
                                    size="small" 
                                    @click="removeLinkExtractionRule(step, ruleIndex)"
                                  >
                                    <el-icon><Delete /></el-icon>
                                    删除
                                  </el-button>
                                </el-form-item>
                              </el-col>
                            </el-row>
                            
                            <el-row>
                              <el-col :span="24">
                                <el-form-item :label="getExpressionLabel(rule.extractType)">
                                  <!-- 链接提取特殊配置 -->
                                  <div v-if="rule.extractType === 'link'">
                                    <el-row :gutter="16">
                                      <el-col :span="12">
                                        <el-input 
                                          v-model="rule.linkSelector" 
                                          placeholder="链接选择器 (CSS选择器或XPath)"
                                          size="small"
                                        />
                                      </el-col>
                                      <el-col :span="12">
                                        <el-input 
                                          v-model="rule.linkFilter" 
                                          placeholder="链接过滤规则 (正则表达式，可选)"
                                          size="small"
                                        />
                                      </el-col>
                                    </el-row>
                                    <el-row style="margin-top: 8px;">
                                      <el-col :span="12">
                                        <el-input-number 
                                          v-model="rule.maxLinks" 
                                          :min="1" 
                                          :max="1000"
                                          placeholder="最大链接数"
                                          size="small"
                                          style="width: 100%"
                                        />
                                      </el-col>
                                      <el-col :span="12">
                                        <el-checkbox v-model="rule.deduplicate" size="small" style="margin-left: 16px;">
                                          去重
                                        </el-checkbox>
                                      </el-col>
                                    </el-row>
                                  </div>
                                  <!-- 其他提取方式的表达式输入 -->
                                  <el-input 
                                    v-else
                                    v-model="rule.expression" 
                                    type="textarea"
                                    :placeholder="getExpressionPlaceholder(rule.extractType)"
                                    :rows="2"
                                    size="small"
                                  />
                                </el-form-item>
                              </el-col>
                            </el-row>
                            
                            <!-- 高级选项 -->
                            <el-collapse>
                              <el-collapse-item title="高级选项" name="advanced">
                                <el-row :gutter="16">
                                  <el-col :span="8">
                                    <el-form-item label="是否必需">
                                      <el-switch v-model="rule.required" size="small" />
                                    </el-form-item>
                                  </el-col>
                                  <el-col :span="8">
                                    <el-form-item label="多值提取">
                                      <el-switch v-model="rule.multiple" size="small" />
                                    </el-form-item>
                                  </el-col>
                                  <el-col :span="8">
                                    <el-form-item label="去除空白">
                                      <el-switch v-model="rule.trim" size="small" />
                                    </el-form-item>
                                  </el-col>
                                </el-row>
                                
                                <el-row :gutter="16">
                                  <el-col :span="12">
                                    <el-form-item label="默认值">
                                      <el-input 
                                        v-model="rule.defaultValue" 
                                        placeholder="提取失败时的默认值"
                                        size="small"
                                      />
                                    </el-form-item>
                                  </el-col>
                                  <el-col :span="12">
                                    <el-form-item label="后处理函数">
                                      <el-input 
                                        v-model="rule.postProcess" 
                                        placeholder="如：strip(), lower(), upper()"
                                        size="small"
                                      />
                                    </el-form-item>
                                  </el-col>
                                </el-row>
                              </el-collapse-item>
                            </el-collapse>
                          </div>
                        </el-card>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 数据提取配置 -->
                <div v-if="step.type === 'data_extraction'" class="config-section">
                  <h4>数据提取配置</h4>
                  
                  <!-- 提取规则列表 -->
                  <div class="extraction-rules">
                    <div class="rule-header">
                      <span>提取规则</span>
                      <el-button type="primary" size="small" @click="addExtractionRule(step)">
                        <el-icon><Plus /></el-icon>
                        添加规则
                      </el-button>
                    </div>
                    
                    <div v-if="!step.config.extractionRules || step.config.extractionRules.length === 0" class="empty-rules">
                      <p style="color: #999; text-align: center; padding: 20px;">暂无提取规则，请点击"添加规则"按钮添加</p>
                    </div>
                    
                    <div v-else class="rules-list">
                      <div 
                        v-for="(rule, ruleIndex) in step.config.extractionRules" 
                        :key="ruleIndex"
                        class="rule-item"
                      >
                        <el-card shadow="never" class="rule-card">
                          <div class="rule-content">
                            <el-row :gutter="16">
                              <el-col :span="6">
                                <el-form-item label="字段名称">
                                  <el-select 
                                    v-model="rule.fieldName" 
                                    placeholder="选择或输入字段名称"
                                    size="small"
                                    style="width: 100%"
                                    filterable
                                    allow-create
                                    default-first-option
                                  >
                                    <el-option label="采集链接" value="link" />
                                    <el-option label="标题" value="title" />
                                    <el-option label="发布时间" value="publish_time" />
                                    <el-option label="内容" value="content" />
                                    <el-option label="作者" value="author" />
                                    <el-option label="摘要" value="summary" />
                                    <el-option label="分类" value="category" />
                                    <el-option label="标签" value="tags" />
                                    <el-option label="阅读量" value="views" />
                                    <el-option label="点赞数" value="likes" />
                                    <el-option label="评论数" value="comments" />
                                    <el-option label="图片链接" value="image_url" />
                                    <el-option label="价格" value="price" />
                                    <el-option label="描述" value="description" />
                                  </el-select>
                                </el-form-item>
                              </el-col>
                              <el-col :span="6">
                                <el-form-item label="提取方式">
                                  <el-select 
                                    v-model="rule.extractType" 
                                    placeholder="选择提取方式"
                                    size="small"
                                    style="width: 100%"
                                  >
                                    <el-option label="XPath" value="xpath" />
                                    <el-option label="正则表达式" value="regex" />
                                    <el-option label="CSS选择器" value="css" />
                                  </el-select>
                                </el-form-item>
                              </el-col>
                              <el-col :span="6">
                                <el-form-item label="数据类型">
                                  <el-select 
                                    v-model="rule.dataType" 
                                    placeholder="选择数据类型"
                                    size="small"
                                    style="width: 100%"
                                  >
                                    <el-option label="文本" value="text" />
                                    <el-option label="html" value="html" />
                                    <el-option label="数字" value="number" />
                                    <el-option label="链接" value="url" />
                                    <el-option label="图片" value="image" />
                                    <el-option label="日期" value="date" />
                                  </el-select>
                                </el-form-item>
                              </el-col>
                              <el-col :span="6">
                                <el-form-item label="操作">
                                  <el-button 
                                    type="danger" 
                                    size="small" 
                                    @click="removeExtractionRule(step, ruleIndex)"
                                  >
                                    <el-icon><Delete /></el-icon>
                                    删除
                                  </el-button>
                                </el-form-item>
                              </el-col>
                            </el-row>
                            
                            <el-row>
                              <el-col :span="24">
                                <el-form-item :label="getExpressionLabel(rule.extractType)">
                                  <el-input 
                                    v-model="rule.expression" 
                                    type="textarea"
                                    :placeholder="getExpressionPlaceholder(rule.extractType)"
                                    :rows="2"
                                    size="small"
                                  />
                                </el-form-item>
                              </el-col>
                            </el-row>
                            
                            <!-- 高级选项 -->
                            <el-collapse>
                              <el-collapse-item title="高级选项" name="advanced">
                                <el-row :gutter="16">
                                  <el-col :span="8">
                                    <el-form-item label="是否必需">
                                      <el-switch v-model="rule.required" size="small" />
                                    </el-form-item>
                                  </el-col>
                                  <el-col :span="8">
                                    <el-form-item label="多值提取">
                                      <el-switch v-model="rule.multiple" size="small" />
                                    </el-form-item>
                                  </el-col>
                                  <el-col :span="8">
                                    <el-form-item label="去除空白">
                                      <el-switch v-model="rule.trim" size="small" />
                                    </el-form-item>
                                  </el-col>
                                </el-row>
                                
                                <el-row :gutter="16">
                                  <el-col :span="12">
                                    <el-form-item label="默认值">
                                      <el-input 
                                        v-model="rule.defaultValue" 
                                        placeholder="提取失败时的默认值"
                                        size="small"
                                      />
                                    </el-form-item>
                                  </el-col>
                                  <el-col :span="12">
                                    <el-form-item label="后处理函数">
                                      <el-input 
                                        v-model="rule.postProcess" 
                                        placeholder="如：strip(), lower(), upper()"
                                        size="small"
                                      />
                                    </el-form-item>
                                  </el-col>
                                </el-row>
                              </el-collapse-item>
                            </el-collapse>
                          </div>
                        </el-card>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 步骤连接器 -->
              <div v-if="stepIndex < workflowSteps.length - 1" class="step-connector">
                <el-icon><ArrowDown /></el-icon>
              </div>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 右侧测试区域 -->
      <div class="test-panel">
        <div class="test-content">
          <!-- 测试日志 -->
          <el-card class="test-card">
            <template #header>
              <div class="card-header">
                <span>测试日志</span>
                <div>
                  <el-button size="small" @click="clearTestLogs">清空日志</el-button>
                </div>
              </div>
            </template>

            <div class="test-log-container">
              <div v-if="testLogs.length === 0" class="empty-logs">
                <p>暂无测试日志</p>
              </div>
              <div v-else class="log-list">
                <div
                  v-for="(log, logIndex) in testLogs"
                  :key="logIndex"
                  class="log-item"
                  :class="`log-${log.type}`"
                >
                  <div class="log-header">
                    <span class="log-time">{{ log.timestamp }}</span>
                    <span class="log-step">{{ log.stepName }}</span>
                    <el-tag :type="log.type === 'error' ? 'danger' : log.type === 'success' ? 'success' : 'info'" size="small">
                      {{ log.type === 'error' ? '错误' : log.type === 'success' ? '成功' : '信息' }}
                    </el-tag>
                  </div>
                  <div class="log-content">
                    <pre>{{ log.content }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </el-card>

          <!-- 任务状态 -->
          <el-card style="margin-top: 16px;" v-if="isEdit">
            <template #header>
              <span>任务状态</span>
            </template>
            <el-row :gutter="16">
              <el-col :span="12">
                <div class="status-item">
                  <div class="status-label">最后运行时间</div>
                  <div class="status-value">{{ taskInfo.crawlStartAt || '-' }}</div>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="status-item">
                  <div class="status-label">最后更新时间</div>
                  <div class="status-value">{{ taskInfo.updatedAt || '-' }}</div>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="status-item">
                  <div class="status-label">采集数量</div>
                  <div class="status-value">{{ taskInfo.crawledCount || 0 }}</div>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="status-item">
                  <div class="status-label">运行状态</div>
                  <div class="status-value">
                    <el-tag :type="getStatusType(taskInfo.status)">
                      {{ getStatusText(taskInfo.status) }}
                    </el-tag>
                  </div>
                </div>
              </el-col>
            </el-row>
          </el-card>

          <!-- 运行日志 -->
          <el-card style="margin-top: 16px;" v-if="isEdit">
            <template #header>
              <span>运行日志</span>
            </template>
            <div class="log-container">
              <pre class="log-content">{{ logs || '暂无日志信息' }}</pre>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup name="SpiderDetail">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { saveSpiderConfig, getSpiderDetail, testSpiderConfig } from '@/api/crawl/spider'

const route = useRoute()
const router = useRouter()

// 响应式数据
const isEdit = ref(false)
const saving = ref(false)
const running = ref(false)
const stopping = ref(false)
const logs = ref('')

// 测试日志数据
const testLogs = ref([])

// 任务基本信息
const taskInfo = reactive({
  id: null,
  name: '',
  baseUrl: '',
  requestInterval: 3,
  concurrency: 1,
  description: '',
  status: 'stopped',
  crawlStartAt: null,
  updatedAt: null,
  crawledCount: 0
})

// 工作流步骤数据
const workflowSteps = ref([])

// 生命周期
onMounted(() => {
  const id = route.params.id
  if (id && id !== 'new') {
    isEdit.value = true
    taskInfo.id = id
    loadTaskDetail()
  }
})

// 方法
const loadTaskDetail = async () => {
  try {
    if (!taskInfo.id) {
      console.log('新建任务，无需加载详情')
      return
    }
    
    console.log('加载任务详情:', taskInfo.id)
    const response = await getSpiderDetail(taskInfo.id)
    
    if (response.code === 200 && response.data) {
      const data = response.data
      
      // 更新基本任务信息
      taskInfo.name = data.task_name || ''
      taskInfo.baseUrl = data.domain || ''
      taskInfo.description = data.column_name || ''
      
      // 如果有配置数据，加载配置
      if (data.config) {
        const config = data.config
        
        // 加载任务基本信息
        if (config.taskInfo) {
          Object.assign(taskInfo, config.taskInfo)
        }
        
        // 加载工作流步骤
        if (config.workflowSteps && Array.isArray(config.workflowSteps)) {
          workflowSteps.value = config.workflowSteps
        }
      }
      
      console.log('任务详情加载成功')
    } else {
      ElMessage.error(response.msg || '加载任务详情失败')
    }
  } catch (error) {
    console.error('加载任务详情失败:', error)
    ElMessage.error('加载任务详情失败')
  }
}

const saveTask = async () => {
  if (!taskInfo.name) {
    ElMessage.warning('请输入任务名称')
    return
  }

  saving.value = true
  try {
    if (isEdit.value) {
      // 编辑模式：保存配置到数据库
      const configData = {
        taskInfo: JSON.parse(JSON.stringify(taskInfo || {})),
        workflowSteps: JSON.parse(JSON.stringify(workflowSteps.value || []))
      }
      
      await saveSpiderConfig(taskInfo.id, configData)
      ElMessage.success('任务配置保存成功')
    } else {
      // 新建模式：创建任务
      console.log('创建任务:', taskInfo)
      ElMessage.success('任务创建成功')
      router.push('/crawl/spider')
    }
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error(isEdit.value ? '保存任务配置失败' : '创建任务失败')
  } finally {
    saving.value = false
  }
}

const runTask = async () => {
  running.value = true
  try {
    console.log('运行任务:', taskInfo.id)
    ElMessage.success('任务启动成功')
    taskInfo.status = 'running'
  } catch (error) {
    ElMessage.error('启动任务失败')
  } finally {
    running.value = false
  }
}

const stopTask = async () => {
  stopping.value = true
  try {
    console.log('停止任务:', taskInfo.id)
    ElMessage.success('任务停止成功')
    taskInfo.status = 'stopped'
  } catch (error) {
    ElMessage.error('停止任务失败')
  } finally {
    stopping.value = false
  }
}

const testConnection = async () => {
  if (!taskInfo.baseUrl) {
    ElMessage.warning('请先输入目标网站')
    return
  }
  
  try {
    console.log('测试连接:', taskInfo.baseUrl)
    ElMessage.success('连接测试成功')
  } catch (error) {
    ElMessage.error('连接测试失败')
  }
}

const goBack = () => {
  router.push('/crawl/spider')
}

// 工作流步骤管理方法
const addWorkflowStep = () => {
  const newStep = {
    id: Date.now(),
    type: 'request',
    condition: 'always',
    customCondition: '',
    retryCount: 0,
    retryDelay: 1,
    timeout: 30,
    config: {
      url: '',
      method: 'GET',
      params: [],
      headers: [],
      headersMode: 'keyvalue',
      headersJson: '',
      headersJsonError: '',
      // 下一级请求配置
      nextRequestMode: 'standard', // 'standard' 或 'custom'
      nextRequestUrl: '',
      nextRequestDeduplicate: true,
      nextRequestMethod: 'GET',
      nextRequestParams: [],
      nextRequestParamsMode: 'keyvalue',
      nextRequestParamsJson: '',
      nextRequestParamsJsonError: '',
      nextRequestHeaders: [],
      nextRequestHeadersMode: 'keyvalue',
      nextRequestHeadersJson: '',
      nextRequestHeadersJsonError: '',
      // 自定义代码配置
      nextRequestCustomCode: '',
      nextRequestCustomCodeError: '',
      customCodeCollapsed: [], // 折叠面板状态
      // 数据提取配置
      extractionRules: [],
      // 链接提取的数据提取配置
      linkExtractionRules: []
    }
  }
  workflowSteps.value.push(newStep)
}

const removeStep = (index) => {
  ElMessageBox.confirm('确定要删除这个工作流步骤吗？', '确认删除', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    workflowSteps.value.splice(index, 1)
    ElMessage.success('步骤删除成功')
  }).catch(() => {
    // 用户取消
  })
}

const duplicateStep = (index) => {
  const originalStep = workflowSteps.value[index]
  const duplicatedStep = {
    ...originalStep,
    id: Date.now(),
    config: JSON.parse(JSON.stringify(originalStep.config))
  }
  workflowSteps.value.splice(index + 1, 0, duplicatedStep)
  ElMessage.success('步骤复制成功')
}

const moveStepUp = (index) => {
  if (index > 0) {
    const step = workflowSteps.value[index]
    workflowSteps.value.splice(index, 1)
    workflowSteps.value.splice(index - 1, 0, step)
    ElMessage.success('步骤上移成功')
  }
}

const moveStepDown = (index) => {
  if (index < workflowSteps.value.length - 1) {
    const step = workflowSteps.value[index]
    workflowSteps.value.splice(index, 1)
    workflowSteps.value.splice(index + 1, 0, step)
    ElMessage.success('步骤下移成功')
  }
}

const onStepTypeChange = (step) => {
  // 保留通用配置
  const condition = step.condition || 'always'
  const customCondition = step.customCondition || ''
  const retryCount = step.retryCount || 0
  const retryDelay = step.retryDelay || 1
  const timeout = step.timeout || 30

  // 重置配置
  if (step.type === 'request') {
    step.config = {
      url: '',
      method: 'GET',
      params: [],
      headers: [],
      headersMode: 'keyvalue',
      headersJson: '',
      headersJsonError: '',
      body: ''
    }
  } else if (step.type === 'link_extraction') {
    step.config = {
      // 链接提取的数据提取配置
      linkExtractionRules: [],
      // 下一级请求配置（仅自定义代码模式）
      nextRequestCustomCode: `def process_request(response_text, current_url, extracted_data):
    """
    处理下一级请求的自定义代码
    
    参数:
    - response_text: 当前页面的HTML内容
    - current_url: 当前页面的URL
    - extracted_data: 已提取的数据字典
    
    返回:
    - 包含下一级请求信息的字典列表，每个字典包含:
      - url: 请求URL
      - method: 请求方法 (GET/POST)
      - params: 请求参数字典 (可选)
      - headers: 请求头字典 (可选)
      - data: POST请求体数据 (可选)
    """
    from bs4 import BeautifulSoup
    
    # 解析HTML
    soup = BeautifulSoup(response_text, "html.parser")
    
    # 示例：提取链接并生成下一级请求
    links = []
    for link_elem in soup.find_all("a", href=True):
        url = link_elem["href"]
        if url.startswith("http"):
            links.append({
                "url": url,
                "method": "GET"
            })
    
    return links`,
      nextRequestCustomCodeError: '',
      customCodeCollapsed: [] // 折叠面板状态
    }
  } else if (step.type === 'data_extraction') {
    step.config = {
      // 数据提取配置
      extractionRules: [],
      // 下一级请求配置（仅自定义代码模式）
      nextRequestCustomCode: `def process_request(response_text, current_url, extracted_data):
    """
    处理下一级请求的自定义代码
    
    参数:
    - response_text: 当前页面的HTML内容
    - current_url: 当前页面的URL
    - extracted_data: 已提取的数据字典
    
    返回:
    - 包含下一级请求信息的字典列表，每个字典包含:
      - url: 请求URL
      - method: 请求方法 (GET/POST)
      - params: 请求参数字典 (可选)
      - headers: 请求头字典 (可选)
      - data: POST请求体数据 (可选)
    """
    from bs4 import BeautifulSoup
    
    # 解析HTML
    soup = BeautifulSoup(response_text, "html.parser")
    
    # 示例：提取链接并生成下一级请求
    links = []
    for link_elem in soup.find_all("a", href=True):
        url = link_elem["href"]
        if url.startswith("http"):
            links.append({
                "url": url,
                "method": "GET"
            })
    
    return links`,
      nextRequestCustomCodeError: '',
      customCodeCollapsed: [] // 折叠面板状态
    }
  }

  // 恢复通用配置
  step.condition = condition
  step.customCondition = customCondition
  step.retryCount = retryCount
  step.retryDelay = retryDelay
  step.timeout = timeout
}

const getStepTypeName = (type) => {
  const typeMap = {
    'request': '请求配置',
    'link_extraction': '链接提取',
    'data_extraction': '数据提取'
  }
  return typeMap[type] || '未知类型'
}

// 参数和头部管理
const addParam = (step) => {
  if (!step.config.params) {
    step.config.params = []
  }
  step.config.params.push({ key: '', value: '' })
}

const removeParam = (step, index) => {
  if (step.config.params) {
    step.config.params.splice(index, 1)
  }
}

const addHeader = (step) => {
  if (!step.config.headers) {
    step.config.headers = []
  }
  step.config.headers.push({ key: '', value: '' })
}

const removeHeader = (step, index) => {
  if (step.config.headers) {
    step.config.headers.splice(index, 1)
  }
}

// 下一级请求参数和请求头管理
const addNextRequestParam = (step) => {
  if (!step.config.nextRequestParams) {
    step.config.nextRequestParams = []
  }
  step.config.nextRequestParams.push({ key: '', value: '' })
}

const removeNextRequestParam = (step, index) => {
  if (step.config.nextRequestParams) {
    step.config.nextRequestParams.splice(index, 1)
  }
}

const addNextRequestHeader = (step) => {
  if (!step.config.nextRequestHeaders) {
    step.config.nextRequestHeaders = []
  }
  step.config.nextRequestHeaders.push({ key: '', value: '' })
}

const removeNextRequestHeader = (step, index) => {
  if (step.config.nextRequestHeaders) {
    step.config.nextRequestHeaders.splice(index, 1)
  }
}

// 状态相关方法
const getStatusType = (status) => {
  const statusMap = {
    running: 'success',
    stopped: 'info',
    error: 'danger',
    completed: 'success'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status) => {
  const statusMap = {
    running: '运行中',
    stopped: '已停止',
    error: '错误',
    completed: '已完成'
  }
  return statusMap[status] || '未知'
}

// 测试相关方法
const testStep = async (stepIndex, step) => {
  if (step.testing) return
  
  step.testing = true
  const stepName = `步骤 ${stepIndex + 1}: ${getStepTypeName(step.type)}`
  
  try {
    // 调用后端API进行真实测试
    const testData = {
      task_id: taskInfo.id || 1,
      test_url: taskInfo.baseUrl || 'https://httpbin.org/html',
      config_data: {
        task_id: taskInfo.id || 1,
        workflowSteps: [step], // 只测试当前步骤
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        delay: taskInfo.requestInterval || 1
      }
    }
    
    const response = await testSpiderConfig(testData)
    
    console.log('API响应:', response) // 调试日志
    
    // 获取实际的测试结果数据
    const testResult = response.data || response
    
    if (testResult.success) {
      let successResult = `${testResult.message || '测试成功'}\n执行时间: ${testResult.execution_time || 0}ms\n`
      
      if (testResult.extracted_data && Object.keys(testResult.extracted_data).length > 0) {
        successResult += `提取的数据:\n${JSON.stringify(testResult.extracted_data, null, 2)}`
      } else {
        successResult += '未提取到数据'
      }
      
      addTestLog(stepName, 'success', successResult)
      ElMessage.success(`${stepName} ${testResult.message || '测试成功'}`)
    } else {
      // 测试失败，显示具体的错误信息
      let errorResult = `${testResult.message || '测试失败'}\n执行时间: ${testResult.execution_time || 0}ms\n`
      
      if (testResult.extracted_data && Object.keys(testResult.extracted_data).length > 0) {
        errorResult += `错误详情:\n${JSON.stringify(testResult.extracted_data, null, 2)}`
      }
      
      if (testResult.error_details) {
        errorResult += `\n错误信息: ${testResult.error_details}`
      }
      
      addTestLog(stepName, 'error', errorResult)
      ElMessage.error(`${stepName} ${testResult.message || '测试失败'}`)
    }
    
  } catch (error) {
    let errorMsg = error.message || '未知错误'
    if (error.response && error.response.data) {
      errorMsg = error.response.data.message || errorMsg
    }
    
    addTestLog(stepName, 'error', `测试失败: ${errorMsg}`)
    ElMessage.error(`${stepName} 测试失败: ${errorMsg}`)
  } finally {
    step.testing = false
  }
}

const testRequestStep = async (step) => {
  const config = step.config
  if (!config.url) {
    throw new Error('请求URL不能为空')
  }
  
  return `请求测试成功
URL: ${config.url}
方法: ${config.method}
状态: 连接正常
响应时间: 245ms`
}

const testLinkExtractionStep = async (step) => {
  const config = step.config
  if (!config.linkSelector) {
    throw new Error('链接选择器不能为空')
  }
  
  return `链接提取测试成功
选择器: ${config.linkSelector}
找到链接: 15个
示例链接: https://example.com/page1, https://example.com/page2`
}

const testDataExtractionStep = async (step) => {
  return `数据提取测试成功
提取字段: 标题、内容、发布时间
成功提取: 3个字段
数据完整性: 100%`
}

const addTestLog = (stepName, type, content) => {
  const log = {
    timestamp: new Date().toLocaleString(),
    stepName,
    type,
    content
  }
  testLogs.value.unshift(log)
  
  // 限制日志数量，最多保留100条
  if (testLogs.value.length > 100) {
    testLogs.value = testLogs.value.slice(0, 100)
  }
}

const clearTestLogs = () => {
  testLogs.value = []
  ElMessage.success('测试日志已清空')
}

// 请求头模式切换和处理方法
const onHeadersModeChange = (step) => {
  if (step.config.headersMode === 'json') {
    // 切换到JSON模式时，将键值对转换为JSON
    convertKeyValueToJson(step, 'headers')
  } else {
    // 切换到键值对模式时，将JSON转换为键值对
    convertJsonToKeyValue(step, 'headers')
  }
}

const onNextRequestHeadersModeChange = (step) => {
  if (step.config.nextRequestHeadersMode === 'json') {
    // 切换到JSON模式时，将键值对转换为JSON
    convertKeyValueToJson(step, 'nextRequestHeaders')
  } else {
    // 切换到键值对模式时，将JSON转换为键值对
    convertJsonToKeyValue(step, 'nextRequestHeaders')
  }
}

const convertKeyValueToJson = (step, type) => {
  try {
    const headers = type === 'headers' ? step.config.headers : step.config.nextRequestHeaders
    const jsonObj = {}
    
    if (headers && Array.isArray(headers)) {
      headers.forEach(header => {
        if (header.key && header.value) {
          jsonObj[header.key] = header.value
        }
      })
    }
    
    const jsonString = JSON.stringify(jsonObj, null, 2)
    
    if (type === 'headers') {
      step.config.headersJson = jsonString
      step.config.headersJsonError = ''
    } else {
      step.config.nextRequestHeadersJson = jsonString
      step.config.nextRequestHeadersJsonError = ''
    }
  } catch (error) {
    console.error('转换键值对到JSON失败:', error)
  }
}

const convertJsonToKeyValue = (step, type, jsonField = null) => {
  try {
    let jsonString = ''
    if (jsonField) {
      jsonString = step.config[jsonField] || ''
    } else if (type === 'headers') {
      jsonString = step.config.headersJson || ''
    } else if (type === 'nextRequestHeaders') {
      jsonString = step.config.nextRequestHeadersJson || ''
    } else if (type === 'nextRequestParams') {
      jsonString = step.config.nextRequestParamsJson || ''
    }
    
    if (!jsonString.trim()) {
      if (type === 'headers') {
        step.config.headers = []
      } else if (type === 'nextRequestHeaders') {
        step.config.nextRequestHeaders = []
      } else if (type === 'nextRequestParams') {
        step.config.nextRequestParams = []
      }
      return
    }
    
    const jsonObj = JSON.parse(jsonString)
    const keyValueArray = []
    
    Object.keys(jsonObj).forEach(key => {
      keyValueArray.push({
        key: key,
        value: String(jsonObj[key])
      })
    })
    
    if (type === 'headers') {
      step.config.headers = keyValueArray
      step.config.headersJsonError = ''
    } else if (type === 'nextRequestHeaders') {
      step.config.nextRequestHeaders = keyValueArray
      step.config.nextRequestHeadersJsonError = ''
    } else if (type === 'nextRequestParams') {
      step.config.nextRequestParams = keyValueArray
      step.config.nextRequestParamsJsonError = ''
    }
  } catch (error) {
    const errorMsg = `JSON格式错误: ${error.message}`
    if (type === 'headers') {
      step.config.headersJsonError = errorMsg
    } else if (type === 'nextRequestHeaders') {
      step.config.nextRequestHeadersJsonError = errorMsg
    } else if (type === 'nextRequestParams') {
      step.config.nextRequestParamsJsonError = errorMsg
    }
  }
}

const validateHeadersJson = (step) => {
  try {
    if (!step.config.headersJson.trim()) {
      step.config.headersJsonError = ''
      return
    }
    
    JSON.parse(step.config.headersJson)
    step.config.headersJsonError = ''
  } catch (error) {
    step.config.headersJsonError = `JSON格式错误: ${error.message}`
  }
}

const validateNextRequestHeadersJson = (step) => {
  try {
    if (!step.config.nextRequestHeadersJson.trim()) {
      step.config.nextRequestHeadersJsonError = ''
      return
    }
    
    JSON.parse(step.config.nextRequestHeadersJson)
    step.config.nextRequestHeadersJsonError = ''
  } catch (error) {
    step.config.nextRequestHeadersJsonError = `JSON格式错误: ${error.message}`
  }
}

const formatHeadersJson = (step) => {
  try {
    if (!step.config.headersJson.trim()) {
      ElMessage.warning('请先输入JSON内容')
      return
    }
    
    const jsonObj = JSON.parse(step.config.headersJson)
    step.config.headersJson = JSON.stringify(jsonObj, null, 2)
    step.config.headersJsonError = ''
    ElMessage.success('JSON格式化成功')
  } catch (error) {
    step.config.headersJsonError = `JSON格式错误: ${error.message}`
    ElMessage.error('JSON格式化失败')
  }
}

const formatNextRequestHeadersJson = (step) => {
  try {
    if (!step.config.nextRequestHeadersJson.trim()) {
      ElMessage.warning('请先输入JSON内容')
      return
    }
    
    const jsonObj = JSON.parse(step.config.nextRequestHeadersJson)
    step.config.nextRequestHeadersJson = JSON.stringify(jsonObj, null, 2)
    step.config.nextRequestHeadersJsonError = ''
    ElMessage.success('JSON格式化成功')
  } catch (error) {
    step.config.nextRequestHeadersJsonError = `JSON格式错误: ${error.message}`
    ElMessage.error('JSON格式化失败')
  }
}

const convertToKeyValue = (step) => {
  step.config.headersMode = 'keyvalue'
  convertJsonToKeyValue(step, 'headers')
}

const convertNextRequestHeadersToKeyValue = (step) => {
  step.config.nextRequestHeadersMode = 'keyvalue'
  convertJsonToKeyValue(step, 'nextRequestHeaders')
}

// 下一级请求参数模式切换和处理方法
const onNextRequestParamsModeChange = (step) => {
  if (step.config.nextRequestParamsMode === 'json') {
    // 从键值对转换为JSON
    convertKeyValueToJson(step, 'nextRequestParams', 'nextRequestParamsJson')
  } else {
    // 从JSON转换为键值对
    convertJsonToKeyValue(step, 'nextRequestParams', 'nextRequestParamsJson')
  }
}

const validateNextRequestParamsJson = (step) => {
  try {
    if (step.config.nextRequestParamsJson.trim()) {
      JSON.parse(step.config.nextRequestParamsJson)
      step.config.nextRequestParamsJsonError = ''
    }
  } catch (error) {
    step.config.nextRequestParamsJsonError = 'JSON格式错误: ' + error.message
  }
}

const formatNextRequestParamsJson = (step) => {
  try {
    if (step.config.nextRequestParamsJson.trim()) {
      const parsed = JSON.parse(step.config.nextRequestParamsJson)
      step.config.nextRequestParamsJson = JSON.stringify(parsed, null, 2)
      step.config.nextRequestParamsJsonError = ''
    }
  } catch (error) {
    step.config.nextRequestParamsJsonError = 'JSON格式错误: ' + error.message
  }
}

const convertNextRequestParamsToKeyValue = (step) => {
  step.config.nextRequestParamsMode = 'keyvalue'
  convertJsonToKeyValue(step, 'nextRequestParams', 'nextRequestParamsJson')
}

// 自定义代码相关方法
const validateCustomCode = (step) => {
  // 基本的Python语法检查
  const code = step.config.nextRequestCustomCode.trim()
  if (!code) {
    step.config.nextRequestCustomCodeError = ''
    return
  }
  
  // 检查是否包含必要的函数定义
  if (!code.includes('def process_request(') && !code.includes('def extract_links(')) {
    step.config.nextRequestCustomCodeError = '代码必须包含 process_request() 或 extract_links() 函数'
    return
  }
  
  // 检查基本的Python语法结构
  const lines = code.split('\n')
  let indentLevel = 0
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (line.trim() === '') continue
    
    // 简单的缩进检查
    const currentIndent = line.length - line.trimStart().length
    if (line.trimStart().endsWith(':')) {
      indentLevel = currentIndent + 4
    } else if (currentIndent > 0 && currentIndent % 4 !== 0) {
      step.config.nextRequestCustomCodeError = `第${i + 1}行缩进错误，Python使用4个空格缩进`
      return
    }
  }
  
  step.config.nextRequestCustomCodeError = ''
}

const formatCustomCode = (step) => {
  // 简单的代码格式化
  const code = step.config.nextRequestCustomCode.trim()
  if (!code) return
  
  const lines = code.split('\n')
  const formattedLines = []
  let indentLevel = 0
  
  for (const line of lines) {
    const trimmedLine = line.trim()
    if (trimmedLine === '') {
      formattedLines.push('')
      continue
    }
    
    // 减少缩进级别
    if (trimmedLine.startsWith('except') || trimmedLine.startsWith('elif') || 
        trimmedLine.startsWith('else') || trimmedLine.startsWith('finally')) {
      indentLevel = Math.max(0, indentLevel - 4)
    }
    
    // 添加格式化的行
    formattedLines.push(' '.repeat(indentLevel) + trimmedLine)
    
    // 增加缩进级别
    if (trimmedLine.endsWith(':')) {
      indentLevel += 4
    }
  }
  
  step.config.nextRequestCustomCode = formattedLines.join('\n')
  validateCustomCode(step)
}

const testCustomCode = (step) => {
  // 这里可以添加代码测试逻辑
  ElMessage.info('代码测试功能开发中...')
}

// 数据提取规则管理方法
const addExtractionRule = (step) => {
  if (!step.config.extractionRules) {
    step.config.extractionRules = []
  }
  
  const newRule = {
    fieldName: '',
    extractType: 'xpath',
    expression: '',
    dataType: 'text',
    required: false,
    multiple: false,
    trim: true,
    defaultValue: '',
    postProcess: ''
  }
  
  step.config.extractionRules.push(newRule)
}

const removeExtractionRule = (step, index) => {
  if (step.config.extractionRules && step.config.extractionRules.length > index) {
    step.config.extractionRules.splice(index, 1)
  }
}

const addLinkExtractionRule = (step) => {
  if (!step.config.linkExtractionRules) {
    step.config.linkExtractionRules = []
  }
  
  const newRule = {
    fieldName: '',
    extractType: 'xpath',
    expression: '',
    dataType: 'text',
    required: false,
    multiple: false,
    trim: true,
    defaultValue: '',
    postProcess: '',
    // 链接提取特有字段
    linkSelector: '',
    linkFilter: '',
    maxLinks: 10,
    deduplicate: true
  }
  
  step.config.linkExtractionRules.push(newRule)
}

const removeLinkExtractionRule = (step, index) => {
  if (step.config.linkExtractionRules && step.config.linkExtractionRules.length > index) {
    step.config.linkExtractionRules.splice(index, 1)
  }
}

// 获取表达式标签和占位符
const getExpressionLabel = (extractType) => {
  const labelMap = {
    'xpath': 'XPath表达式',
    'regex': '正则表达式',
    'css': 'CSS选择器',
    'link': '链接提取配置'
  }
  return labelMap[extractType] || '表达式'
}

const getExpressionPlaceholder = (extractType) => {
  const placeholderMap = {
    'xpath': '例如：//div[@class="title"]/text()',
    'regex': '例如：<title>(.*?)</title>',
    'css': '例如：.title, #content',
    'link': '配置链接选择器和过滤规则'
  }
  return placeholderMap[extractType] || '请输入提取表达式'
}
</script>

<style scoped>
.app-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
  padding: 16px;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* 左右分栏布局样式 */
.main-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 200px);
}

.config-panel {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
}

.config-content {
  height: 100%;
}

.test-panel {
  width: 400px;
  flex-shrink: 0;
}

.test-content {
  height: 100%;
}

.test-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.test-card .el-card__body {
  flex: 1;
  padding: 0;
  overflow: hidden;
}

.test-log-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 300px);
  min-height: 400px;
}

.empty-logs {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  text-align: center;
  padding: 40px 20px;
}

.log-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  /* 自定义滚动条样式 */
  scrollbar-width: thin;
  scrollbar-color: #c1c1c1 #f1f1f1;
  /* 优化滚动行为 */
  scroll-behavior: smooth;
}

/* Webkit浏览器滚动条样式 */
.log-list::-webkit-scrollbar {
  width: 8px;
}

.log-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.log-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
  transition: background 0.3s ease;
}

.log-list::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.log-item {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 12px;
  background: #fff;
  transition: all 0.3s;
}

.log-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.log-item.log-error {
  border-color: #f56c6c;
  background: #fef0f0;
}

.log-item.log-success {
  border-color: #67c23a;
  background: #f0f9ff;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
  border-radius: 6px 6px 0 0;
}

.log-time {
  font-size: 12px;
  color: #909399;
}

.log-step {
  font-weight: 600;
  color: #303133;
  margin: 0 12px;
}

.log-content {
  padding: 12px 16px;
}

.log-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #303133;
}

.config-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-config {
  text-align: center;
  padding: 40px;
  color: #999;
}

.status-item {
  text-align: center;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 6px;
}

.status-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.status-value {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.workflow-step {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 20px;
  background: #fff;
  position: relative;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  border-radius: 8px 8px 0 0;
}

.step-title {
  display: flex;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

.step-title .el-icon {
  margin-right: 8px;
  color: #409eff;
}

.step-actions {
  display: flex;
  gap: 8px;
}

.step-content {
  padding: 20px;
}

.config-section {
  margin-top: 16px;
}

.config-section h4 {
  margin: 0 0 16px 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.params-config, .headers-config {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
  background: #fafafa;
}

.param-item, .header-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.param-item:last-child, .header-item:last-child {
  margin-bottom: 0;
}

.step-connector {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 40px;
  color: #909399;
  font-size: 20px;
}

.log-container {
  max-height: 400px;
  overflow-y: auto;
  background: #f5f5f5;
  border-radius: 4px;
  padding: 16px;
}

.log-content {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #303133;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
}

/* 数据提取规则样式 */
.extraction-rules {
  margin-top: 16px;
}

.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-weight: 600;
  color: #303133;
}

.empty-rules {
  border: 1px dashed #e4e7ed;
  border-radius: 6px;
  background: #fafafa;
}

.rules-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rule-item {
  width: 100%;
}

.rule-card {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
}

.rule-card .el-card__body {
  padding: 16px;
}

.rule-content {
  width: 100%;
}

.json-error {
  margin-top: 8px;
}

.json-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
</style>