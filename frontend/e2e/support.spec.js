// Support suite (Ayura phase F): a customer reports a problem, the owner answers.
//
// Three journeys, each one an acceptance line from the roadmap:
//
//   1. A signed-in customer reports a damaged order with a photo; the owner answers from the
//      admin area; the customer sees the reply and writes back on the same thread.
//   2. A guest reports a problem with no account at all, is given a signed link, and that link
//      opens their own conversation and nothing else.
//   3. The grievance-officer block is absent until the owner fills it in, and appears with her
//      own words once she has (ROADMAP L4).
//
// Accounts come from `seed_e2e`; the catalogue from `seed_ayura`.
import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

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

// A real 8x8 PNG, written to a temp file so the file chooser has something genuine to upload.
// The server opens the bytes and verifies them, so a corrupt or disguised file is refused —
// which is the point of the checks below. Generated with Pillow and verified to round-trip.
const PNG = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFElEQVR4nGM8saWHARtgwio6aCUAmYMCGEvikSgAAAAASUVORK5CYII=',
    'base64');

const photoPath = () => {
    const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'ayura-e2e-')), 'leak.png');
    fs.writeFileSync(file, PNG);
    return file;
};

// Two kinds of "not a photo", because they are caught in two different places:
//
//   * an honestly-named PDF: the browser reports a non-image type, so the picker refuses it
//     before the customer waits for an upload;
//   * a PDF wearing a .png name: the browser infers the type from the extension and reports
//     image/png, so the picker lets it through and the SERVER refuses it after opening the
//     bytes. That is the real gate, and the shape of an actual attack.
const notAPhotoPath = (name = 'invoice.pdf') => {
    const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'ayura-e2e-')), name);
    fs.writeFileSync(file, '%PDF-1.4\nnot a picture at all\n%%EOF\n');
    return file;
};

const addProduct = async (page, slug, size) => {
    await page.goto(`/detail/${slug}`);
    await page.getByTestId('option-Size').getByRole('button', { name: size }).click();
    const added = page.waitForResponse((r) => r.url().includes('/cart-view/') && r.request().method() === 'POST');
    await page.getByTestId('add-to-cart').click();
    expect((await added).status()).toBeLessThan(300);
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

test.describe.serial('phase F support', () => {
    test('a customer reports a damaged order with a photo and the owner answers', async ({ page }) => {
        test.setTimeout(180_000);

        // --- a customer orders, then reports a problem from the order itself
        await signIn(page, CUSTOMER);
        await addProduct(page, 'body-butter', '100 g');
        const oid = await checkoutCod(page, CUSTOMER);

        await page.goto(`/customer/order/detail/${oid}/`);
        await expect(page.getByTestId('order-detail-page')).toBeVisible();
        await page.getByTestId('order-report-problem').click();

        await expect(page.getByTestId('support-new')).toBeVisible();
        await expect(page.locator('body')).toContainText(`About order ${oid}`);
        // Signed in, so there is no email to retype.
        await expect(page.locator('#supportEmail')).toHaveCount(0);

        await page.getByTestId('support-reason').selectOption('My order arrived damaged or leaking');
        await page.getByTestId('support-body').fill('The body butter jar was cracked and leaking in the box.');

        // An honestly-named PDF never leaves the browser.
        await page.getByTestId('photo-input').setInputFiles(notAPhotoPath('invoice.pdf'));
        await expect(page.getByTestId('photo-problem')).toContainText('not a photo');
        await expect(page.getByTestId('photo-chosen')).toHaveCount(0);

        // A PDF renamed .png gets past the browser, because the type is guessed from the name.
        // The server opens the bytes and refuses it, and nothing is stored.
        await page.getByTestId('photo-input').setInputFiles(notAPhotoPath('leak.png'));
        await expect(page.getByTestId('photo-chosen')).toHaveCount(1);
        await page.getByTestId('support-send').click();
        await expect(page.getByTestId('support-error')).toContainText('is not a photo');
        await expect(page.getByTestId('support-sent')).toHaveCount(0);

        // Swap it for a real photo and the message goes.
        await page.getByTestId('photo-remove').click();
        await expect(page.getByTestId('photo-chosen')).toHaveCount(0);
        await page.getByTestId('photo-input').setInputFiles(photoPath());
        await expect(page.getByTestId('photo-chosen')).toHaveCount(1);

        await page.getByTestId('support-send').click();
        await expect(page.getByTestId('support-sent')).toBeVisible();
        const ref = (await page.getByTestId('support-ref').innerText()).trim();
        expect(ref).toHaveLength(10);
        // A signed-in customer signs in instead of keeping a link.
        await expect(page.getByTestId('support-guest-link')).toHaveCount(0);

        // The order page now lists the thread instead of inviting the same report twice.
        await page.goto(`/customer/order/detail/${oid}/`);
        await expect(page.getByTestId('order-support-threads')).toContainText('damaged or leaking');
        await expect(page.getByTestId('order-report-problem')).toHaveText('Report something else');
        await signOut(page);

        // --- the owner finds it in the inbox, with the photo, and answers
        await signIn(page, OWNER);
        await page.goto('/admin-area/dashboard/');
        await expect(page.getByTestId('sidebar-badge-support')).toHaveText('1');

        await page.goto('/admin-area/owner/support/');
        const row = page.getByTestId('owner-support-row').filter({ hasText: ref });
        await expect(row).toHaveCount(1);
        await expect(row.getByTestId('owner-support-unread')).toBeVisible();
        await expect(row).toContainText(oid);
        await row.getByRole('link').first().click();

        await expect(page.getByTestId('owner-support-thread')).toBeVisible();
        await expect(page.getByTestId('owner-support-status')).toHaveText('Needs an answer');
        await expect(page.getByTestId('owner-message')).toHaveCount(1);
        await expect(page.getByTestId('owner-message-photo')).toHaveCount(1);

        // An empty reply cannot be sent.
        await expect(page.getByTestId('owner-reply-send')).toBeDisabled();
        await page.getByTestId('owner-reply-body').fill('So sorry about that. A replacement jar goes out today.');
        await page.getByTestId('owner-reply-send').click();
        await expect(page.getByTestId('owner-support-status')).toHaveText('Answered');
        await expect(page.getByTestId('owner-message')).toHaveCount(2);

        // Looking at it cleared the unread mark.
        await page.goto('/admin-area/owner/support/');
        await expect(page.getByTestId('sidebar-badge-support')).toHaveCount(0);
        await signOut(page);

        // --- the customer sees the reply and writes back on the same thread
        await signIn(page, CUSTOMER);
        await page.goto('/support/mine');
        await expect(page.getByTestId('support-new-replies')).toContainText('new reply');
        const mine = page.getByTestId('support-mine-row').filter({ hasText: ref });
        await expect(mine.getByTestId('support-badge')).toBeVisible();
        await mine.getByRole('link').click();

        await expect(page.getByTestId('support-thread')).toBeVisible();
        await expect(page.getByTestId('thread-status')).toHaveText('Answered');
        await expect(page.getByTestId('thread-message')).toHaveCount(2);
        await expect(page.getByTestId('thread-message').last()).toContainText('replacement jar');

        await page.getByTestId('thread-reply-body').fill('Thank you, that is very kind.');
        await page.getByTestId('thread-send').click();
        await expect(page.getByTestId('thread-message')).toHaveCount(3);
        await expect(page.getByTestId('thread-status')).toHaveText('Waiting for us');

        // Reading it cleared the badge.
        await page.goto('/support/mine');
        await expect(page.getByTestId('support-new-replies')).toHaveCount(0);
        await signOut(page);
    });

    test('a guest reports a problem and their link opens only their own conversation', async ({ page }) => {
        test.setTimeout(180_000);

        // No account at all: straight from the contact page.
        await page.goto('/contact');
        await expect(page.getByTestId('contact-get-help')).toBeVisible();
        await page.getByTestId('contact-get-help-link').click();

        await expect(page.getByTestId('support-new')).toBeVisible();
        await page.getByTestId('support-reason').selectOption('Something is missing from my order');
        await page.getByTestId('support-body').fill('The soap I ordered was not in the parcel.');
        await page.locator('#supportEmail').fill('guest-f@e2e.test');
        await page.getByTestId('support-send').click();

        await expect(page.getByTestId('support-sent')).toBeVisible();
        const guestRef = (await page.getByTestId('support-ref').innerText()).trim();
        // A guest has nothing to sign in to, so the link is put in front of them.
        const link = page.getByTestId('support-guest-link');
        await expect(link).toBeVisible();
        const href = await link.getByRole('link').getAttribute('href');
        expect(href).toContain('/support/thread?token=');

        // The link opens their conversation.
        await page.goto(href);
        await expect(page.getByTestId('support-thread')).toBeVisible();
        await expect(page.getByTestId('thread-ref')).toHaveText(guestRef);
        await expect(page.getByTestId('thread-message')).toHaveCount(1);

        // They can add to it without an account.
        await page.getByTestId('thread-reply-body').fill('It was the lavender one, if that helps.');
        await page.getByTestId('thread-send').click();
        await expect(page.getByTestId('thread-message')).toHaveCount(2);

        // The reference alone opens nothing: knowing it is not access.
        await page.goto(`/support/thread/${guestRef}`);
        await expect(page.getByTestId('thread-unavailable')).toBeVisible();

        // A tampered token opens nothing either.
        await page.goto(`${href.slice(0, -4)}xxxx`);
        await expect(page.getByTestId('thread-unavailable')).toBeVisible();

        // And the owner sees it as a guest thread.
        await signIn(page, OWNER);
        await page.goto('/admin-area/owner/support/');
        const row = page.getByTestId('owner-support-row').filter({ hasText: guestRef });
        await expect(row).toContainText('guest-f@e2e.test');
        await expect(row).toContainText('(guest)');

        // Closing it is not the last word: the customer can still write back.
        await row.getByRole('link').first().click();
        await page.getByTestId('owner-reply-body').fill('We have posted the missing soap.');
        await page.getByTestId('owner-reply-send-close').click();
        await expect(page.getByTestId('owner-support-status')).toHaveText('Closed');
        await signOut(page);

        await page.goto(href);
        await expect(page.getByTestId('thread-status')).toHaveText('Closed');
        await expect(page.locator('body')).toContainText('reopens this conversation');
        await page.getByTestId('thread-reply-body').fill('It arrived, thank you.');
        await page.getByTestId('thread-send').click();
        await expect(page.getByTestId('thread-status')).toHaveText('Waiting for us');
    });

    test('the grievance officer block appears only once the owner has filled it in', async ({ page }) => {
        test.setTimeout(120_000);

        // Nothing published until she types it (ROADMAP L4).
        await page.goto('/contact');
        await expect(page.getByTestId('policy-contact')).toBeVisible();
        await expect(page.getByTestId('grievance-officer')).toHaveCount(0);

        await signIn(page, OWNER);
        await page.goto('/admin-area/owner/settings/');
        await expect(page.getByTestId('owner-settings')).toBeVisible();
        await page.getByTestId('setting-grievance-name').fill('A. Owner');
        await page.getByTestId('setting-grievance-designation').fill('Proprietor');
        await page.getByTestId('setting-grievance-email').fill('grievance@e2e.test');
        await page.getByTestId('setting-grievance-phone').fill('+91 98765 43210');
        await page.getByTestId('setting-grievance-days').fill('2');
        await page.getByTestId('save-settings').click();
        await expect(page.getByTestId('settings-notice')).toBeVisible();
        await signOut(page);

        // Her own words, and only the fields she filled.
        await page.goto('/contact');
        const block = page.getByTestId('grievance-officer');
        await expect(block).toBeVisible();
        await expect(block).toContainText('A. Owner');
        await expect(block).toContainText('Proprietor');
        await expect(block).toContainText('grievance@e2e.test');
        await expect(block).toContainText('2 days');
        // She left the address blank, so no empty row is drawn for it.
        await expect(block).not.toContainText('Address');
    });
});
