import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import UserData from '../plugin/UserData';
import usePageTitle from '../../utils/usePageTitle';
import { Field, PageIntro } from '../ui/kit';
import PhotoPicker from './PhotoPicker';
import { messageOf, openQuery } from './supportApi';

// "Get help": reporting a problem (Ayura phase F).
//
// Reached from the contact page, and from an order with ?order=<oid> filled in, which is how
// "Report a problem" on an order arrives here.
//
// A guest needs no account. When they send the message the server hands back a signed link to
// the conversation, which this page shows and which is also emailed to them: that link is their
// way back in, so it is put in front of them plainly rather than buried in an email they may
// never get.

const REASONS = [
    'My order arrived damaged or leaking',
    'Something is missing from my order',
    'I was sent the wrong item',
    'My order has not arrived',
    'A question about a product',
    'Something else',
];

function NewQuery() {
    usePageTitle('Get help');
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const userData = UserData();

    const orderOid = params.get('order') || '';
    const [reason, setReason] = useState(REASONS[0]);
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [photos, setPhotos] = useState([]);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [sent, setSent] = useState(null);

    // A signed-in customer does not retype their address: the server uses the account's.
    const signedIn = Boolean(userData?.user_id);
    useEffect(() => { if (signedIn) setError(''); }, [signedIn]);

    const send = async (event) => {
        event.preventDefault();
        setBusy(true);
        setError('');
        try {
            const thread = await openQuery({
                subject: subject.trim() || reason,
                body,
                email: signedIn ? '' : email,
                phone,
                orderOid,
                photos,
            });
            setSent(thread);
        } catch (problem) {
            setError(messageOf(problem));
        } finally {
            setBusy(false);
        }
    };

    if (sent) {
        return (
            <main data-testid="support-sent">
                <PageIntro eyebrow="Customer care" title="We have your message." />
                <div className="mx-auto max-w-3xl px-5 py-12 md:px-10 md:py-20">
                    <p className="text-sm leading-7">
                        Thank you. We will come back to you as soon as we can. Your reference is{' '}
                        <b data-testid="support-ref">{sent.ref}</b>.
                    </p>
                    {sent.link &&
                        <div className="mt-8 border border-line bg-panel p-5" data-testid="support-guest-link">
                            <p className="ui-label mb-2">Your conversation</p>
                            <p className="text-sm leading-7 text-subtle">
                                You ordered as a guest, so there is no account to sign in to. Keep this link: it
                                opens this conversation and nothing else. We have emailed it to you as well.
                            </p>
                            <p className="mt-3 break-all text-xs">
                                <Link to={sent.link.replace(/^.*\/support\//, '/support/')} className="ui-link">
                                    {sent.link}
                                </Link>
                            </p>
                        </div>
                    }
                    <div className="mt-10 flex flex-wrap items-center gap-5">
                        {signedIn
                            ? <Link to="/support/mine" className="ui-btn">My conversations</Link>
                            : <Link to="/" className="ui-btn">Back to the shop</Link>
                        }
                        <Link to="/contact" className="ui-link ui-caption">Other ways to reach us</Link>
                    </div>
                </div>
            </main>
        );
    }

    return (
        <main data-testid="support-new">
            <PageIntro eyebrow="Customer care" title="Tell us what went wrong.">
                <p className="mt-5 max-w-xl text-sm leading-7 text-subtle">
                    {orderOid
                        ? `About order ${orderOid}. We will reply to you here, and by email.`
                        : 'We read every message ourselves. If it is about an order, your order number helps us most.'}
                </p>
            </PageIntro>

            <div className="mx-auto max-w-3xl px-5 py-12 md:px-10 md:py-16">
                <form onSubmit={send} className="flex flex-col gap-7">
                    <div className="flex flex-col gap-2">
                        <label htmlFor="supportReason" className="ui-label">What is this about?</label>
                        <select id="supportReason" value={reason} onChange={(event) => setReason(event.target.value)}
                            className="ui-input" data-testid="support-reason">
                            {REASONS.map((option) => <option key={option} value={option}>{option}</option>)}
                        </select>
                    </div>

                    <Field id="supportSubject" label="Subject (optional)" value={subject}
                        onChange={(event) => setSubject(event.target.value)} maxLength={200} />

                    <div className="flex flex-col gap-2">
                        <label htmlFor="supportBody" className="ui-label">What happened?</label>
                        <textarea id="supportBody" rows={6} value={body} required maxLength={4000}
                            onChange={(event) => setBody(event.target.value)}
                            placeholder="Tell us what you received and what is wrong with it."
                            className="w-full border border-line-strong bg-transparent p-3 text-sm outline-none focus:border-accent"
                            data-testid="support-body" />
                    </div>

                    {!signedIn &&
                        <div className="grid gap-7 sm:grid-cols-2">
                            <Field id="supportEmail" label="Your email" type="email" value={email} required
                                autoComplete="email" onChange={(event) => setEmail(event.target.value)} />
                            <Field id="supportPhone" label="Your phone (optional)" value={phone} inputMode="tel"
                                autoComplete="tel" onChange={(event) => setPhone(event.target.value)} />
                        </div>
                    }

                    <PhotoPicker files={photos} onChange={setPhotos} idPrefix="support-new" />

                    {error && <p className="text-sm text-danger" role="alert" data-testid="support-error">{error}</p>}

                    <div className="flex flex-wrap items-center gap-5">
                        <button type="submit" className="ui-btn" disabled={busy} data-testid="support-send">
                            {busy ? 'Sending...' : 'Send message'}
                        </button>
                        <button type="button" className="ui-link ui-caption" onClick={() => navigate(-1)}>Cancel</button>
                    </div>
                </form>
            </div>
        </main>
    );
}

export default NewQuery;
