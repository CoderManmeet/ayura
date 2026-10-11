// Storefront smoke suite (phases G1 and G2).
//
// Runs against the placeholder catalogue from `python manage.py seed_ayura`. The product used
// here is the Face Serum: 30 ml (Rs 449, MRP Rs 499) and 50 ml (Rs 649, MRP Rs 699), 20 of each
// in stock, plus the coupon WELCOME10 (10% off). Shipping is Rs 79, free from Rs 999.
import { test, expect } from '@playwright/test';

const PRODUCT = '/detail/face-serum';

const addToCart = async (page) => {
    const added = page.waitForResponse((response) => response.url().includes('/cart-view/') && response.request().method() === 'POST');
    await page.getByTestId('add-to-cart').click();
    expect((await added).status()).toBeLessThan(300);
    // The page re-reads the product after adding; wait for the button to settle.
    await expect(page.getByTestId('add-to-cart')).toHaveText(/Add to bag/);
};

const fillAddress = async (page) => {
    await page.getByLabel('Full Name').fill('Asha Rao');
    await page.getByLabel('Email').fill('asha@example.com');
    await page.getByLabel('Mobile').fill('9876543210');
    await page.getByLabel('Address', { exact: true }).fill('12 MG Road');
    await page.getByLabel('City').fill('Ludhiana');
    await page.getByLabel('State').fill('Punjab');
    await page.getByLabel('PIN code').fill('141001');
};

test('G2: choosing a size shows that size\'s price and honest stock, and adds that size to the cart', async ({ page }) => {
    await page.goto(PRODUCT);
    await expect(page.getByTestId('product-title')).toHaveText('Face Serum');

    // Default size.
    await expect(page.getByTestId('product-price')).toHaveText('₹449');
    await expect(page.getByTestId('product-mrp')).toHaveText('₹499');
    await expect(page.getByTestId('product-percent-off')).toHaveText('10% off');

    // Pick 50 ml. (Rs 50 off an MRP of Rs 699 is 7.15%, shown rounded down.)
    await page.getByTestId('option-Size').getByRole('button', { name: '50 ml' }).click();
    await expect(page.getByTestId('product-price')).toHaveText('₹649');
    await expect(page.getByTestId('product-mrp')).toHaveText('₹699');
    await expect(page.getByTestId('product-percent-off')).toHaveText('7% off');
    await expect(page.getByTestId('stock-status')).toHaveText('In stock');
    await expect(page.getByTestId('shipping-line')).toContainText('Shipping ₹79. Free on orders of ₹999 or more.');
    await expect(page.locator('main')).toContainText('Inclusive of all taxes');

    await addToCart(page);

    await page.goto('/cart/');
    await expect(page.getByTestId('cart-line')).toHaveCount(1);
    await expect(page.getByTestId('cart-line-variant')).toHaveText('50 ml');
    await expect(page.getByTestId('cart-line-subtotal')).toHaveText('₹649');
});

test('G1: add to cart, apply a coupon, and see correct INR totals in the cart and at checkout', async ({ page }) => {
    await page.goto(PRODUCT);
    await page.getByTestId('option-Size').getByRole('button', { name: '50 ml' }).click();
    await expect(page.getByTestId('product-price')).toHaveText('₹649');
    await addToCart(page);

    await page.goto('/cart/');
    await expect(page.getByTestId('summary-subtotal')).toHaveText('₹649');
    await expect(page.getByTestId('summary-shipping')).toHaveText('₹79');
    await expect(page.getByTestId('summary-total')).toHaveText('₹728');
    await expect(page.getByTestId('free-shipping-line')).toHaveText('Add ₹350 more for free shipping.');

    // An unknown code is refused with a reason and changes nothing.
    await page.getByLabel('Coupon code').fill('NOPE');
    await page.getByRole('button', { name: 'Apply' }).click();
    await expect(page.getByTestId('coupon-message')).toHaveText('This coupon code is not valid.');
    await expect(page.getByTestId('summary-total')).toHaveText('₹728');

    // 10% off the Rs 649 subtotal = Rs 64.90; shipping still applies.
    await page.getByLabel('Coupon code').fill('welcome10');
    await page.getByRole('button', { name: 'Apply' }).click();
    await expect(page.getByTestId('summary-discount')).toHaveText('-₹64.90');
    await expect(page.getByTestId('summary-shipping')).toHaveText('₹79');
    await expect(page.getByTestId('summary-total')).toHaveText('₹663.10');
    await expect(page.getByTestId('cart-summary')).toContainText('Inclusive of all taxes');
    await expect(page.getByTestId('cart-summary')).not.toContainText('Tax');
    await expect(page.getByTestId('cart-summary')).not.toContainText('Service');

    await fillAddress(page);
    await page.getByRole('button', { name: 'Go to checkout' }).click();

    await expect(page).toHaveURL(/\/checkout\//);
    const summary = page.getByTestId('checkout-summary');
    await expect(summary.getByTestId('summary-subtotal')).toHaveText('₹649');
    await expect(summary.getByTestId('summary-discount')).toHaveText('-₹64.90');
    await expect(summary.getByTestId('summary-shipping')).toHaveText('₹79');
    await expect(summary.getByTestId('summary-total')).toHaveText('₹663.10');
    await expect(summary).toContainText('Discount (WELCOME10)');
    await expect(summary).toContainText('Inclusive of all taxes');
    await expect(page.getByLabel('UPI / Card / Netbanking')).toBeChecked();
    await expect(page.getByTestId('pay-online')).toHaveText('Pay ₹663.10');

    // No dollars, no PayPal, no tax or service-fee rows anywhere on the page.
    const body = page.locator('body');
    await expect(body).not.toContainText('$');
    await expect(body).not.toContainText('USD');
    await expect(body).not.toContainText(/paypal/i);
    await expect(summary).not.toContainText('Tax');
    await expect(summary).not.toContainText('Service');

    // The policies are linked from checkout.
    await expect(page.getByTestId('checkout-policies').getByRole('link')).toHaveCount(5);
});

test('G1: an order of Rs 999 or more ships free', async ({ page }) => {
    await page.goto(PRODUCT);
    // Two of the 50 ml (Rs 649 each) = Rs 1,298.
    await page.getByTestId('option-Size').getByRole('button', { name: '50 ml' }).click();
    await page.getByLabel('Quantity').fill('2');
    await addToCart(page);

    await page.goto('/cart/');
    await expect(page.getByTestId('summary-subtotal')).toHaveText('₹1,298');
    await expect(page.getByTestId('summary-shipping')).toHaveText('Free');
    await expect(page.getByTestId('summary-total')).toHaveText('₹1,298');
    await expect(page.locator('body')).not.toContainText('$');
});

test('G2: every policy page and the contact page render and are linked from the footer', async ({ page }) => {
    await page.goto('/');
    const footer = page.getByTestId('footer-policies');

    const pages = [
        ['Shipping Policy', 'policy-shipping'],
        ['Returns and Refunds', 'policy-returns'],
        ['Privacy Policy', 'policy-privacy'],
        ['Terms and Conditions', 'policy-terms'],
    ];
    for (const [title, testId] of pages) {
        await footer.getByRole('link', { name: title }).click();
        await expect(page.getByTestId(testId).getByRole('heading', { level: 1 })).toHaveText(title);
        // The copy is placeholder text and says so.
        await expect(page.getByTestId('placeholder-notice')).toBeVisible();
    }

    // The shipping page states the live charge and threshold.
    await page.goto('/policy/shipping');
    await expect(page.getByTestId('policy-shipping')).toContainText('Shipping is ₹79 per order. Orders of ₹999 or more');

    await page.getByRole('contentinfo').getByRole('link', { name: 'Contact us' }).click();
    await expect(page.getByTestId('policy-contact').getByRole('heading', { level: 1 })).toHaveText('Contact us');
    await expect(page.getByTestId('contact-email')).toHaveAttribute('href', /^mailto:/);
    await expect(page.getByTestId('contact-whatsapp')).toHaveAttribute('href', /^https:\/\/wa\.me\/\d+$/);
    await expect(page.getByTestId('footer-whatsapp')).toHaveAttribute('href', /^https:\/\/wa\.me\/\d+$/);
});
