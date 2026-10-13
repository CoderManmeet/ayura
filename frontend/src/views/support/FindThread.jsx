import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import usePageTitle from '../../utils/usePageTitle';
import { Field, PageIntro } from '../ui/kit';
import { findThread, messageOf } from './supportApi';

// "Find my conversation" (Ayura phase F): for a guest who has lost the link they were given.
//
// The order number and the email address used on that order are both required. The server's
// answer is the same whichever of the two is wrong, so this page cannot be used to find out
// whether an address has ordered here.

function FindThread() {
    usePageTitle('Find my conversation');
    const navigate = useNavigate();
    const [orderOid, setOrderOid] = useState('');
    const [email, setEmail] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    const look = async (event) => {
        event.preventDefault();
        setBusy(true);
        setError('');
        try {
            const found = await findThread({ orderOid: orderOid.trim(), email: email.trim() });
            // The link is a full URL; this app owns that path, so route to it rather than reload.
            const path = found.link.slice(found.link.indexOf('/support/'));
            navigate(path);
        } catch (problem) {
            setError(messageOf(problem));
        } finally {
            setBusy(false);
        }
    };

    return (
        <main data-testid="support-find">
            <PageIntro eyebrow="Customer care" title="Find my conversation.">
                <p className="mt-5 max-w-xl text-sm leading-7 text-subtle">
                    Ordered as a guest and lost the link we sent you? Your order number and the email address
                    you ordered with will open it again.
                </p>
            </PageIntro>

            <div className="mx-auto max-w-3xl px-5 py-12 md:px-10 md:py-16">
                <form onSubmit={look} className="flex max-w-md flex-col gap-7">
                    <Field id="findOrder" label="Order number" value={orderOid} required
                        onChange={(event) => setOrderOid(event.target.value)} />
                    <Field id="findEmail" label="The email you ordered with" type="email" value={email} required
                        autoComplete="email" onChange={(event) => setEmail(event.target.value)} />

                    {error && <p className="text-sm text-danger" role="alert" data-testid="find-error">{error}</p>}

                    <div className="flex flex-wrap items-center gap-5">
                        <button type="submit" className="ui-btn" disabled={busy} data-testid="find-go">
                            {busy ? 'Looking...' : 'Open my conversation'}
                        </button>
                        <Link to="/support/new" className="ui-link ui-caption">Start a new message</Link>
                    </div>
                </form>
            </div>
        </main>
    );
}

export default FindThread;
