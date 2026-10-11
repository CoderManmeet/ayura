import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import moment from 'moment';
import "chart.js/auto";
import { Line } from "react-chartjs-2";

import apiInstance from '../../utils/axios';
import UserData from '../plugin/UserData';
import Sidebar from './Sidebar';
import { formatINR, formatRupees } from '../../utils/money';
import { Photo } from '../ui/kit';

// Admin home: the few numbers worth seeing at a glance, what needs attention right now, and
// the most recent orders and products.
function StatCard({ label, value, note, to }) {
    const body = (
        <>
            <p className="ui-caption text-subtle">{label}</p>
            <p className="mt-3 font-display text-4xl leading-none">{value}</p>
            {note && <p className="mt-2 text-xs text-subtle">{note}</p>}
        </>
    );
    return to
        ? <Link to={to} className="block border border-line bg-white p-5 transition-colors hover:border-line-strong">{body}</Link>
        : <div className="border border-line bg-white p-5">{body}</div>;
}

// The chart's colours come from the theme (src/theme/brand.css), read once the page is drawn,
// so the dashboard follows the brand without naming a colour here.
const themeColour = (name, fallback) => {
    if (typeof window === 'undefined') return fallback;
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
};

const chartLine = () => {
    const accent = themeColour('--color-accent', '#555555');
    return {
        fill: true,
        // About 12% opacity: a hex colour with an alpha byte, which every canvas understands.
        backgroundColor: /^#[0-9a-f]{6}$/i.test(accent) ? `${accent}1f` : 'rgba(0, 0, 0, 0.06)',
        borderColor: accent,
        pointBackgroundColor: accent,
        tension: 0.35,
    };
};

const chartOptions = () => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y: { beginAtZero: true, grid: { color: themeColour('--color-line', 'rgba(0,0,0,0.08)') }, ticks: { font: { size: 10 }, precision: 0 } },
    },
});

function Dashboard() {
    const [stats, setStats] = useState(null)
    const [products, setProducts] = useState(null)
    const [orders, setOrders] = useState(null)
    const [orderChartData, setOrderChartData] = useState(null)

    const axios = apiInstance
    const userData = UserData()

    useEffect(() => {
        const vendorId = userData?.vendor_id;
        if (!vendorId) return;
        const get = (url, set) => axios.get(url).then((res) => set(res.data)).catch((error) => console.error(url, error));
        get(`vendor/stats/${vendorId}/`, (data) => setStats(data[0]));
        get(`vendor/products/${vendorId}/`, setProducts);
        get('owner/orders/', setOrders);
        get(`vendor-orders-report-chart/${vendorId}/`, setOrderChartData);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const recentOrders = (orders || []).slice(0, 5);
    const needsAttention = (orders || []).filter((o) => o.needs_attention);
    const awaitingCod = (orders || []).filter(
        (o) => o.payment_method === 'COD' && !o.cod_confirmed_at && o.order_status !== 'Cancelled');
    const toShip = (orders || []).filter((o) => (o.orderitem || []).some(
        (item) => ['On Hold', 'Shipping Processing'].includes(item.delivery_status))
        && ['paid', 'pending'].includes(o.payment_status) && o.order_status !== 'Cancelled');
    const soldOut = (products || []).filter((p) => p.available_qty === 0);

    const chart = {
        labels: (orderChartData || []).map((row) => moment(row.month, 'M').format('MMM')),
        datasets: [{ label: 'Orders', data: (orderChartData || []).map((row) => row.orders), ...chartLine() }],
    };

    const task = (count, label, to) => count > 0 && (
        <Link to={to} className="flex items-center justify-between gap-4 border border-line bg-white px-4 py-3 text-sm hover:border-line-strong">
            <span>{label}</span>
            <span className="bg-accent px-2 py-1 text-[10px] text-white">{count}</span>
        </Link>
    );

    const anyTask = needsAttention.length + awaitingCod.length + toShip.length + soldOut.length > 0;

    return (
        <div className="ui-admin">
            <div className="flex flex-col md:flex-row">
                <Sidebar />
                <main className="min-w-0 flex-1 px-5 py-8 md:px-8" data-testid="admin-dashboard">
                    <p className="ui-eyebrow mb-2">Admin</p>
                    <h1 className="mb-8">Your shop today.</h1>

                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                        <StatCard label="Products" value={stats?.products ?? '—'}
                                  note={soldOut.length > 0 ? `${soldOut.length} sold out` : 'all in stock'}
                                  to="/admin-area/products/" />
                        <StatCard label="Orders" value={stats?.orders ?? '—'} note="paid and placed" to="/admin-area/owner/orders/" />
                        <StatCard label="Revenue" value={stats ? formatRupees(stats.revenue || 0) : '—'} note="all time" to="/admin-area/earning/" />
                        <StatCard label="Needs you" value={needsAttention.length + awaitingCod.length + toShip.length}
                                  note="orders waiting on an action" to="/admin-area/owner/orders/" />
                    </div>

                    <section className="mt-10">
                        <h2 className="mb-4">What needs doing</h2>
                        {!anyTask && orders !== null &&
                            <p className="border border-line bg-white px-4 py-6 text-center text-sm text-subtle">
                                Nothing waiting. Every order is handled.
                            </p>
                        }
                        <div className="grid gap-3 sm:grid-cols-2">
                            {task(needsAttention.length, 'Orders flagged for attention', '/admin-area/owner/orders/')}
                            {task(awaitingCod.length, 'Cash on Delivery orders to confirm', '/admin-area/owner/orders/')}
                            {task(toShip.length, 'Orders to pack and ship', '/admin-area/owner/orders/')}
                            {task(soldOut.length, 'Products sold out', '/admin-area/products/')}
                        </div>
                    </section>

                    <section className="mt-10 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
                        <div className="border border-line bg-white p-5">
                            <h2 className="mb-1">Orders by month</h2>
                            <p className="mb-4 text-xs text-subtle">Paid orders, this year</p>
                            <div className="h-64">
                                {orderChartData === null
                                    ? <p className="pt-20 text-center text-sm text-subtle">Loading...</p>
                                    : <Line data={chart} options={chartOptions()} />
                                }
                            </div>
                        </div>

                        <div className="border border-line bg-white p-5">
                            <div className="mb-4 flex items-center justify-between gap-3">
                                <h2 className="mb-0">Latest orders</h2>
                                <Link to="/admin-area/owner/orders/" className="ui-caption text-accent">All orders</Link>
                            </div>
                            {orders === null && <p className="text-sm text-subtle">Loading...</p>}
                            {orders !== null && recentOrders.length === 0 && <p className="text-sm text-subtle">No orders yet.</p>}
                            <div className="flex flex-col">
                                {recentOrders.map((order) => (
                                    <Link to={`/admin-area/owner/orders/${order.oid}/`} key={order.oid}
                                          className="flex items-center justify-between gap-3 border-b border-line py-3 last:border-0">
                                        <span className="min-w-0">
                                            <span className="block truncate text-sm">{order.full_name}</span>
                                            <span className="block text-[11px] text-subtle">
                                                #{order.oid} · {moment(order.date).format('DD MMM')} · {order.payment_method === 'COD' ? 'COD' : 'Online'}
                                            </span>
                                        </span>
                                        <span className="shrink-0 text-sm">{formatINR(order.total_paise)}</span>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    </section>

                    <section className="mt-10">
                        <div className="mb-4 flex items-center justify-between gap-3">
                            <h2 className="mb-0">Recently added</h2>
                            <Link to="/admin-area/products/" className="ui-caption text-accent">All products</Link>
                        </div>
                        {products === null && <p className="text-sm text-subtle">Loading...</p>}
                        {products !== null && products.length === 0 &&
                            <p className="border border-line bg-white px-4 py-6 text-center text-sm text-subtle">
                                No products yet. <Link to="/admin-area/product/new/" className="ui-link">Add your first product</Link>.
                            </p>
                        }
                        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                            {(products || []).slice(0, 4).map((product) => (
                                <Link to={`/admin-area/product/update/${product.pid}/`} key={product.pid}
                                      className="border border-line bg-white hover:border-line-strong">
                                    <div className="aspect-[4/5] bg-muted">
                                        <Photo src={product.image} alt={product.title} className="size-full object-cover" />
                                    </div>
                                    <div className="p-3">
                                        <p className="truncate text-sm">{product.title}</p>
                                        <p className="mt-1 text-[11px] text-subtle">
                                            {formatRupees(product.price)} · {product.available_qty > 0 ? `${product.available_qty} in stock` : 'sold out'}
                                        </p>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </section>
                </main>
            </div>
        </div>
    )
}

export default Dashboard