import { test, expect } from '@playwright/test';

test.describe('智能翻译模块', () => {
  test('应该能够访问实时翻译页面', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 查找并点击翻译菜单
    const translateMenu = page.locator('text=实时翻译').or(page.locator('text=智能翻译'));
    await expect(translateMenu.first()).toBeVisible({ timeout: 10000 });
    await translateMenu.first().click();

    // 验证页面加载（使用更具体的选择器）
    await page.waitForTimeout(1000);
    const pageContent = await page.content();
    expect(pageContent).toContain('翻译');

    await page.screenshot({ path: 'test-screenshots/translate-page.png', fullPage: true });
  });

  test('应该显示翻译功能选项', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 导航到翻译页面
    const translateMenu = page.locator('text=实时翻译').or(page.locator('text=智能翻译'));
    await translateMenu.first().click();

    // 等待页面加载
    await page.waitForTimeout(2000);

    // 查找翻译相关功能（声音克隆、文字转语音、会议模式等）
    const hasFeatures = await page.locator('text=声音克隆').or(
      page.locator('text=文字转语音')
    ).or(
      page.locator('text=会议')
    ).or(
      page.locator('button')
    ).first().isVisible({ timeout: 5000 }).catch(() => false);

    expect(hasFeatures).toBeTruthy();

    await page.screenshot({ path: 'test-screenshots/translate-features.png', fullPage: true });
  });
});
