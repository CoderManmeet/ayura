import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
    Bell, Boxes, CalendarClock, ClipboardList, FolderTree, Gift, LayoutDashboard, LifeBuoy, LogOut, Package,
    PackagePlus, PlusCircle, Settings as SettingsIcon, SlidersHorizontal, Star, Store, Tag, TrendingUp,
} from 'lucide-react';

import apiInstance from '../../utils/axios';

// Admin navigation, in two groups: what the owner touches daily, and the rest.
// The screens themselves still carry their original markup; src/theme/admin.css gives it the
// store's look.
const DAILY = [
    { to: '/admin-area/dashboard/', label: 'Dashboard', Icon: LayoutDashboard },
    { to: '/admin-area/owner/orders/', label: 'Orders', Icon: ClipboardList, hint: 'COD, shipping' },
    { to: '/admin-area/products/', label: 'Products', Icon: Package },
    { to: '/admin-area/product/new/', label: 'Add product', Icon: PlusCircle },
    { to: '/admin-area/owner/categories/', label: 'Categories', Icon: FolderTree },
    { to: '/admin-area/owner/support/', label: 'Support', Icon: LifeBuoy, hint: 'Customer questions', badge: 'support' },
    { to: '/admin-area/owner/kits/', label: 'Kits', Icon: PackagePlus, hint: "What's in the box" },
    { to: '/admin-area/owner/expiry/', label: 'Stock & expiry', Icon: CalendarClock, hint: 'Write-offs, recall' },
    { to: '/admin-area/owner/reviews/', label: 'Review moderation', Icon: Star },
];

const MORE = [
    { to: '/admin-area/owner/settings/', label: 'Store settings', Icon: SlidersHorizontal, hint: 'Shipping, COD fee' },
    { to: '/admin-area/owner/samples/', label: 'Samples', Icon: Gift, hint: 'Did they convert?' },
    { to: '/admin-area/coupon/', label: 'Coupons', Icon: Tag },
    { to: '/admin-area/earning/', label: 'Earnings', Icon: TrendingUp },
    { to: '/admin-area/orders/', label: 'All orders', Icon: Boxes },
    { to: '/admin-area/reviews/', label: 'All reviews', Icon: Star },
    { to: '/admin-area/notifications/', label: 'Notifications', Icon: Bell },
    { to: '/admin-area/settings/', label: 'Shop settings', Icon: SettingsIcon },
];

function Sidebar() {
    const { pathname } = useLocation();
    // Support threads not yet looked at (phase F). A failure here leaves the badge off rather
    // than breaking the navigation.
    const [unread, setUnread] = useState(0);

    useEffect(() => {
        apiInstance.get('owner/support/')
            .then((res) => setUnread(res.data?.counts?.unread || 0))
            .catch(() => setUnread(0));
    }, [pathname]);

    const counts = { support: unread };

    const item = ({ to, label, Icon, hint, badge }) => {
        const active = pathname === to || (to !== '/admin-area/dashboard/' && pathname.startsWith(to));
        const count = badge ? counts[badge] : 0;
        return (
            <li key={to}>
                <Link
                    to={to}
                    aria-current={active ? 'page' : undefined}
                    className={`flex items-center gap-3 px-4 py-3 text-xs transition-colors ${active
                        ? 'bg-ink text-canvas'
                        : 'text-ink hover:bg-panel'}`}
                >
                    <Icon className="size-4 shrink-0" strokeWidth={1.5} aria-hidden="true" />
                    <span className="min-w-0 flex-1">
                        {label}
                        {hint && <span className={`block text-[10px] ${active ? 'text-canvas/60' : 'text-subtle'}`}>{hint}</span>}
                    </span>
                    {count > 0 &&
                        <span className="shrink-0 bg-accent px-1.5 py-0.5 text-[10px] text-white"
                            data-testid={`sidebar-badge-${badge}`}
                            aria-label={`${count} not looked at yet`}>
                            {count}
                        </span>
                    }
                </Link>
            </li>
        );
    };

    const heading = 'px-4 pb-2 pt-5 ui-caption text-subtle';

    return (
        <nav aria-label="Admin" className="w-full shrink-0 border-line bg-canvas md:w-60 md:border-r" data-testid="admin-sidebar">
            <div className="sticky top-0 pb-6">
                <p className={heading}>Every day</p>
                <ul className="list-none p-0">{DAILY.map(item)}</ul>
                <p className={heading}>More</p>
                <ul className="list-none p-0">{MORE.map(item)}</ul>
                <div className="mt-6 border-t border-line pt-4">
                    <Link to="/" className="flex items-center gap-3 px-4 py-2 text-xs text-subtle hover:text-ink">
                        <Store className="size-4" strokeWidth={1.5} aria-hidden="true" /> View the shop
                    </Link>
                    <Link to="/logout" className="flex items-center gap-3 px-4 py-2 text-xs text-subtle hover:text-ink">
                        <LogOut className="size-4" strokeWidth={1.5} aria-hidden="true" /> Sign out
                    </Link>
                </div>
            </div>
        </nav>
    );
}

export default Sidebar;