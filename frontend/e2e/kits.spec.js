// Kits suite (Ayura phase E): one item on the shelf made out of other sizes.
//
// The owner adds a kit size to the Face Serum, says what goes inside it on the Kits screen, and
// sees how many the scarcest part allows. A customer buys one: the product page says what is in
// the box before they commit, the bag holds one line at the kit's price, and the components'
// stock moves, not the kit's. Cancelling the order gives every component back.
//
// Stock counts are read before and after each step rather than hard-coded: the other specs in
// this suite have already bought and cancelled things in the same database.
//
// Accounts come from `seed_e2e`; the catalogue from `seed_ayura`.
import { test, expect } from '@playwright/test';

const OWNER = 'owner@e2e.test';
const CUSTOMER = 'customer@e2e.test';
const PASSWORD = 'E2e-only-Passw0rd!';

const KIT = 'Face routine kit';

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

// The owner's Kits screen, as numbers: what each part allows and what the kit can sell.
const kitFigures = async (page) => {
    await page.goto('/admin-area/owner/kits/');
    const card = page.locator('[data-testid="kit-card"]').filter({ hasText: KIT });
    await expect(card).toHaveCount(1);
    const parts = {};
    for (const row of await card.getByTestId('kit-part').all()) {
        parts[await row.getAttribute('data-sku')] = {
            available: Number(await row.getByTestId('kit-part-available').innerText()),
            possible: Number(await row.getByTestId('kit-part-possible').innerText()),
        };
    }
    return { card, available: Number(await card.getByTestId('kit-available').innerText()), parts };
};

const addPart = async (page, card, label, qty) => {
    const select = card.getByTestId('kit-part-select');
    const value = await select.locator('option', { hasText: label }).first().getAttribute('value');
    await select.selectOption(value);
    await card.getByTestId('kit-part-qty').fill(String(qty));
    await card.getByTestId('kit-part-add').click();
};

test.describe.serial('phase E kits', () => {
    test('the owner makes a kit out of two other sizes and sees what limits it', async ({ page }) => {
        test.setTimeout(150_000);
        await signIn(page, OWNER);

        // --- a kit size on the Face Serum, at the owner's own price
        await page.goto('/admin-area/products/');
        await page.getByRole('row', { name: /Face Serum/ }).getByTestId('sizes-stock-link').click();
        await expect(page.getByTestId('owner-product-title')).toContainText('Face Serum');

        await page.getByTestId('new-size-label').fill(KIT);
        await page.getByTestId('new-size-net_quantity').fill('80');
        await page.getByTestId('new-size-unit').selectOption('ml');
        await page.getByTestId('new-size-is-kit').check();
        // A size is either a kit or a sample, never both: ticking one locks the other out.
        await expect(page.getByTestId('new-size-is-sample')).toBeDisabled();
        await page.getByTestId('new-size-price').fill('699');
        await page.getByTestId('new-size-mrp').fill('899');
        await page.getByTestId('new-size-weight_grams').fill('400');
        await page.getByTestId('add-size').click();

        const kitRow = page.locator(`[data-testid="size-row"][data-size="${KIT}"]`);
        await expect(kitRow.getByTestId('size-kit')).toBeVisible();
        await expect(kitRow.getByTestId('size-available')).toContainText('0');   // nothing in it yet

        // A kit keeps no stock of its own, so the stock panel offers no batches for it.
        const kitStock = page.locator(`[data-testid="stock-size"][data-size="${KIT}"]`);
        await expect(kitStock.getByTestId('stock-kit-note')).toBeVisible();
        await expect(kitStock.locator('[data-testid="add-stock"]')).toHaveCount(0);

        // --- say what goes in it
        let figures = await kitFigures(page);
        await expect(figures.card.getByTestId('kit-empty')).toBeVisible();
        expect(figures.available).toBe(0);

        await addPart(page, figures.card, 'Face Serum 30 ml', 1);
        await expect(figures.card.getByTestId('kit-part')).toHaveCount(1);
        await addPart(page, figures.card, 'Face Scrub 50 g', 2);
        await expect(figures.card.getByTestId('kit-part')).toHaveCount(2);

        figures = await kitFigures(page);
        const serum = figures.parts['SEED-FACE-SERUM-30ML'];
        const scrub = figures.parts['SEED-FACE-SCRUB-50G'];
        // Two scrubs per kit, so the scrub allows half as many as it has.
        expect(scrub.possible).toBe(Math.floor(scrub.available / 2));
        expect(serum.possible).toBe(serum.available);
        expect(figures.available).toBe(Math.min(serum.possible, scrub.possible));
        await expect(figures.card.getByTestId('kit-bottleneck')).toBeVisible();

        // Changing how many go in moves what the kit can sell, with no stock anywhere touched.
        const scrubRow = figures.card.getByTestId('kit-part').filter({ hasText: 'Face Scrub' });
        await scrubRow.getByTestId('kit-part-row-qty').fill('4');
        await scrubRow.getByTestId('kit-part-save').click();
        await expect(figures.card.getByTestId('kit-available'))
            .toHaveText(String(Math.min(serum.possible, Math.floor(scrub.available / 4))));

        // Put it back to two and carry on.
        await scrubRow.getByTestId('kit-part-row-qty').fill('2');
        await scrubRow.getByTestId('kit-part-save').click();
        await expect(figures.card.getByTestId('kit-available')).toHaveText(String(figures.available));
        await signOut(page);
    });

    test('a customer sees what is in the kit, buys one, and the components move', async ({ page }) => {
        test.setTimeout(180_000);

        // What the parts have before the sale.
        await signIn(page, OWNER);
        const before = await kitFigures(page);
        await signOut(page);

        // --- the product page: what is inside, before anything is added to the bag
        await page.goto('/detail/face-serum');
        await page.getByTestId('option-Size').getByRole('button', { name: KIT }).click();
        const inside = page.getByTestId('kit-contents');
        await expect(inside).toBeVisible();
        await expect(inside).toContainText('Face Serum 30 ml');
        await expect(inside).toContainText('2 × Face Scrub 50 g');
        // The parts are named, never priced: the kit has one price of its own.
        await expect(inside).not.toContainText('₹');
        await expect(page.getByTestId('product-price')).toHaveText('₹699');
        await expect(page.getByTestId('stock-status')).not.toHaveText('Sold out');

        // --- buy one
        await signIn(page, CUSTOMER);
        await page.goto('/detail/face-serum');
        await page.getByTestId('option-Size').getByRole('button', { name: KIT }).click();
        const added = page.waitForResponse((r) => r.url().includes('/cart-view/') && r.request().method() === 'POST');
        await page.getByTestId('add-to-cart').click();
        expect((await added).status()).toBeLessThan(300);

        await page.goto('/cart/');
        await expect(page.locator('body')).toContainText(KIT);
        await page.getByLabel('Full Name').fill('Asha Rao');
        await page.getByLabel('Email').fill(CUSTOMER);
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
        const oid = page.url().split('/order/')[1].replace(/\//g, '');
        await signOut(page);

        // --- one kit sold: one serum and two scrubs are held, and the kit's own stock is still nil
        await signIn(page, OWNER);
        const after = await kitFigures(page);
        expect(after.parts['SEED-FACE-SERUM-30ML'].available).toBe(before.parts['SEED-FACE-SERUM-30ML'].available - 1);
        expect(after.parts['SEED-FACE-SCRUB-50G'].available).toBe(before.parts['SEED-FACE-SCRUB-50G'].available - 2);
        expect(after.available).toBe(before.available - 1);

        // --- cancelling gives every component back
        await page.goto(`/admin-area/owner/orders/${oid}/`);
        await page.getByRole('button', { name: 'Cancel order' }).click();
        await page.getByRole('button', { name: 'Yes' }).click();
        await expect(page.getByTestId('owner-order-status')).toHaveText('Cancelled');

        const restored = await kitFigures(page);
        expect(restored.parts['SEED-FACE-SERUM-30ML'].available).toBe(before.parts['SEED-FACE-SERUM-30ML'].available);
        expect(restored.parts['SEED-FACE-SCRUB-50G'].available).toBe(before.parts['SEED-FACE-SCRUB-50G'].available);
        expect(restored.available).toBe(before.available);
        await signOut(page);
    });

    test('a kit with a part that has none left is sold out, and says so in the shop', async ({ page }) => {
        test.setTimeout(180_000);
        await signIn(page, OWNER);

        // A third part that has never been made: the Lip Balm's new travel size, with no stock.
        // Nothing is written off anywhere, so the rest of the catalogue is left as it was.
        await page.goto('/admin-area/products/');
        await page.getByRole('row', { name: /Lip Balm/ }).getByTestId('sizes-stock-link').click();
        await page.getByTestId('new-size-label').fill('4 g travel');
        await page.getByTestId('new-size-net_quantity').fill('4');
        await page.getByTestId('new-size-unit').selectOption('g');
        await page.getByTestId('new-size-price').fill('99');
        await page.getByTestId('new-size-weight_grams').fill('30');
        await page.getByTestId('add-size').click();
        const travel = page.locator('[data-testid="size-row"][data-size="4 g travel"]');
        await expect(travel.getByTestId('size-available')).toContainText('0');

        let figures = await kitFigures(page);
        expect(figures.available).toBeGreaterThan(0);
        await addPart(page, figures.card, 'Lip Balm 4 g travel', 1);
        await expect(figures.card.getByTestId('kit-part')).toHaveCount(3);
        await expect(figures.card.getByTestId('kit-available')).toHaveText('0');
        await signOut(page);

        // The shop says "Sold out" and the button cannot be used.
        await page.goto('/detail/face-serum');
        await page.getByTestId('option-Size').getByRole('button', { name: KIT }).click();
        await expect(page.getByTestId('stock-status')).toHaveText('Sold out');
        await expect(page.getByTestId('add-to-cart')).toBeDisabled();
        await expect(page.getByTestId('add-to-cart')).toHaveText('Sold out');
        // What is in the box is still shown: the shopper can see why it is not available.
        await expect(page.getByTestId('kit-contents')).toContainText('Lip Balm 4 g travel');

        // Taking the empty part out makes the kit sellable again, with no stock anywhere touched.
        await signIn(page, OWNER);
        figures = await kitFigures(page);
        await figures.card.getByTestId('kit-part').filter({ hasText: 'Lip Balm' })
            .getByTestId('kit-part-remove').click();
        await expect(figures.card.getByTestId('kit-part')).toHaveCount(2);
        await expect(figures.card.getByTestId('kit-available')).not.toHaveText('0');
        await signOut(page);
    });
});
