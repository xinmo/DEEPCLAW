import { test, expect } from '@playwright/test';

test.describe('NanoClaw 功能测试', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
  });

  test('1. 对话管理 - 创建新会话并发送消息', async ({ page }) => {
    // 使用 data-menu-id 点击菜单项
    await page.click('[data-menu-id*="nanoclaw-chat"]');

    // 等待页面加载
    await expect(page.locator('h2:has-text("系统监控")')).not.toBeVisible();

    // 点击新建会话按钮
    await page.click('button:has-text("新建会话")');
    await page.waitForTimeout(500);

    // 验证会话列表中有新会话
    await expect(page.locator('.ant-list-item').first()).toBeVisible();

    // 输入消息
    const input = page.locator('input[placeholder="输入消息..."]');
    await input.fill('你好，这是一个测试消息');

    // 点击发送按钮
    await page.click('button:has-text("发送")');

    // 验证消息已发送（用户消息应该显示）
    await expect(page.locator('text=你好，这是一个测试消息')).toBeVisible({ timeout: 10000 });

    // 截图
    await page.screenshot({ path: 'test-screenshots/nanoclaw-chat.png', fullPage: true });
  });

  test('2. 模型配置 - 查看和修改 Agent 配置', async ({ page }) => {
    await page.click('[data-menu-id*="nanoclaw-model"]');

    // 等待页面加载
    await expect(page.locator('h2:has-text("模型配置")')).toBeVisible();

    // 验证 Agent 配置 Tab 存在
    await expect(page.locator('text=Agent 配置')).toBeVisible();

    // 验证默认模型选择器存在
    await expect(page.locator('label:has-text("默认模型")')).toBeVisible();

    // 验证 Temperature 滑块存在
    await expect(page.locator('label:has-text("Temperature")')).toBeVisible();

    // 验证最大工具迭代次数输入框存在
    await expect(page.locator('label:has-text("最大工具迭代次数")')).toBeVisible();

    // 切换到 LLM 提供商 Tab
    await page.click('text=LLM 提供商');
    await page.waitForTimeout(300);

    // 验证提供商配置卡片存在
    await expect(page.locator('text=Anthropic (Claude)')).toBeVisible();
    await expect(page.locator('text=OpenAI (GPT)')).toBeVisible();
    await expect(page.locator('text=DeepSeek')).toBeVisible();

    await page.screenshot({ path: 'test-screenshots/nanoclaw-model-config.png', fullPage: true });
  });

  test('3. 技能管理 - 查看技能列表和创建技能', async ({ page }) => {
    await page.click('[data-menu-id*="nanoclaw-skills"]');

    // 等待页面加载
    await expect(page.locator('h2:has-text("技能管理")')).toBeVisible();

    // 验证创建技能按钮存在
    await expect(page.locator('button:has-text("创建技能")')).toBeVisible();

    // 验证表格存在
    await expect(page.locator('.ant-table')).toBeVisible();

    // 点击创建技能按钮
    await page.click('button:has-text("创建技能")');

    // 验证模态框打开
    await expect(page.locator('.ant-modal-title:has-text("创建技能")')).toBeVisible();

    // 验证表单字段
    await expect(page.locator('label:has-text("技能名称")')).toBeVisible();
    await expect(page.locator('label:has-text("描述")')).toBeVisible();
    await expect(page.locator('label:has-text("技能内容")')).toBeVisible();
    await expect(page.locator('label:has-text("Always 加载")')).toBeVisible();

    // 填写表单
    await page.fill('input[placeholder="例如: github"]', 'test-skill');
    await page.fill('input[placeholder="简短描述技能功能"]', '测试技能描述');
    await page.fill('textarea', '---\nname: test-skill\ndescription: Test skill\n---\n\n# Test Skill\n\nThis is a test skill.');

    // 关闭模态框（不保存）
    await page.locator('.ant-modal-footer .ant-btn').first().click();
    await page.waitForTimeout(300);

    await page.screenshot({ path: 'test-screenshots/nanoclaw-skills.png', fullPage: true });
  });

  test('4. 定时任务 - 查看任务列表和创建任务', async ({ page }) => {
    await page.click('[data-menu-id*="nanoclaw-cron"]');

    // 等待页面加载
    await expect(page.locator('h2:has-text("定时任务管理")')).toBeVisible();

    // 验证创建任务按钮存在
    await expect(page.locator('button:has-text("创建任务")')).toBeVisible();

    // 验证表格存在
    await expect(page.locator('.ant-table')).toBeVisible();

    // 点击创建任务按钮
    await page.click('button:has-text("创建任务")');

    // 验证模态框打开
    await expect(page.locator('.ant-modal-title:has-text("创建任务")')).toBeVisible();

    // 验证表单字段
    await expect(page.locator('label:has-text("任务名称")')).toBeVisible();
    await expect(page.locator('label:has-text("消息内容")')).toBeVisible();
    await expect(page.locator('label:has-text("调度类型")')).toBeVisible();

    // 验证调度类型字段存在（默认是间隔执行）
    await expect(page.locator('label:has-text("调度类型")')).toBeVisible();
    await expect(page.locator('label:has-text("间隔时间")')).toBeVisible();

    // 关闭模态框
    await page.locator('.ant-modal-footer .ant-btn').first().click();
    await page.waitForTimeout(300);

    await page.screenshot({ path: 'test-screenshots/nanoclaw-cron.png', fullPage: true });
  });

  test('5. 渠道配置 - 查看渠道配置选项', async ({ page }) => {
    await page.click('[data-menu-id*="nanoclaw-channels"]');

    // 等待页面加载
    await expect(page.locator('h2:has-text("渠道配置")')).toBeVisible();

    // 验证 Tab 存在
    await expect(page.locator('.ant-tabs-tab:has-text("QQ")')).toBeVisible();
    await expect(page.locator('.ant-tabs-tab:has-text("飞书")')).toBeVisible();
    await expect(page.locator('.ant-tabs-tab:has-text("Telegram")')).toBeVisible();
    await expect(page.locator('.ant-tabs-tab:has-text("Discord")')).toBeVisible();

    // 验证 QQ 配置卡片
    await expect(page.locator('text=QQ 机器人')).toBeVisible();
    await expect(page.locator('label:has-text("App ID")')).toBeVisible();
    await expect(page.locator('label:has-text("Secret / Token")')).toBeVisible();
    await expect(page.locator('label:has-text("白名单")')).toBeVisible();

    // 切换到飞书 Tab
    await page.click('.ant-tabs-tab:has-text("飞书")');
    await page.waitForTimeout(300);
    await expect(page.locator('text=飞书机器人')).toBeVisible();

    // 切换到 Telegram Tab
    await page.click('.ant-tabs-tab:has-text("Telegram")');
    await page.waitForTimeout(300);
    await expect(page.locator('text=Telegram Bot')).toBeVisible();

    // 切换到 Discord Tab
    await page.click('.ant-tabs-tab:has-text("Discord")');
    await page.waitForTimeout(300);
    await expect(page.locator('text=Discord Bot')).toBeVisible();

    await page.screenshot({ path: 'test-screenshots/nanoclaw-channels.png', fullPage: true });
  });

  test('6. MCP 服务器 - 查看服务器列表和添加服务器', async ({ page }) => {
    await page.click('[data-menu-id*="nanoclaw-mcp"]');

    // 等待页面加载
    await expect(page.locator('h2:has-text("MCP 服务器管理")')).toBeVisible();

    // 验证添加服务器按钮存在
    await expect(page.locator('button:has-text("添加服务器")')).toBeVisible();

    // 验证表格存在
    await expect(page.locator('.ant-table')).toBeVisible();

    // 点击添加服务器按钮
    await page.click('button:has-text("添加服务器")');

    // 验证模态框打开
    await expect(page.locator('.ant-modal-title:has-text("添加 MCP 服务器")')).toBeVisible();

    // 验证表单字段
    await expect(page.locator('label:has-text("服务器名称")')).toBeVisible();
    await expect(page.locator('label:has-text("类型")')).toBeVisible();

    // 验证 Stdio 类型的字段（默认）
    await expect(page.locator('label:has-text("命令")')).toBeVisible();
    await expect(page.locator('label:has-text("参数")')).toBeVisible();

    // 切换到 HTTP 类型
    await page.locator('.ant-modal .ant-select').click();
    await page.waitForTimeout(200);
    await page.click('.ant-select-dropdown .ant-select-item:has-text("HTTP")');
    await page.waitForTimeout(300);

    // 验证 HTTP 类型的字段
    await expect(page.locator('label:has-text("URL")')).toBeVisible();

    // 关闭模态框
    await page.locator('.ant-modal-footer .ant-btn').first().click();
    await page.waitForTimeout(300);

    await page.screenshot({ path: 'test-screenshots/nanoclaw-mcp.png', fullPage: true });
  });

  test('7. 系统监控 - 查看监控数据', async ({ page }) => {
    await page.click('[data-menu-id*="nanoclaw-monitor"]');

    // 等待页面加载
    await expect(page.locator('h2:has-text("系统监控")')).toBeVisible();

    // 验证统计卡片存在
    await expect(page.locator('.ant-statistic-title:has-text("会话总数")')).toBeVisible();
    await expect(page.locator('.ant-statistic-title:has-text("消息总数")')).toBeVisible();
    await expect(page.locator('.ant-statistic-title:has-text("定时任务")')).toBeVisible();
    await expect(page.locator('.ant-statistic-title:has-text("技能数量")')).toBeVisible();
    await expect(page.locator('.ant-statistic-title:has-text("配置总数")')).toBeVisible();
    await expect(page.locator('.ant-statistic-title:has-text("LLM 提供商")')).toBeVisible();
    await expect(page.locator('.ant-statistic-title:has-text("MCP 服务器")')).toBeVisible();

    // 验证最近活动表格
    await expect(page.locator('text=最近会话')).toBeVisible();
    await expect(page.locator('text=最近消息')).toBeVisible();

    // 等待数据加载
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'test-screenshots/nanoclaw-monitor.png', fullPage: true });
  });

  test('8. 菜单导航 - 验证所有菜单项可点击', async ({ page }) => {
    // 依次点击每个菜单项，验证页面切换
    await page.click('[data-menu-id*="nanoclaw-chat"]');
    await page.waitForTimeout(500);

    await page.click('[data-menu-id*="nanoclaw-model"]');
    await expect(page.locator('h2:has-text("模型配置")')).toBeVisible();

    await page.click('[data-menu-id*="nanoclaw-skills"]');
    await expect(page.locator('h2:has-text("技能管理")')).toBeVisible();

    await page.click('[data-menu-id*="nanoclaw-cron"]');
    await expect(page.locator('h2:has-text("定时任务管理")')).toBeVisible();

    await page.click('[data-menu-id*="nanoclaw-channels"]');
    await expect(page.locator('h2:has-text("渠道配置")')).toBeVisible();

    await page.click('[data-menu-id*="nanoclaw-mcp"]');
    await expect(page.locator('h2:has-text("MCP 服务器管理")')).toBeVisible();

    await page.click('[data-menu-id*="nanoclaw-monitor"]');
    await expect(page.locator('h2:has-text("系统监控")')).toBeVisible();

    await page.screenshot({ path: 'test-screenshots/nanoclaw-navigation.png', fullPage: true });
  });
});
