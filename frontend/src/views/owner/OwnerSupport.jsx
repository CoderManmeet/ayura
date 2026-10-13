import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import moment from 'moment';

import apiInstance from '../../utils/axios';
import Sidebar from '../vendor/Sidebar';

// The support inbox (Ayura phase E's neighbour, phase F).
//
// One screen, two modes: the list of conversations, and one conversation open. Opening a
// conversation clears its unread mark, so the sidebar count means "not yet looked at".
//
// Replying moves the thread to Answered and tells the customer by email. Closing is never the
// last word: a customer who writes back reopens the thread and it returns to this inbox.

const messageOf = (error) => error?.response?.data?.message || 'Something went wrong. Please try again.';

const STATUS_BADGE = {
    OPEN: 'bg-danger',
    ANSWERED: 'bg-secondary',
    CLOSED: 'bg-dark',
};

const STATUS_LABEL = { OPEN: 'Needs an answer', ANSWERED: 'Answered', CLOSED: 'Closed' };

// `ref` is reserved by React and is never passed through to a component, so the thread's
// reference travels under its own name.
function Thread({ threadRef }) {
    const [thread, setThread] = useState(null);
    const [failed, setFailed] = useState('');
    const [body, setBody] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    const load = useCallback(() => {
        apiInstance.get(`owner/support/${threadRef}/`)
            .then((res) => setThread(res.data))
            .catch((problem) => setFailed(messageOf(problem)));
    }, [threadRef]);

    useEffect(() => { load() }, [load]);

    const act = async (request) => {
        setBusy(true);
        setError('');
        try {
            const res = await request();
            setThread(res.data);
            setBody('');
        } catch (problem) {
            setError(messageOf(problem));
        } finally {
            setBusy(false);
        }
    };

    const reply = (close) => (event) => {
        event.preventDefault();
        return act(() => apiInstance.post(`owner/support/${threadRef}/`, { body, close: close ? 'true' : '' }));
    };

    const setClosed = (action) => () =>
        act(() => apiInstance.post(`owner/support/${threadRef}/close/`, { action }));

    if (failed) return <div className="alert alert-danger" role="alert">{failed}</div>;
    if (thread === null) return <p>Loading...</p>;

    return (
        <div data-testid="owner-support-thread" data-ref={thread.ref}>
            <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-3">
                <div>
                    <h5 className="mb-1">{thread.subject}</h5>
                    <p className="text-subtle mb-0"><small>
                        {thread.ref}
                        {' · '}{thread.customer_name || thread.email}
                        {thread.has_account ? '' : ' (guest)'}
                        {thread.order_oid && <> · <a href={`/admin-area/owner/orders/${thread.order_oid}/`}>order {thread.order_oid}</a></>}
                    </small></p>
                </div>
                <span className={`badge ${STATUS_BADGE[thread.status] || 'bg-secondary'}`} data-testid="owner-support-status">
                    {STATUS_LABEL[thread.status] || thread.status}
                </span>
            </div>

            <div className="card mb-4"><div className="card-body">
                <h6 className="card-title">How to reach them</h6>
                <p className="mb-0"><small>
                    Email: {thread.email}
                    {thread.phone_e164 && <> · Phone: {thread.phone_e164}</>}
                </small></p>
            </div></div>

            <div className="card mb-4"><div className="card-body">
                <h6 className="card-title">Conversation</h6>
                {thread.messages.map((message) => (
                    <div key={message.id} className="border-bottom pb-3 mb-3" data-testid="owner-message"
                        data-author={message.author}>
                        <p className="text-subtle mb-1"><small>
                            <b>{message.author === 'OWNER' ? 'You' : 'Customer'}</b>
                            {' · '}{moment(message.created_at).format('DD MMM YYYY, HH:mm')}
                        </small></p>
                        <p className="mb-2" style={{ whiteSpace: 'pre-line' }}>{message.body}</p>
                        {message.photos.length > 0 &&
                            <div className="d-flex flex-wrap gap-2">
                                {message.photos.map((photo) => (
                                    <a key={photo.id} href={photo.url} target="_blank" rel="noopener noreferrer"
                                        data-testid="owner-message-photo">
                                        <img src={photo.url} alt="" style={{ width: '6rem', height: '6rem', objectFit: 'cover' }} />
                                    </a>
                                ))}
                            </div>
                        }
                    </div>
                ))}
            </div></div>

            <div className="card mb-4"><div className="card-body">
                <h6 className="card-title">Your reply</h6>
                <p className="text-subtle"><small>
                    The customer is emailed a link to this conversation. They can write back on it, which
                    reopens it even if you close it now.
                </small></p>
                <form onSubmit={reply(false)}>
                    <textarea className="form-control mb-3" rows={5} value={body} maxLength={4000}
                        onChange={(event) => setBody(event.target.value)} aria-label="Your reply"
                        data-testid="owner-reply-body" />
                    {error && <div className="alert alert-danger" role="alert" data-testid="owner-support-error">{error}</div>}
                    <div className="d-flex flex-wrap gap-2">
                        <button type="submit" className="btn btn-primary" disabled={busy || !body.trim()}
                            data-testid="owner-reply-send">{busy ? 'Sending...' : 'Send reply'}</button>
                        <button type="button" className="btn btn-outline-primary" disabled={busy || !body.trim()}
                            onClick={reply(true)} data-testid="owner-reply-send-close">Send and close</button>
                        {thread.status !== 'CLOSED' &&
                            <button type="button" className="btn btn-outline-secondary" disabled={busy}
                                onClick={setClosed('close')} data-testid="owner-support-close">Close without replying</button>
                        }
                        {thread.status === 'CLOSED' &&
                            <button type="button" className="btn btn-outline-secondary" disabled={busy}
                                onClick={setClosed('reopen')} data-testid="owner-support-reopen">Reopen</button>
                        }
                    </div>
                </form>
            </div></div>

            <Link to="/admin-area/owner/support/" className="btn btn-outline-secondary btn-sm">Back to the inbox</Link>
        </div>
    );
}

function Inbox() {
    const [data, setData] = useState(null);
    const [failed, setFailed] = useState('');
    const [filter, setFilter] = useState('live');

    const load = useCallback(() => {
        const params = filter === 'live' ? undefined : { status: filter };
        apiInstance.get('owner/support/', { params })
            .then((res) => setData(res.data))
            .catch((problem) => setFailed(messageOf(problem)));
    }, [filter]);

    useEffect(() => { load() }, [load]);

    if (failed) return <div className="alert alert-danger" role="alert">{failed}</div>;
    if (data === null) return <p>Loading...</p>;

    const tabs = [['live', 'Needs me'], ['open', 'Open'], ['answered', 'Answered'], ['closed', 'Closed']];

    return (
        <div data-testid="owner-support-inbox">
            <p className="text-subtle"><small>
                Every message a customer has sent. {data.counts.unread > 0
                    ? `${data.counts.unread} not looked at yet.`
                    : 'Nothing new.'}
            </small></p>

            <div className="d-flex flex-wrap gap-2 mb-3">
                {tabs.map(([value, label]) => (
                    <button key={value} type="button" onClick={() => setFilter(value)}
                        className={`btn btn-sm ${filter === value ? 'btn-primary' : 'btn-outline-secondary'}`}
                        data-testid={`support-tab-${value}`}>
                        {label}{value === 'open' ? ` (${data.counts.open})` : ''}
                    </button>
                ))}
            </div>

            {data.queries.length === 0 &&
                <div className="card"><div className="card-body" data-testid="owner-support-empty">
                    <p className="mb-0">Nothing here.</p>
                </div></div>
            }

            {data.queries.length > 0 &&
                <div className="table-responsive">
                    <table className="table">
                        <thead className="table-dark">
                            <tr><th>Subject</th><th>Customer</th><th>Order</th><th>Last message</th><th>Status</th></tr>
                        </thead>
                        <tbody>
                            {data.queries.map((query) => (
                                <tr key={query.ref} data-testid="owner-support-row" data-ref={query.ref}>
                                    <td>
                                        <Link to={`/admin-area/owner/support/${query.ref}/`}>{query.subject}</Link>
                                        {query.unread && <span className="badge bg-danger ms-2" data-testid="owner-support-unread">New</span>}
                                        <div className="text-subtle"><small>{query.ref} · {query.message_count} message(s)</small></div>
                                    </td>
                                    <td>
                                        {query.customer_name || '—'}
                                        <div className="text-subtle"><small>{query.email}{query.has_account ? '' : ' (guest)'}</small></div>
                                    </td>
                                    <td>{query.order_oid
                                        ? <Link to={`/admin-area/owner/orders/${query.order_oid}/`}>{query.order_oid}</Link>
                                        : '—'}</td>
                                    <td>{moment(query.last_message_at).format('DD MMM, HH:mm')}</td>
                                    <td><span className={`badge ${STATUS_BADGE[query.status] || 'bg-secondary'}`}>
                                        {STATUS_LABEL[query.status] || query.status}
                                    </span></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            }
        </div>
    );
}

function OwnerSupport() {
    const { ref: threadRef } = useParams();

    return (
        <div className="container-fluid" id="main">
            <div className="row row-offcanvas row-offcanvas-left h-100">
                <Sidebar />
                <div className="col-md-9 col-lg-10 main mt-4" data-testid="owner-support">
                    <h4>Support</h4>
                    {threadRef ? <Thread threadRef={threadRef} /> : <Inbox />}
                </div>
            </div>
        </div>
    );
}

export default OwnerSupport;
