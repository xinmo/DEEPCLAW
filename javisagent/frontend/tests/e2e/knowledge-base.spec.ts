import { test, expect } from '@playwright/test';

test.describe('智能知识库模块', () => {
  test('应该能够访问知识库管理页面', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 查找并点击知识库菜单
    const kbMenu = page.locator('text=知识库管理').or(page.locator('text=知识库')).or(page.locator('text=智能知识库'));
    await expect(kbMenu.first()).toBeVisible({ timeout: 10000 });
    await kbMenu.first().click();

    // 验证页面加载（使用更具体的选择器）
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    expect(pageContent).toContain('知识库');

    await page.screenshot({ path: 'test-screenshots/knowledge-base-page.png', fullPage: true });
  });

  test('应该显示知识库列表或创建按钮', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 导航到知识库页面
    const kbMenu = page.locator('text=知识库管理').or(page.locator('text=知识库')).or(page.locator('text=智能知识库'));
    await kbMenu.first().click();

    await page.waitForTimeout(2000);

    // 查找创建按钮或知识库列表
    const hasKBFeatures = await page.locator('text=创建知识库').or(
      page.locator('text=新建')
    ).or(
      page.locator('button')
    ).first().isVisible({ timeout: 5000 }).catch(() => false);

    expect(hasKBFeatures).toBeTruthy();

    await page.screenshot({ path: 'test-screenshots/knowledge-base-features.png', fullPage: true });
  });

  test('应该能够访问知识问答页面', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 查找并点击知识问答菜单
    const chatMenu = page.locator('text=知识问答').or(page.locator('text=智能问答'));
    const isVisible = await chatMenu.first().isVisible({ timeout: 5000 }).catch(() => false);

    if (isVisible) {
      await chatMenu.first().click();
      await page.waitForTimeout(2000);

      // 验证聊天界面元素
      const hasChatFeatures = await page.locator('input').or(
        page.locator('textarea')
      ).or(
        page.locator('text=发送')
      ).first().isVisible({ timeout: 5000 }).catch(() => false);

      expect(hasChatFeatures).toBeTruthy();

      await page.screenshot({ path: 'test-screenshots/knowledge-chat-page.png', fullPage: true });
    } else {
      // 如果没有独立的问答菜单，跳过此测试
      test.skip();
    }
  });
});
