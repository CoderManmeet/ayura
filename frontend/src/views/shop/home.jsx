import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

import Addon from '../plugin/Addon';
import { formatINR } from '../../utils/money';
import { STORE_NAME, TAGLINE } from '../../utils/constants';
import { Photo, ProductCard, ProductRail, RailSkeleton, WakingNotice } from '../ui/kit';
import { SIZES } from '../../utils/image';
import { useCachedApi } from '../../utils/apiCache';

// Home page. Every product, price and photo shown here comes from the store's
// own catalogue; nothing is hard-coded.
function Home() {
    // The catalogue was already requested in main.jsx, and the previous visit's answer is
    // painted straight away while a fresh one is fetched. See utils/apiCache.js.
    const { data: products, loading, waking, failed } = useCachedApi('products/')
    const addon = Addon()

    useEffect(() => {
        document.title = STORE_NAME;
    }, [])

    const featured = (products || []).filter((product) => product.featured)
    const hero = featured[0] || (products || [])[0]
    const collection = (featured.length > 0 ? featured : (products || [])).slice(0, 8)

    return (
        <main>
            <section className="overflow-hidden bg-muted">
                <div className="mx-auto grid max-w-[1440px] md:grid-cols-[1.1fr_0.9fr]">
                    <div className="flex min-h-[460px] flex-col justify-center px-6 py-16 md:min-h-[600px] md:px-16 lg:px-24">
                        {/* The brand's promise is the headline: it is the one line that says what this shop is. */}
                        <h1 className="ui-hero-title max-w-2xl font-display" data-testid="hero-title">{TAGLINE}</h1>
                        <p className="mt-8 max-w-sm text-base leading-7 text-subtle">Skin, hair and body care, made fresh in small batches.</p>
                        <Link to="/shop" className="ui-btn mt-9 w-fit">Shop all <ArrowRight className="size-4" aria-hidden="true" /></Link>
                    </div>
                    <div className="relative min-h-[380px] bg-soft md:min-h-[600px]">
                        {/* The one photo on screen at the start: fetched eagerly and early, never lazily. */}
                        {hero?.image && <Photo src={hero.image} alt={hero.title} width={SIZES.hero} priority className="absolute inset-0 size-full object-cover" />}
                        {hero &&
                            <Link to={`/detail/${hero.slug}`} className="absolute bottom-8 right-8 bg-canvas/90 px-4 py-3 text-right">
                                <p className="ui-caption text-subtle">Featured</p>
                                <p className="mt-1 font-display text-2xl">{hero.title}</p>
                            </Link>
                        }
                    </div>
                </div>
            </section>

            <section className="border-b border-line bg-panel px-5 py-16 md:px-10 md:py-24">
                <div className="mx-auto max-w-[1440px]">
                    <div className="flex items-end justify-between gap-6">
                        <div>
                            <p className="ui-eyebrow mb-4">Skin, hair and body</p>
                            <h2 className="font-display text-4xl md:text-5xl">The collection.</h2>
                        </div>
                        <Link to="/shop" className="ui-link hidden ui-caption md:block">View all products</Link>
                    </div>
                    {loading && <div className="mt-12"><RailSkeleton /><WakingNotice show={waking} /></div>}
                    {failed && <p className="py-20 text-center font-display text-2xl">The collection could not be loaded. Please refresh.</p>}
                    {!loading && !failed && collection.length === 0 && <p className="py-20 text-center font-display text-2xl">The collection is being prepared.</p>}
                    {/* One row the shopper swipes through, rather than a grid: the whole
                        collection stays on one screen and the rest is an invitation to scroll. */}
                    {!loading && collection.length > 0 &&
                    <div className="mt-12" data-testid="home-products">
                        <ProductRail label="The collection">
                            {collection.map((product) => <ProductCard key={product.id} product={product} inRail />)}
                        </ProductRail>
                    </div>
                    }
                    <Link to="/shop" className="ui-btn-outline mt-10 w-full md:hidden">View all products</Link>
                </div>
            </section>

            <section className="mx-auto grid max-w-[1440px] gap-12 px-5 py-16 md:grid-cols-2 md:items-center md:px-10 md:py-28">
                <div className="relative aspect-square overflow-hidden bg-muted">
                    {(collection[1] || hero)?.image && <Photo src={(collection[1] || hero).image} alt="" width={SIZES.detail} className="size-full object-cover" />}
                </div>
                <div className="max-w-lg md:pl-8">
                    <p className="ui-eyebrow mb-6">Why we started</p>
                    <h2 className="font-display text-4xl leading-[1.08] md:text-5xl">Made the way we would make it for ourselves.</h2>
                    <p className="mt-8 text-sm leading-7 text-subtle">Everything we sell is something we use at home first. The full story is on its way.</p>
                    <Link to="/about" className="mt-8 inline-flex min-h-11 items-center gap-3 ui-caption">Our story <ArrowRight className="size-4" aria-hidden="true" /></Link>
                </div>
            </section>

            {addon?.shipping_flat_paise != null &&
                <section className="bg-ink px-5 py-14 text-canvas md:px-10">
                    <div className="mx-auto grid max-w-[1440px] gap-8 text-center md:grid-cols-3">
                        <div>
                            <p className="font-display text-2xl">Shipping {formatINR(addon.shipping_flat_paise)}</p>
                            <p className="mt-2 text-xs text-canvas/70">Free on orders of {formatINR(addon.free_shipping_threshold_paise)} or more</p>
                        </div>
                        <div>
                            <p className="font-display text-2xl">UPI, cards or cash</p>
                            <p className="mt-2 text-xs text-canvas/70">Pay online or on delivery, at the same price</p>
                        </div>
                        <div>
                            <p className="font-display text-2xl">Prices include all taxes</p>
                            <p className="mt-2 text-xs text-canvas/70">What you see is what you pay</p>
                        </div>
                    </div>
                </section>
            }
        </main>
    )
}

export default Home