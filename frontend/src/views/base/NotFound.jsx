import { Link } from 'react-router-dom';

import usePageTitle from '../../utils/usePageTitle';

function NotFound() {
    usePageTitle('Page not found');
    return (
        <main className="mx-auto max-w-2xl px-5 py-28 text-center" data-testid="not-found">
            <p className="ui-eyebrow mb-4">Page not found</p>
            <h1 className="font-display text-5xl">We couldn't find that page.</h1>
            <p className="mt-6 text-sm text-subtle">The page you are looking for does not exist or has moved.</p>
            <Link to="/shop" className="ui-btn mt-9">Browse the shop</Link>
        </main>
    );
}

export default NotFound;
