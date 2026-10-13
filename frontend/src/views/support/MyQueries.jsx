import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import moment from 'moment';

import usePageTitle from '../../utils/usePageTitle';
import { Loading, PageIntro } from '../ui/kit';
import { STATUS_LABEL, messageOf, myQueries } from './supportApi';

// "My conversations": every support thread of the signed-in customer (Ayura phase F).
//
// Threads opened as a guest with this account's email address are here too, so creating an
// account after reporting a problem does not lose the conversation.

const STATUS_CLASS = {
    OPEN: 'text-accent',
    ANSWERED: 'text-success',
    CLOSED: 'text-subtle',
};

function MyQueries() {
    usePageTitle('My conversations');
    const [data, setData] = useState(null);
    const [failed, setFailed] = useState('');

    useEffect(() => {
        myQueries().then(setData).catch((problem) => setFailed(messageOf(problem)));
    }, []);

    if (failed) {
        return (
            <main>
                <PageIntro eyebrow="Customer care" title="My conversations" />
                <div className="mx-auto max-w-3xl px-5 py-12 md:px-10 md:py-20">
                    <p className="text-sm text-danger" role="alert">{failed}</p>
                </div>
            </main>
        );
    }
    if (data === null) return <main><Loading /></main>;

    return (
        <main data-testid="support-mine">
            <PageIntro eyebrow="Customer care" title="My conversations.">
                {data.new_replies > 0 &&
                    <p className="mt-5 text-sm text-success" data-testid="support-new-replies">
                        {data.new_replies === 1 ? 'One conversation has a new reply.' : `${data.new_replies} conversations have new replies.`}
                    </p>
                }
            </PageIntro>

            <div className="mx-auto max-w-3xl px-5 py-12 md:px-10 md:py-16">
                {data.queries.length === 0 &&
                    <div data-testid="support-mine-empty">
                        <p className="font-display text-2xl">Nothing here yet.</p>
                        <p className="mt-4 text-sm leading-7 text-subtle">
                            If something is wrong with an order, tell us and we will sort it out.
                        </p>
                        <Link to="/support/new" className="ui-btn mt-8 inline-block">Get help</Link>
                    </div>
                }

                {data.queries.length > 0 &&
                    <>
                        <ul className="flex flex-col p-0">
                            {data.queries.map((query) => (
                                <li key={query.ref} className="border-b border-line py-5" data-testid="support-mine-row">
                                    <Link to={`/support/thread/${query.ref}`} className="flex flex-wrap items-baseline justify-between gap-3">
                                        <span>
                                            <span className="font-display text-xl">{query.subject}</span>
                                            {query.has_new_reply &&
                                                <span className="ml-3 bg-accent px-2 py-0.5 text-[10px] uppercase tracking-[0.15em] text-white"
                                                    data-testid="support-badge">New reply</span>
                                            }
                                            <span className="mt-1 block text-xs text-subtle">
                                                {query.ref}
                                                {query.order_oid && ` · order ${query.order_oid}`}
                                                {' · '}{moment(query.last_message_at).format('DD MMM YYYY')}
                                            </span>
                                        </span>
                                        <span className={`ui-caption ${STATUS_CLASS[query.status] || ''}`}>
                                            {STATUS_LABEL[query.status] || query.status}
                                        </span>
                                    </Link>
                                </li>
                            ))}
                        </ul>
                        <Link to="/support/new" className="ui-btn mt-10 inline-block">Report something else</Link>
                    </>
                }
            </div>
        </main>
    );
}

export default MyQueries;
