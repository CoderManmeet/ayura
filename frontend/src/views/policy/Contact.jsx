import { Link } from 'react-router-dom';
import { LifeBuoy, Mail, MessageCircle } from 'lucide-react';

import { STORE_NAME, SUPPORT_EMAIL, WHATSAPP_LINK } from '../../utils/constants';
import usePageTitle from '../../utils/usePageTitle';
import { PageIntro } from '../ui/kit';
import GrievanceOfficer from './GrievanceOfficer';
import { POLICY_LINKS } from './policies';

// Contact page: a named way to reach the store by email or WhatsApp (ROADMAP P13), and from
// phase F the "Get help" thread, which is the one route that keeps a record both sides can read.
// The address and number come from VITE_SUPPORT_EMAIL / VITE_WHATSAPP_NUMBER.
function Contact() {
    usePageTitle('Contact us');
    return (
        <main data-testid="policy-contact">
            <PageIntro eyebrow="Customer care" title="Contact us" />
            <div className="mx-auto max-w-3xl px-5 py-12 md:px-10 md:py-20">
                <p className="text-sm leading-7 text-subtle">Need help with an order from {STORE_NAME}? Tell us what happened and we will answer on the same thread — that way nothing gets lost. You can also write to us or message us on WhatsApp.</p>

                <div className="mt-8 border border-line bg-panel p-6" data-testid="contact-get-help">
                    <div className="flex items-start gap-4">
                        <LifeBuoy className="mt-1 size-5 shrink-0 text-accent" aria-hidden="true" />
                        <div>
                            <p className="ui-label">Something wrong with an order?</p>
                            <p className="mt-2 text-sm leading-7 text-subtle">
                                Report it here, with photos if it arrived damaged or leaking. You will get a
                                reference and can follow the conversation, with or without an account.
                            </p>
                            <div className="mt-5 flex flex-wrap items-center gap-5">
                                <Link to="/support/new" className="ui-btn" data-testid="contact-get-help-link">Get help</Link>
                                <Link to="/support/find" className="ui-link ui-caption">Find my conversation</Link>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="mt-8 grid gap-4 sm:grid-cols-2">
                    <a href={`mailto:${SUPPORT_EMAIL}`} className="flex items-center gap-4 border border-line p-5" data-testid="contact-email">
                        <Mail className="size-5 text-accent" aria-hidden="true" />
                        <span><span className="ui-label block">Email</span><span className="text-sm">{SUPPORT_EMAIL}</span></span>
                    </a>
                    <a href={WHATSAPP_LINK} target="_blank" rel="noopener noreferrer" className="flex items-center gap-4 border border-line p-5" data-testid="contact-whatsapp">
                        <MessageCircle className="size-5 text-accent" aria-hidden="true" />
                        <span><span className="ui-label block">WhatsApp</span><span className="text-sm">Chat on WhatsApp</span></span>
                    </a>
                </div>

                <GrievanceOfficer />

                <h2 className="mt-14 font-display text-2xl">Policies</h2>
                <ul className="mt-4 flex flex-col gap-3 text-sm">
                    {POLICY_LINKS.map((link) => (
                        <li key={link.path}><Link to={link.path} className="ui-link">{link.title}</Link></li>
                    ))}
                </ul>
            </div>
        </main>
    );
}

export default Contact;
