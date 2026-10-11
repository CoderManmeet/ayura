// Policy pages: Shipping, Returns and Refunds, Privacy, Terms.
//
// ============================  PLACEHOLDER COPY  ============================
// Every paragraph below is placeholder text written so the pages, links and layout can be
// built and tested. It is NOT the store's real policy and must be replaced by the owner
// before launch (docs/ROADMAP.md, phase A and the legal questions L1-L7). Nothing here has been
// reviewed as a legal statement, and none of it makes a product claim.
// While `PLACEHOLDER_COPY` is true each page shows a visible notice saying so; set it to
// false once the real text is in.
// ============================================================================
//
// The shipping figures are NOT placeholders: the pages read the live shipping charge and
// free-shipping threshold from the server's settings, so they can never disagree with what
// checkout charges.

export const PLACEHOLDER_COPY = true;

export const POLICY_LINKS = [
    { path: '/policy/shipping', title: 'Shipping Policy' },
    { path: '/policy/returns', title: 'Returns and Refunds' },
    { path: '/policy/privacy', title: 'Privacy Policy' },
    { path: '/policy/terms', title: 'Terms and Conditions' },
];

// Each section is { heading, paragraphs }. The tokens {shipping}, {threshold}, {email} and
// {store} are filled in by PolicyPage.
export const POLICIES = {
    shipping: {
        title: 'Shipping Policy',
        sections: [
            {
                heading: 'Shipping charges',
                paragraphs: [
                    'Shipping is {shipping} per order. Orders of {threshold} or more (after any discount) ship free. The shipping charge for your order is always shown in the cart and at checkout before you pay.',
                ],
            },
            {
                heading: 'Dispatch and delivery',
                paragraphs: [
                    '[PLACEHOLDER] How many working days {store} takes to dispatch an order, and the usual delivery time, go here.',
                    '[PLACEHOLDER] Where {store} delivers, and how tracking details are shared, go here.',
                ],
            },
        ],
    },
    returns: {
        title: 'Returns and Refunds',
        sections: [
            {
                heading: 'Returns',
                paragraphs: [
                    '[PLACEHOLDER] Which items can be returned, within how many days, and in what condition, go here.',
                ],
            },
            {
                heading: 'Opened products',
                paragraphs: [
                    '[PLACEHOLDER] Whether an opened skin, hair or body care product can be returned, and why, goes here.',
                ],
            },
            {
                heading: 'Damaged, leaking or wrong items',
                paragraphs: [
                    '[PLACEHOLDER] What to do if an order arrives damaged, leaking or with the wrong item, and how quickly to tell us, goes here.',
                    'If this happens, write to {email} with your order number and a photo, and we will sort it out.',
                ],
            },
            {
                heading: 'Refunds',
                paragraphs: [
                    '[PLACEHOLDER] How refunds are paid and how long they take goes here.',
                    'To ask about a return or refund, write to {email}.',
                ],
            },
        ],
    },
    privacy: {
        title: 'Privacy Policy',
        sections: [
            {
                heading: 'What we collect',
                paragraphs: [
                    '[PLACEHOLDER] The personal information {store} collects when you place an order (name, phone, email, delivery address) and why goes here.',
                ],
            },
            {
                heading: 'How it is used and shared',
                paragraphs: [
                    '[PLACEHOLDER] How that information is used, who it is shared with (for example couriers and payment providers) and how long it is kept go here.',
                    'To ask about your data, write to {email}.',
                ],
            },
        ],
    },
    terms: {
        title: 'Terms and Conditions',
        sections: [
            {
                heading: 'Orders and pricing',
                paragraphs: [
                    'All prices are in Indian rupees and are inclusive of all taxes.',
                    '[PLACEHOLDER] The terms on which {store} accepts and may cancel orders go here.',
                ],
            },
            {
                heading: 'Using our products',
                paragraphs: [
                    '[PLACEHOLDER] Patch-test advice, cautions (for example external use only, keep away from eyes) and how to store the products go here.',
                ],
            },
            {
                heading: 'Shelf life',
                paragraphs: [
                    '[PLACEHOLDER] How long the products keep, and where the use-by date is shown, goes here.',
                ],
            },
            {
                heading: 'General',
                paragraphs: [
                    '[PLACEHOLDER] Limitation of liability and governing law go here.',
                ],
            },
        ],
    },
};
