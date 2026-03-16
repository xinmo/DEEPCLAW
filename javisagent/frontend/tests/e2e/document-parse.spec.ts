import { test, expect } from '@playwright/test';

test.describe('智能解析模块', () => {
  test('应该能够访问文档解析页面', async ({ page }) => {
    await page.goto('/');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 查找并点击文档解析菜单
    const parseMenu = page.locator('text=文档解析').or(page.locator('text=智能解析'));
    await expect(parseMenu.first()).toBeVisible({ timeout: 10000 });
    await parseMenu.first().click();

    // 验证页面标题或关键元素（使用 first() 避免 strict mode 错误）
    await expect(page.locator('text=上传文件').first()).toBeVisible({ timeout: 10000 });

    // 截图
    await page.screenshot({ path: 'test-screenshots/document-parse-page.png', fullPage: true });
  });

  test('应该显示文件上传区域', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 导航到文档解析页面
    const parseMenu = page.locator('text=文档解析').or(page.locator('text=智能解析'));
    await parseMenu.first().click();

    // 查找上传相关元素
    const uploadArea = page.locator('[class*="upload"]').or(page.locator('text=上传')).or(page.locator('input[type="file"]'));
    await expect(uploadArea.first()).toBeVisible({ timeout: 10000 });

    await page.screenshot({ path: 'test-screenshots/document-upload-area.png', fullPage: true });
  });
});
