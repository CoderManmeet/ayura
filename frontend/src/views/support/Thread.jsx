import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import moment from 'moment';

import { STORE_NAME } from '../../utils/constants';
import usePageTitle from '../../utils/usePageTitle';
import { Loading, PageIntro } from '../ui/kit';
import PhotoPicker from './PhotoPicker';
import { STATUS_LABEL, messageOf, readThread, readThreadByLink, replyByLink, replyToThread } from './supportApi';

// One support conversation, as its customer sees it (Ayura phase F).
//
// Two ways in, one screen:
//
//   /support/thread/<ref>          a signed-in customer, authorised by their JWT
//   /support/thread?token=...      a guest, authorised by the signed link they were given
//
// The guest route carries no reference in the address: the token names the thread, so the page
// reads the thread first and learns which one it is. That means a link cannot be edited into
// somebody else's conversation.

const STATUS_CLASS = {
    OPEN: 'text-accent',
    ANSWERED: 'text-success',
    CLOSED: 'text-subtle',
};

function Message({ message }) {
    const fromUs = message.author === 'OWNER';
    return (
        <li className={`flex flex-col gap-2 ${fromUs ? 'items-start' : 'items-end'}`} data-testid="thread-message"
            data-author={message.author}>
            <div className={`max-w-[85%] p-5 ${fromUs ? 'bg-panel' : 'border border-line'}`}>
                <p className="ui-caption mb-2 text-subtle">{fromUs ? STORE_NAME : 'You'}</p>
                <p className="whitespace-pre-line text-sm leading-7">{message.body}</p>
                {message.photos.length > 0 &&
                    <ul className="mt-4 flex flex-wrap gap-3 p-0">
                        {message.photos.map((photo) => (
                            <li key={photo.id}>
                                <a href={photo.url} target="_blank" rel="noopener noreferrer"
                                    className="block size-20 overflow-hidden bg-muted" data-testid="thread-photo">
                                    <img src={photo.url} alt="" className="size-full object-cover" />
                                </a>
                            </li>
                        ))}
                    </ul>
                }
            </div>
            <p className="text-[10px] text-subtle">{moment(message.created_at).format('DD MMM YYYY, HH:mm')}</p>
        </li>
    );
}

function Thread() {
    const { ref: refFromPath } = useParams();
    const [params] = useSearchParams();
    const token = params.get('token') || '';

    const [thread, setThread] = useState(null);
    const [failed, setFailed] = useState('');
    const [body, setBody] = useState('');
    const [photos, setPhotos] = useState([]);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    usePageTitle(thread ? `Conversation ${thread.ref}` : 'Conversation');

    const load = useCallback(() => {
        if (!token && !refFromPath) {
            setFailed('This link is not valid.');
            return;
        }
        // A guest's link names the thread inside its signed token, so the server resolves it;
        // nothing here has to read the token, and there is no reference in the link to edit.
        const ask = token ? readThreadByLink(token) : readThread(refFromPath);
        ask.then(setThread).catch((problem) => setFailed(messageOf(problem)));
    }, [refFromPath, token]);

    useEffect(() => { load(); }, [load]);

    const send = async (event) => {
        event.preventDefault();
        setBusy(true);
        setError('');
        try {
            const updated = token
                ? await replyByLink(token, { body, photos })
                : await replyToThread(thread.ref, { body, photos });
            setThread(updated);
            setBody('');
            setPhotos([]);
        } catch (problem) {
            setError(messageOf(problem));
        } finally {
            setBusy(false);
        }
    };

    if (failed) {
        return (
            <main data-testid="thread-unavailable">
                <PageIntro eyebrow="Customer care" title="We cannot open that conversation." />
                <div className="mx-auto max-w-3xl px-5 py-12 md:px-10 md:py-20">
                    <p className="text-sm leading-7">{failed}</p>
                    <div className="mt-8 flex flex-wrap items-center gap-5">
                        <Link to="/support/new" className="ui-btn">Start a new message</Link>
                        <Link to="/support/find" className="ui-link ui-caption">Find my conversation</Link>
                    </div>
                </div>
            </main>
        );
    }

    if (thread === null) return <main><Loading /></main>;

    return (
        <main data-testid="support-thread">
            <PageIntro eyebrow="Customer care" title={thread.subject}>
                <p className="mt-5 text-xs text-subtle">
                    <span data-testid="thread-ref">{thread.ref}</span>
                    {thread.order_oid && <> · order <Link to={`/customer/order/detail/${thread.order_oid}/`} className="ui-link">{thread.order_oid}</Link></>}
                    {' · '}
                    <span className={STATUS_CLASS[thread.status] || ''} data-testid="thread-status">
                        {STATUS_LABEL[thread.status] || thread.status}
                    </span>
                </p>
            </PageIntro>

            <div className="mx-auto max-w-3xl px-5 py-12 md:px-10 md:py-16">
                <ul className="flex flex-col gap-8 p-0">
                    {thread.messages.map((message) => <Message key={message.id} message={message} />)}
                </ul>

                <form onSubmit={send} className="mt-12 flex flex-col gap-5 border-t border-line pt-10">
                    <div className="flex flex-col gap-2">
                        <label htmlFor="threadReply" className="ui-label">
                            {thread.status === 'CLOSED' ? 'Still not sorted out? Write back' : 'Add to this conversation'}
                        </label>
                        <textarea id="threadReply" rows={4} value={body} required maxLength={4000}
                            onChange={(event) => setBody(event.target.value)}
                            className="w-full border border-line-strong bg-transparent p-3 text-sm outline-none focus:border-accent"
                            data-testid="thread-reply-body" />
                        {thread.status === 'CLOSED' &&
                            <p className="text-xs text-subtle">Writing back reopens this conversation.</p>
                        }
                    </div>

                    <PhotoPicker files={photos} onChange={setPhotos} idPrefix="thread" />

                    {error && <p className="text-sm text-danger" role="alert" data-testid="thread-error">{error}</p>}

                    <div className="flex flex-wrap items-center gap-5">
                        <button type="submit" className="ui-btn w-fit" disabled={busy} data-testid="thread-send">
                            {busy ? 'Sending...' : 'Send'}
                        </button>
                        {!token && <Link to="/support/mine" className="ui-link ui-caption">My conversations</Link>}
                    </div>
                </form>
            </div>
        </main>
    );
}

export default Thread;
