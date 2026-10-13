import { useContext, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, Search, ShoppingBag, User, X } from 'lucide-react';

import { useAuthStore } from '../../store/auth';
import { CartContext } from '../plugin/Context';
import Addon from '../plugin/Addon';
import { announcementText } from '../../utils/shippingText';
import { STORE_NAME } from '../../utils/constants';

// Storefront header. Shoppers see: Shop, About, search, their account and the
// bag. Staff additionally see one "Admin" link; nobody else sees any link to the dashboard.
// The logo is an image (frontend/public/brand/). `variant` picks the file: the word alone for
// the header, the full logo (mark above the word) for the footer. Sizes come from the theme.
const LOGO_FILES = {
    header: { src: '/brand/logo-wordmark.png', className: 'ui-logo-header', width: 599, height: 117 },
    footer: { src: '/brand/logo-full.png', className: 'ui-logo-footer', width: 615, height: 414 },
};

export function Logo({ className = '', variant = 'header' }) {
    const file = LOGO_FILES[variant] || LOGO_FILES.header;
    return (
        <Link to="/" aria-label={`${STORE_NAME} home`} className={`inline-block ${className}`} data-testid="store-logo">
            <img src={file.src} alt={STORE_NAME} width={file.width} height={file.height} className={file.className} decoding="async" />
        </Link>
    );
}

const NAV_LINK = 'ui-caption text-subtle transition-colors hover:text-ink';

function StoreHeader() {
    const [cartCount] = useContext(CartContext);
    const [menuOpen, setMenuOpen] = useState(false);
    const [searchOpen, setSearchOpen] = useState(false);
    const [search, setSearch] = useState('');
    const [isLoggedIn, user] = useAuthStore((state) => [state.isLoggedIn, state.user]);
    const addon = Addon();
    const navigate = useNavigate();
    const location = useLocation();

    // Close the menus whenever the page changes.
    useEffect(() => {
        setMenuOpen(false);
        setSearchOpen(false);
    }, [location.pathname, location.search]);

    const submitSearch = (event) => {
        event.preventDefault();
        const query = search.trim();
        navigate(query ? `/shop?query=${encodeURIComponent(query)}` : '/shop');
    };

    const signedIn = isLoggedIn();
    const isStaff = signedIn && user().is_staff;
    // Follows the owner's shipping switches; hidden when there is no free shipping to announce.
    const announcement = announcementText(addon);

    return (
        <div className="ui-chrome font-body">
            {announcement &&
                <div className="bg-ink px-4 py-2.5 text-center ui-caption text-canvas" data-testid="announcement">
                    {announcement}
                </div>
            }
            <header className="relative border-b border-line bg-canvas">
                <div className="mx-auto grid h-16 max-w-[1440px] grid-cols-[1fr_auto_1fr] items-center px-4 sm:px-5 md:h-[72px] md:px-10">
                    <div className="flex items-center gap-1 md:gap-7">
                        <button type="button" aria-label={menuOpen ? 'Close menu' : 'Open menu'} onClick={() => setMenuOpen((open) => !open)} className="flex size-10 items-center justify-start md:hidden">
                            {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
                        </button>
                        <nav aria-label="Main" className="hidden items-center gap-7 md:flex">
                            <Link to="/shop" className={NAV_LINK}>Shop</Link>
                            <Link to="/about" className={NAV_LINK}>Our story</Link>
                            <Link to="/contact" className={NAV_LINK}>Contact</Link>
                        </nav>
                    </div>
                    <Logo />
                    <div className="flex items-center justify-end gap-1 sm:gap-2 md:gap-4">
                        {isStaff && <Link to="/admin-area/dashboard/" className={`${NAV_LINK} hidden md:inline`} data-testid="admin-link">Admin</Link>}
                        <button type="button" aria-label="Search" onClick={() => setSearchOpen((open) => !open)} className="flex size-10 items-center justify-center">
                            <Search className="size-[18px]" strokeWidth={1.5} aria-hidden="true" />
                        </button>
                        <Link to={signedIn ? '/customer/orders/' : '/login'} aria-label={signedIn ? 'My account' : 'Sign in'} className="hidden size-10 items-center justify-center md:flex" data-testid="account-link">
                            <User className="size-[18px]" strokeWidth={1.5} aria-hidden="true" />
                        </Link>
                        <Link to="/cart/" aria-label="Open shopping bag" className="relative flex size-10 items-center justify-center">
                            <ShoppingBag className="size-[18px]" strokeWidth={1.5} aria-hidden="true" />
                            {cartCount > 0 &&
                                <span className="absolute right-0.5 top-0.5 flex size-4 items-center justify-center bg-accent text-[9px] leading-none text-white" data-testid="cart-count">{cartCount}</span>
                            }
                        </Link>
                    </div>
                </div>

                {searchOpen &&
                    <div className="border-t border-line px-5 py-4">
                        <form onSubmit={submitSearch} className="mx-auto flex max-w-[600px] items-center gap-3 border-b border-line-strong pb-2" role="search">
                            <Search className="size-4" aria-hidden="true" />
                            <input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} aria-label="Search products" placeholder="Search by product name" className="w-full bg-transparent text-base outline-none" />
                            <button type="submit" className="ui-caption text-accent">Search</button>
                        </form>
                    </div>
                }

                {menuOpen &&
                    <div className="absolute inset-x-0 top-full z-20 border-b border-line bg-canvas px-5 py-6 shadow-sm md:hidden">
                        <nav aria-label="Mobile" className="flex flex-col gap-5 ui-caption">
                            <Link to="/shop">Shop all</Link>
                            <Link to="/about">Our story</Link>
                            <Link to={signedIn ? '/customer/orders/' : '/login'}>{signedIn ? 'My orders' : 'Sign in'}</Link>
                            {signedIn && <Link to="/logout">Sign out</Link>}
                            <Link to="/policy/shipping">Shipping</Link>
                            <Link to="/contact">Contact</Link>
                            {isStaff && <Link to="/admin-area/dashboard/">Admin</Link>}
                        </nav>
                    </div>
                }
            </header>
        </div>
    );
}

export default StoreHeader;
