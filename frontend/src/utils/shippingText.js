// The sentences the storefront uses to describe shipping and Cash on Delivery (Phase C).
//
// They are built from the store settings the server sends (`addon/`), so whatever the owner
// switches on or off in "Store settings" is what every page says: the announcement bar, the
// home page, the product page and the shipping policy. Amounts are integer paise, formatted
// here; nothing is added up in the browser.

import { formatINR } from './money';

const known = (settings) => settings && settings.shipping_flat_paise != null;
const shippingOn = (settings) => settings.shipping_enabled !== false;
const freeShippingOn = (settings) => shippingOn(settings) && settings.free_shipping_enabled !== false;

// What a Cash on Delivery order pays on top, in paise (0 when COD or its fee is off).
export function codFeePaise(settings) {
    if (!settings || settings.cod_enabled === false || !settings.cod_fee_enabled) return 0;
    return Number(settings.cod_fee_paise) > 0 ? Number(settings.cod_fee_paise) : 0;
}

// One line for the announcement bar, or '' when there is nothing true and short to say.
export function announcementText(settings) {
    if (!known(settings)) return '';
    if (!shippingOn(settings)) return 'Free shipping on every order';
    if (freeShippingOn(settings)) return `Free shipping on orders of ${formatINR(settings.free_shipping_threshold_paise)} or more`;
    return '';
}

// The short line under the price on a product page.
export function shippingLine(settings) {
    if (!known(settings)) return '';
    if (!shippingOn(settings)) return 'Free shipping on every order.';
    if (!freeShippingOn(settings)) return `Shipping ${formatINR(settings.shipping_flat_paise)} on every order.`;
    return `Shipping ${formatINR(settings.shipping_flat_paise)}. Free on orders of ${formatINR(settings.free_shipping_threshold_paise)} or more.`;
}

// The full sentence for the shipping policy.
export function shippingSentence(settings) {
    if (!known(settings)) return '';
    if (!shippingOn(settings)) return 'Shipping is free on every order.';
    const charge = `Shipping is ${formatINR(settings.shipping_flat_paise)} per order.`;
    if (!freeShippingOn(settings)) return charge;
    return `${charge} Orders of ${formatINR(settings.free_shipping_threshold_paise)} or more (after any discount) ship free.`;
}

// A short headline and a sub-line for the shipping tile on the home page.
export function shippingTile(settings) {
    if (!known(settings)) return null;
    if (!shippingOn(settings)) return { title: 'Free shipping', detail: 'On every order' };
    if (!freeShippingOn(settings)) return { title: `Shipping ${formatINR(settings.shipping_flat_paise)}`, detail: 'Per order' };
    return {
        title: `Shipping ${formatINR(settings.shipping_flat_paise)}`,
        detail: `Free on orders of ${formatINR(settings.free_shipping_threshold_paise)} or more`,
    };
}

// How to pay, for the home page tile.
export function paymentTile(settings) {
    if (!settings || settings.cod_enabled === false) {
        return { title: 'UPI, cards or netbanking', detail: 'Pay securely online' };
    }
    const fee = codFeePaise(settings);
    if (fee > 0) return { title: 'UPI, cards or cash', detail: `Pay online, or on delivery for a ${formatINR(fee)} fee` };
    return { title: 'UPI, cards or cash', detail: 'Pay online or on delivery, at the same price' };
}

// The Cash on Delivery sentence for the shipping policy, or '' when there is none to make.
export function codSentence(settings) {
    if (!settings || settings.cod_enabled === false) return 'Cash on Delivery is not available at the moment.';
    const fee = codFeePaise(settings);
    if (fee > 0) {
        return `Cash on Delivery orders pay a ${formatINR(fee)} fee. It is shown on the payment choice and in the total at checkout, before you place the order. Paying online adds no fee.`;
    }
    return 'Cash on Delivery costs the same as paying online.';
}
