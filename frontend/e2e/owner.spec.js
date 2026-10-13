// Owner dispatch suite (Ayura phase D): the checks before a parcel is sealed.
//
// The owner creates a sample size, gives it stock, puts it in a customer's parcel, records a
// missing use-by date from the order, sends the order, and sees the batch in the recall lookup
// and the sample in the conversion report. Throughout, the customer is never told about the
// sample (ROADMAP Y19).
//
// Accounts come from `seed_e2e`; the catalogue from `seed_ayura`.
import { test, expect } from '@playwright/test';

const OWNER = 'owner@e2e.test';
const CUSTOMER = 'customer@e2e.test';
const PASSWORD = 'E2e-only-Passw0rd!';

const signIn = async (page, email) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password').fill(PASSWORD);
    const token = page.waitForResponse((r) => r.url().includes('/user/token/') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Sign In' }).click();
    expect((await token).status()).toBe(200);
    await expect.poll(async () => (await page.context().cookies()).some((c) => c.name === 'access_token')).toBe(true);
};

const signOut = async (page) => {
    await page.goto('/logout');
    await expect.poll(async () => (await page.context().cookies()).some((c) => c.name === 'access_token')).toBe(false);
};

const addProduct = async (page, slug, size) => {
    await page.goto(`/detail/${slug}`);
    await page.getByTestId('option-Size').getByRole('button', { name: size }).click();
    const added = page.waitForResponse((r) => r.url().includes('/cart-view/') && r.request().method() === 'POST');
    await page.getByTestId('add-to-cart').click();
    expect((await added).status()).toBeLessThan(300);
    await expect(page.getByTestId('add-to-cart')).toHaveText(/Add to bag/);
};

const checkoutCod = async (page, email) => {
    await page.goto('/cart/');
    await page.getByLabel('Full Name').fill('Asha Rao');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Mobile').fill('9876543210');
    await page.getByLabel('Address', { exact: true }).fill('12 MG Road');
    await page.getByLabel('City').fill('Ludhiana');
    await page.getByLabel('State').fill('Punjab');
    await page.getByLabel('PIN code').fill('141001');
    await page.getByRole('button', { name: 'Go to checkout' }).click();
    await expect(page.getByTestId('payment-methods')).toBeVisible();
    await page.getByLabel('Cash on delivery').check();
    await page.getByTestId('place-cod').click();
    await expect(page).toHaveURL(/\/order\//);
    return page.url().split('/order/')[1].replace(/\//g, '');
};

const isoDay = (days) => new Date(Date.now() + days * 86400000).toISOString().slice(0, 10);

test.describe.serial('phase D dispatch', () => {
    test('the owner creates a sample, puts it in a parcel, and the customer is never told', async ({ page }) => {
        test.setTimeout(150_000);

        // --- the owner adds a sample size to the Face Scrub and gives it stock
        await signIn(page, OWNER);
        await page.goto('/admin-area/products/');
        await page.getByRole('row', { name: /Face Scrub/ }).getByTestId('sizes-stock-link').click();
        await expect(page.getByTestId('owner-product-title')).toContainText('Face Scrub');

        await page.getByTestId('new-size-label').fill('5 g sample');
        await page.getByTestId('new-size-net_quantity').fill('5');
        await page.getByTestId('new-size-unit').selectOption('g');
        await page.getByTestId('new-size-is-sample').check();
        await expect(page.getByTestId('new-size-price')).toHaveValue('0');   // a gift costs nothing
        await page.getByTestId('new-size-weight_grams').fill('20');
        await page.getByTestId('add-size').click();
        const sampleRow = page.locator('[data-testid="size-row"][data-size="5 g sample"]');
        await expect(sampleRow.getByTestId('size-sample')).toBeVisible();

        const stockForm = page.locator('[data-testid="stock-form"][data-size="5 g sample"]');
        await stockForm.getByTestId('stock-quantity').fill('6');
        await stockForm.getByTestId('stock-use-by').fill(isoDay(200));
        await stockForm.getByTestId('add-stock').click();
        await expect(sampleRow.getByTestId('size-available')).toContainText('6');

        // The sample is not in the shop and not in the size picker.
        await page.goto('/detail/face-scrub');
        await expect(page.getByTestId('option-Size')).not.toContainText('5 g sample');
        await signOut(page);

        // --- a customer orders the Face Scrub
        await signIn(page, CUSTOMER);
        await addProduct(page, 'face-scrub', '50 g');
        const oid = await checkoutCod(page, CUSTOMER);
        await signOut(page);

        // --- the owner packs it: batch shown, sample added, missing date recorded
        await signIn(page, OWNER);
        await page.goto(`/admin-area/owner/orders/${oid}/`);
        await expect(page.getByTestId('packing-panel')).toBeVisible();
        await expect(page.getByTestId('packing-batch')).toHaveCount(1);

        await page.getByTestId('samples-undecided').waitFor();
        // The option's value is the variant id, which the test does not know: find it by its text.
        const sampleOption = await page.getByTestId('sample-select').locator('option', { hasText: '5 g sample' })
            .getAttribute('value');
        await page.getByTestId('sample-select').selectOption(sampleOption);
        await page.getByTestId('sample-qty').fill('2');
        await page.getByTestId('sample-add').click();
        await expect(page.getByTestId('sample-item')).toHaveCount(1);
        await expect(page.getByTestId('samples-list')).toContainText('2 × Face Scrub 5 g sample');

        // More than there are is refused, with the reason, and nothing changes.
        await page.getByTestId('sample-select').selectOption(sampleOption);
        await page.getByTestId('sample-add').click();
        await expect(page.getByTestId('samples-error')).toContainText('already on this order');
        await expect(page.getByTestId('sample-item')).toHaveCount(1);

        // The seeded batch has a use-by date; set a new one from here and see it stick.
        await page.getByTestId('packing-use-by').first().fill(isoDay(300));
        await page.getByRole('button', { name: 'Save' }).first().click();
        await expect(page.getByTestId('packing-use-by').first()).toHaveValue(isoDay(300));

        // Send it.
        await page.getByRole('button', { name: 'Confirm COD' }).click();
        await page.getByRole('button', { name: 'Yes' }).click();
        await page.getByRole('button', { name: 'Mark shipped' }).click();
        await expect(page.getByTestId('owner-delivery-status').first()).toHaveText('Shipped');
        await signOut(page);

        // --- the customer's own pages never mention the sample (ROADMAP Y19)
        await signIn(page, CUSTOMER);
        await page.goto('/customer/orders/');
        await expect(page.locator('body')).not.toContainText(/sample/i);
        await page.goto(`/customer/order/detail/${oid}/`);
        await expect(page.getByTestId('order-detail-page')).toBeVisible();
        await expect(page.locator('body')).not.toContainText(/sample/i);
        await signOut(page);
    });

    test('stock and expiry: undated stock is listed, expired stock is written off, batches are traceable', async ({ page }) => {
        test.setTimeout(120_000);
        await signIn(page, OWNER);

        // The seed gives every batch a use-by date, so add one without a date to see it listed.
        await page.goto('/admin-area/products/');
        await page.getByRole('row', { name: /Lip Balm/ }).getByTestId('sizes-stock-link').click();
        const lipStock = page.locator('[data-testid="stock-form"]').first();
        await lipStock.getByTestId('stock-quantity').fill('4');
        await lipStock.getByTestId('add-stock').click();
        await expect(page.locator('[data-testid="stock-size"]').first()).toContainText('No use-by date recorded yet');

        await page.goto('/admin-area/owner/expiry/');
        await expect(page.getByTestId('owner-expiry')).toBeVisible();
        // Other specs leave undated stock of their own behind, so work with this batch only.
        const row = page.getByTestId('undated-row').filter({ hasText: 'Lip Balm' });
        await expect(row).toHaveCount(1);
        const undatedCode = await row.getAttribute('data-batch');
        await expect(row.locator('td').nth(3)).toHaveText('4');     // on hand

        // Write off two of those four: a ledger movement, not an edit.
        await row.getByTestId('write-off-open').click();
        await page.getByTestId('write-off-quantity').fill('2');
        await page.getByTestId('write-off-reason').fill('spilled while filling');
        await page.getByTestId('write-off-confirm').click();
        await expect(page.getByTestId('undated-row').filter({ hasText: 'Lip Balm' }).locator('td').nth(3)).toHaveText('2');

        // The recall lookup finds that batch; nothing has been ordered from it.
        await page.getByTestId('lookup-code').fill(undatedCode);
        await page.getByTestId('lookup-go').click();
        await expect(page.getByTestId('lookup-empty')).toBeVisible();

        await page.getByTestId('lookup-code').fill('NOPE-NOT-A-BATCH');
        await page.getByTestId('lookup-go').click();
        await expect(page.getByTestId('lookup-none')).toBeVisible();
    });

    test('the samples report shows what went out and whether it converted', async ({ page }) => {
        await signIn(page, OWNER);
        await page.goto('/admin-area/owner/samples/');
        await expect(page.getByTestId('owner-samples')).toBeVisible();
        const row = page.getByTestId('sample-row');
        await expect(row).toHaveCount(1);
        await expect(row.getByTestId('sample-given')).toHaveText('1');
        // The customer has not come back for the Face Scrub yet.
        await expect(row.getByTestId('sample-converted')).toHaveText('0');
        await expect(row.getByTestId('sample-percent')).toHaveText('0%');
    });
});
