// Catalogue smoke suite (Ayura phase B): the owner adds a product with sizes, net quantities,
// stock batches, a category and care information; a shopper finds it by category and sees what
// the owner entered.
//
// Accounts come from `python manage.py seed_e2e`; categories (Skincare > Face, Lips; Haircare;
// Bodycare) and the Face Serum from `seed_ayura`. The photo uploaded here goes to
// backend/e2e-media/ (DJANGO_MEDIA_ROOT in playwright.config.js), never to backend/media/.
import { test, expect } from '@playwright/test';

const OWNER = 'owner@e2e.test';
const PASSWORD = 'E2e-only-Passw0rd!';
const TITLE = 'Rose Face Mist';

// A 1x1 PNG, enough for the photo field.
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');

const signIn = async (page, email) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password').fill(PASSWORD);
    const token = page.waitForResponse((r) => r.url().includes('/user/token/') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Sign In' }).click();
    expect((await token).status()).toBe(200);
    await expect.poll(async () => (await page.context().cookies()).some((c) => c.name === 'access_token')).toBe(true);
};

// A date `days` from today as YYYY-MM-DD, for the date inputs.
const isoDay = (days) => {
    const day = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
    return day.toISOString().slice(0, 10);
};

const addSize = async (page, { label, quantity, unit, price, mrp, weight }) => {
    await page.getByTestId('new-size-label').fill(label);
    await page.getByTestId('new-size-net_quantity').fill(quantity);
    await page.getByTestId('new-size-unit').selectOption(unit);
    await page.getByTestId('new-size-price').fill(price);
    await page.getByTestId('new-size-mrp').fill(mrp);
    await page.getByTestId('new-size-weight_grams').fill(weight);
    const saved = page.waitForResponse((r) => r.url().includes('/variants/') && r.request().method() === 'POST');
    await page.getByTestId('add-size').click();
    return (await saved).status();
};

test.describe.serial('phase B catalogue', () => {
    test('the owner creates a product, then sets its sizes, stock, category and care information', async ({ page }) => {
        test.setTimeout(120_000);
        await signIn(page, OWNER);

        // Create the product in the existing form; it then opens the sizes-and-stock screen.
        await page.goto('/admin-area/product/new/');
        await page.locator('input[name="image"]').setInputFiles({ name: 'mist.png', mimeType: 'image/png', buffer: PNG });
        await page.locator('input[name="title"]').fill(TITLE);
        await page.locator('textarea[name="description"]').fill('A light mist for the face.');
        await page.locator('select[name="category"]').selectOption({ label: 'Face' });
        await page.locator('input[name="price"]').fill('349');
        await page.locator('input[name="old_price"]').fill('399');
        await page.locator('input[name="shipping_amount"]').fill('0');
        await page.locator('input[name="stock_qty"]').fill('0');
        await page.getByRole('button', { name: /Create Product/ }).click();
        await page.getByRole('button', { name: 'OK' }).click();
        await expect(page).toHaveURL(/\/admin-area\/owner\/products\/[^/]+\/$/);
        await expect(page.getByTestId('owner-product-title')).toContainText(TITLE);

        // A benefit line that reads as a medical claim is flagged while typing; saving still works.
        await page.getByTestId('benefit-line').fill('Cures dry skin overnight');
        await expect(page.getByTestId('claim-warnings')).toContainText('cures');
        await page.getByTestId('benefit-line').fill('A light mist for a fresh feel');
        await expect(page.getByTestId('claim-warnings')).toHaveCount(0);
        await page.getByTestId('category-select').selectOption({ label: 'Skincare › Face' });
        await page.getByLabel('How to use').fill('Mist over the face from arm\'s length.');
        await page.getByLabel('Cautions').fill('For external use only. Keep away from eyes.');
        await page.getByTestId('save-details').click();
        await expect(page.getByTestId('owner-notice').first()).toHaveText('Details saved.');

        // The first size takes over the placeholder "Default" size; the second is added beside it.
        expect(await addSize(page, { label: '30 ml', quantity: '30', unit: 'ml', price: '349', mrp: '399', weight: '90' })).toBe(201);
        await expect(page.getByTestId('size-row')).toHaveCount(1);
        await expect(page.locator('[data-testid="size-row"][data-size="30 ml"]').getByTestId('size-net-quantity')).toHaveText('30 ml');
        expect(await addSize(page, { label: '100 ml', quantity: '100', unit: 'ml', price: '799', mrp: '899', weight: '180' })).toBe(201);
        await expect(page.getByTestId('size-row')).toHaveCount(2);

        // A price above the MRP is refused, with the reason.
        expect(await addSize(page, { label: '200 ml', quantity: '200', unit: 'ml', price: '999', mrp: '899', weight: '300' })).toBe(400);
        await expect(page.getByTestId('owner-error')).toContainText('cannot be higher than the MRP');
        await expect(page.getByTestId('size-row')).toHaveCount(2);

        // Stock arrives as batches: one with a use-by date, one without (allowed, and shown).
        const small = page.locator('[data-testid="stock-form"][data-size="30 ml"]');
        await small.getByTestId('stock-quantity').fill('12');
        await small.getByTestId('stock-use-by').fill(isoDay(300));
        await small.getByTestId('add-stock').click();
        await expect(page.locator('[data-testid="size-row"][data-size="30 ml"]').getByTestId('size-available')).toContainText('12');

        const large = page.locator('[data-testid="stock-form"][data-size="100 ml"]');
        await large.getByTestId('stock-quantity').fill('5');
        await large.getByTestId('add-stock').click();
        const largeStock = page.locator('[data-testid="stock-size"][data-size="100 ml"]');
        await expect(largeStock.getByTestId('batch-row')).toHaveCount(1);
        await expect(largeStock).toContainText('No use-by date recorded yet');

        // The product list links straight to this screen.
        await page.goto('/admin-area/products/');
        await page.getByRole('row', { name: new RegExp(TITLE) }).getByTestId('sizes-stock-link').click();
        await expect(page.getByTestId('owner-product-title')).toContainText(TITLE);

        // Categories screen lists the tree, and a third level can be added (Skincare › Face › Mists).
        await page.goto('/admin-area/owner/categories/');
        await expect(page.locator('[data-testid="category-row"][data-slug="face"]')).toContainText('Face');
        await page.getByLabel('Name').fill('Mists');
        await page.getByLabel('Inside').selectOption({ label: '— Face' });
        await page.getByRole('button', { name: 'Add category' }).click();
        await expect(page.locator('[data-testid="category-row"][data-slug="mists"]')).toContainText('Mists');
    });

    test('a shopper filters by category and sees the sizes, net quantity and care information', async ({ page }) => {
        await page.goto('/shop');
        const filter = page.getByTestId('category-filter');
        await filter.getByRole('button', { name: 'Skincare' }).click();
        await expect(page).toHaveURL(/category=skincare/);
        // Skincare includes everything inside it: the Face products and the Lip Balm.
        const grid = page.getByTestId('shop-products');
        await expect(grid.getByRole('heading', { name: TITLE })).toBeVisible();
        await expect(grid.getByRole('heading', { name: 'Lip Balm' })).toBeVisible();
        await expect(grid.getByRole('heading', { name: 'Hair Oil' })).toHaveCount(0);

        await page.getByTestId('subcategory-filter').getByRole('button', { name: 'Face' }).click();
        await expect(page).toHaveURL(/category=face/);
        await expect(grid.getByRole('heading', { name: TITLE })).toBeVisible();
        await expect(grid.getByRole('heading', { name: 'Lip Balm' })).toHaveCount(0);

        // A third level gets its own row of chips. Mists has no products yet.
        await expect(page.getByTestId('subcategory-filter')).toHaveCount(2);
        await page.getByTestId('subcategory-filter').nth(1).getByRole('button', { name: 'Mists' }).click();
        await expect(page).toHaveURL(/category=mists/);
        await expect(page.getByText('No products found.')).toBeVisible();
        await page.getByRole('button', { name: 'All face' }).click();
        await expect(grid.getByRole('heading', { name: TITLE })).toBeVisible();

        // The owner's benefit line shows on the tile when the mouse is over it.
        const card = page.getByTestId('product-card').filter({ hasText: TITLE });
        await card.hover();
        await expect(card.getByTestId('product-benefit-overlay')).toHaveText('A light mist for a fresh feel');
        await expect(card.getByTestId('product-benefit-overlay')).toHaveCSS('opacity', '1');

        await card.getByRole('link', { name: TITLE }).last().click();
        await expect(page.getByTestId('product-title')).toHaveText(TITLE);
        await expect(page.getByTestId('breadcrumb')).toContainText('Skincare');
        await expect(page.getByTestId('breadcrumb')).toContainText('Face');
        await expect(page.getByTestId('product-net-quantity')).toHaveText('Net quantity 30 ml');
        await page.getByTestId('option-Size').getByRole('button', { name: '100 ml' }).click();
        await expect(page.getByTestId('product-net-quantity')).toHaveText('Net quantity 100 ml');
        await expect(page.getByTestId('product-price')).toHaveText('₹799');
        await expect(page.getByTestId('product-how-to-use')).toContainText('Mist over the face');
        await expect(page.getByTestId('product-cautions')).toContainText('For external use only');
        await expect(page.getByTestId('product-information')).toContainText('₹899 (inclusive of all taxes)');
        // Nothing the owner has not typed is shown: no ingredients were entered for this product.
        await expect(page.getByTestId('product-ingredients')).toHaveCount(0);
    });
});

test.describe('phase B catalogue on a phone', () => {
    test.use({ viewport: { width: 390, height: 844 } });

    test('the benefit line is shown under the product name, with no hover needed', async ({ page }) => {
        await page.goto('/shop?category=face');
        const card = page.getByTestId('product-card').filter({ hasText: 'Face Serum' });
        await expect(card.getByTestId('product-benefit')).toBeVisible();
        await expect(card.getByTestId('product-benefit')).toHaveText('A light serum for everyday use');
        await expect(card.getByTestId('product-benefit-overlay')).toBeHidden();
    });
});
