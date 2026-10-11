import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import usePageTitle from '../../utils/usePageTitle';
import { GridSkeleton, PageIntro, ProductCard, WakingNotice } from '../ui/kit';
import { useCachedApi } from '../../utils/apiCache';

// The shop: every product, with search (?query=), a category filter (?category=<slug>) and
// sorting. Also serves /search.
//
// Categories can sit inside one another (Skincare › Face › Serums). Choosing a category shows
// its products and those of every category inside it (the server does that), and opens one more
// row of chips for each level below it that has sub-categories.
const SORTS = {
    featured: { label: 'Featured', compare: null },
    low: { label: 'Price: low to high', compare: (a, b) => (a.price_from_paise ?? 0) - (b.price_from_paise ?? 0) },
    high: { label: 'Price: high to low', compare: (a, b) => (b.price_from_paise ?? 0) - (a.price_from_paise ?? 0) },
};

const chipClass = (selected) => `min-h-10 border px-4 ui-caption transition-colors ${selected
    ? 'border-ink bg-ink text-canvas'
    : 'border-line-strong hover:border-ink'}`;

function Shop() {
    const [searchParams, setSearchParams] = useSearchParams();
    const query = (searchParams.get('query') || '').trim();
    const categorySlug = query ? '' : (searchParams.get('category') || '').trim();
    const [sort, setSort] = useState('featured')

    const { data: categoryData } = useCachedApi('category/');
    const categories = useMemo(() => categoryData || [], [categoryData]);
    const bySlug = useMemo(() => Object.fromEntries(categories.map((c) => [c.slug, c])), [categories]);
    const byId = useMemo(() => Object.fromEntries(categories.map((c) => [c.id, c])), [categories]);
    const childrenOf = (id) => categories.filter((c) => c.parent === id).sort((a, b) => a.title.localeCompare(b.title));
    const topLevel = childrenOf(null);

    const selected = categorySlug ? bySlug[categorySlug] : null;
    // The chosen category and the categories above it, from the top down (Skincare, Face).
    const path = useMemo(() => {
        const chain = [];
        const seen = new Set();
        let node = selected;
        while (node && !seen.has(node.id)) {
            chain.unshift(node);
            seen.add(node.id);
            node = node.parent ? byId[node.parent] : null;
        }
        return chain;
    }, [selected, byId]);
    const selectedTop = path[0] || null;
    const onPath = (category) => path.some((node) => node.id === category.id);

    usePageTitle(query ? `Search: ${query}` : (selected ? selected.title : 'Shop all'));

    // Without a search or a category this is the same request the home page made, so it is
    // already cached and the grid appears at once. A search always goes to the server.
    // See utils/apiCache.js.
    const { data: products, loading, waking, failed } = useCachedApi(
        query ? 'search/' : 'products/',
        query ? { params: { query } } : (categorySlug ? { params: { category: categorySlug } } : undefined),
    )

    const visible = useMemo(() => {
        const list = [...(products || [])];
        const compare = SORTS[sort].compare;
        return compare ? list.sort(compare) : list;
    }, [products, sort])

    const choose = (slug) => {
        const next = new URLSearchParams(searchParams);
        if (slug) next.set('category', slug); else next.delete('category');
        setSearchParams(next);
    };

    const title = query ? `Results for "${query}".` : (selected ? `${selected.title}.` : 'Everything we make.');

    return (
        <main>
            <PageIntro eyebrow={query ? 'Search' : 'The collection'} title={title} />
            <div className="mx-auto max-w-[1440px] px-5 py-10 md:px-10 md:py-16">
                {!query && topLevel.length > 0 &&
                    <nav aria-label="Categories" className="mb-8" data-testid="category-filter">
                        <div className="flex flex-wrap gap-2">
                            <button type="button" onClick={() => choose('')} aria-pressed={!categorySlug} className={chipClass(!categorySlug)}>All</button>
                            {topLevel.map((category) => (
                                <button key={category.id} type="button" onClick={() => choose(category.slug)} data-testid="category-chip"
                                    aria-pressed={selectedTop?.id === category.id} className={chipClass(selectedTop?.id === category.id)}>
                                    {category.title}
                                </button>
                            ))}
                        </div>
                        {path.map((parent) => {
                            const children = childrenOf(parent.id);
                            if (children.length === 0) return null;
                            return (
                                <div key={parent.id} className="mt-3 flex flex-wrap gap-2" data-testid="subcategory-filter">
                                    <button type="button" onClick={() => choose(parent.slug)} aria-pressed={selected?.id === parent.id}
                                        className={chipClass(selected?.id === parent.id)}>All {parent.title.toLowerCase()}</button>
                                    {children.map((category) => (
                                        <button key={category.id} type="button" onClick={() => choose(category.slug)} data-testid="subcategory-chip"
                                            aria-pressed={onPath(category)} className={chipClass(onPath(category))}>
                                            {category.title}
                                        </button>
                                    ))}
                                </div>
                            );
                        })}
                    </nav>
                }
                <div className="mb-8 flex items-center justify-between gap-4 ui-caption text-subtle">
                    <span data-testid="shop-count">{loading ? '' : `${visible.length} ${visible.length === 1 ? 'product' : 'products'}`}</span>
                    <label className="flex items-center gap-2">
                        <span>Sort</span>
                        <select value={sort} onChange={(event) => setSort(event.target.value)} className="border-b border-line-strong bg-transparent py-2 ui-caption outline-none">
                            {Object.entries(SORTS).map(([value, { label }]) => <option key={value} value={value}>{label}</option>)}
                        </select>
                    </label>
                </div>
                {loading && <><GridSkeleton /><WakingNotice show={waking} /></>}
                {failed && <p className="py-20 text-center font-display text-2xl">The products could not be loaded. Please refresh.</p>}
                {!loading && !failed && visible.length === 0 && <p className="py-20 text-center font-display text-2xl">No products found.</p>}
                {!loading &&
                    <div className="grid gap-x-4 gap-y-12 sm:grid-cols-2 lg:grid-cols-4" data-testid="shop-products">
                        {visible.map((product) => <ProductCard key={product.id} product={product} />)}
                    </div>
                }
            </div>
        </main>
    )
}

export default Shop
