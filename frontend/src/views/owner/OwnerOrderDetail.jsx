import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import moment from 'moment';
import Swal from 'sweetalert2';

import apiInstance from '../../utils/axios';
import Sidebar from '../vendor/Sidebar';
import { formatINR } from '../../utils/money';

// One order, with the actions the owner takes on it. Every button posts to the server, which
// runs the change through the order state machine: it refuses anything that is not allowed
// (for example shipping an unconfirmed Cash on Delivery order) and records who did what.
//
// Phase D adds the two things to check before the parcel is sealed:
//   * Packing: which batch each line is going out from, with an expired or undated one
//     flagged. Flags never block the dispatch (ROADMAP Y12); the owner decides.
//   * Gift samples: what free samples go in. The customer is NEVER told, here or anywhere
//     else (ROADMAP Y19), so none of this appears on their order page or in any email.
const DELIVERY_STEPS = ['On Hold', 'Shipping Processing', 'Shipped', 'Arrived', 'Delivered'];

const messageOf = (error) => error?.response?.data?.message || 'Please try again.';

// --------------------------------------------------------------------------- packing

function BatchLine({ batch, onSaved }) {
    const [bestBefore, setBestBefore] = useState(batch.best_before || '')
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')

    const save = async () => {
        setBusy(true)
        setError('')
        try {
            await apiInstance.patch(`owner/batches/${batch.id}/`, { best_before: bestBefore || null })
            await onSaved()
        } catch (err) {
            setError(messageOf(err))
        } finally {
            setBusy(false)
        }
    }

    return (
        <tr data-testid="packing-batch" data-batch={batch.batch_code}>
            <td>{batch.batch_code}</td>
            <td>{batch.quantity}</td>
            <td>
                <div className="d-flex gap-2 align-items-center">
                    <input type="date" className="form-control" value={bestBefore}
                        onChange={(event) => setBestBefore(event.target.value)}
                        aria-label={`Use by for batch ${batch.batch_code}`} data-testid="packing-use-by" />
                    {(bestBefore || '') !== (batch.best_before || '') &&
                        <button type="button" className="btn btn-sm btn-primary" disabled={busy} onClick={save}>Save</button>
                    }
                </div>
                {error && <div className="text-danger" role="alert"><small>{error}</small></div>}
            </td>
            <td>
                {batch.expired && <span className="badge bg-danger" data-testid="batch-expired">Expired</span>}
                {batch.undated && <span className="badge bg-warning text-dark" data-testid="batch-undated">No use-by date</span>}
                {!batch.expired && !batch.undated && <span className="text-subtle">OK</span>}
            </td>
        </tr>
    )
}

function Packing({ dispatch, reload }) {
    if (!dispatch) return null
    return (
        <div className="card mb-4" data-testid="packing-panel">
            <div className="card-body">
                <h6>Packing</h6>
                {dispatch.any_expired &&
                    <div className="alert alert-danger" data-testid="packing-expired-warning">
                        <b>This order has expired stock allocated to it.</b> Check the jars before you pack them.
                        Nothing is stopping you sending it; the decision is yours.
                    </div>
                }
                {dispatch.any_undated && !dispatch.any_expired &&
                    <div className="alert alert-info" data-testid="packing-undated-warning">
                        Some of this stock has no use-by date recorded. Add it below before the parcel goes out.
                    </div>
                }
                {dispatch.lines.map((line) => (
                    <div className="mb-3" key={line.order_item_id} data-testid="packing-line">
                        <p className="mb-1"><b>{line.title}</b>{line.variant ? ` · ${line.variant}` : ''} · {line.qty} unit(s)</p>
                        {line.batches.length === 0
                            ? <p className="text-subtle"><small>No batch is allocated to this line yet.</small></p>
                            : <div className="table-responsive">
                                <table className="table">
                                    <thead><tr><th>Batch</th><th>From this batch</th><th>Use by</th><th>Check</th></tr></thead>
                                    <tbody>
                                        {line.batches.map((batch) => (
                                            <BatchLine key={`${batch.id}-${batch.best_before}`} batch={batch} onSaved={reload} />
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        }
                    </div>
                ))}
            </div>
        </div>
    )
}

// --------------------------------------------------------------------------- gift samples

function Samples({ dispatch, oid, reload }) {
    const [variantId, setVariantId] = useState('')
    const [qty, setQty] = useState('1')
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')

    if (!dispatch) return null

    const act = async (payload) => {
        setBusy(true)
        setError('')
        try {
            await apiInstance.post(`owner/orders/${oid}/samples/`, payload)
            await reload()
            setVariantId('')
            setQty('1')
        } catch (err) {
            setError(messageOf(err))
        } finally {
            setBusy(false)
        }
    }

    const decided = dispatch.sample_decision
    return (
        <div className="card mb-4" data-testid="samples-panel">
            <div className="card-body">
                <h6>Gift samples</h6>
                <p className="text-subtle"><small>
                    Free samples to put in this parcel. They cost the customer nothing and never change
                    the order total. <b>The customer is never told</b>: samples appear nowhere on their order
                    page and in no email, so opening the box is a surprise.
                </small></p>

                {decided === 'UNDECIDED' &&
                    <div className="alert alert-info" data-testid="samples-undecided">Not decided yet for this order.</div>
                }
                {decided === 'NONE' &&
                    <p data-testid="samples-none">No samples with this order.</p>
                }

                {dispatch.samples.length > 0 &&
                    <ul className="list-group mb-3" data-testid="samples-list">
                        {dispatch.samples.map((sample) => (
                            <li className="list-group-item d-flex justify-content-between align-items-center" key={sample.id}
                                data-testid="sample-item" data-sku={sample.sku}>
                                <span>{sample.qty} &times; {sample.name} <small className="text-subtle">({sample.sku})</small></span>
                                <button type="button" className="btn btn-sm btn-outline-secondary" disabled={busy}
                                    onClick={() => act({ action: 'remove', sample_id: sample.id })} data-testid="sample-remove">
                                    Remove
                                </button>
                            </li>
                        ))}
                    </ul>
                }

                {error && <div className="alert alert-danger" role="alert" data-testid="samples-error">{error}</div>}

                {dispatch.sample_options.length === 0
                    ? <p className="text-subtle"><small>
                        No sample sizes exist yet. Open a product's "Sizes &amp; stock" screen, add a small size
                        and tick "Sample", then give it stock.
                    </small></p>
                    : <div className="row g-2 align-items-end">
                        <div className="col-md-6">
                            <label className="form-label" htmlFor="sampleVariant">Add a sample</label>
                            <select id="sampleVariant" className="form-select" value={variantId}
                                onChange={(event) => setVariantId(event.target.value)} data-testid="sample-select">
                                <option value="">- Choose -</option>
                                {dispatch.sample_options.map((option) => (
                                    <option key={option.variant_id} value={option.variant_id} disabled={option.available < 1}>
                                        {option.name} ({option.available} left)
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="col-md-2">
                            <label className="form-label" htmlFor="sampleQty">Qty</label>
                            <input id="sampleQty" className="form-control" inputMode="numeric" value={qty}
                                onChange={(event) => setQty(event.target.value)} data-testid="sample-qty" />
                        </div>
                        <div className="col-md-4 d-flex gap-2">
                            <button type="button" className="btn btn-primary" disabled={busy || !variantId}
                                onClick={() => act({ action: 'add', variant_id: variantId, qty })} data-testid="sample-add">
                                Add to parcel
                            </button>
                            {dispatch.samples.length === 0 && decided !== 'NONE' &&
                                <button type="button" className="btn btn-outline-secondary" disabled={busy}
                                    onClick={() => act({ action: 'none' })} data-testid="sample-none">
                                    No samples
                                </button>
                            }
                        </div>
                    </div>
                }
            </div>
        </div>
    )
}

// --------------------------------------------------------------------------- the page

function OwnerOrderDetail() {
    const { oid } = useParams()
    const [order, setOrder] = useState(null)
    const [dispatch, setDispatch] = useState(null)
    const [couriers, setCouriers] = useState([])
    const [trackingId, setTrackingId] = useState("")
    const [courierId, setCourierId] = useState("")
    const [busy, setBusy] = useState(false)

    const loadDispatch = useCallback(() => {
        return apiInstance.get(`owner/orders/${oid}/dispatch/`)
            .then((res) => setDispatch(res.data))
            .catch(() => setDispatch(null))
    }, [oid])

    useEffect(() => {
        apiInstance.get(`owner/orders/${oid}/`).then((res) => setOrder(res.data))
        apiInstance.get('vendor/couriers/').then((res) => setCouriers(res.data)).catch(() => setCouriers([]))
        loadDispatch()
    }, [oid, loadDispatch])

    const act = async (payload, confirmText) => {
        if (confirmText) {
            const answer = await Swal.fire({ icon: 'question', title: confirmText, showCancelButton: true, confirmButtonText: 'Yes' })
            if (!answer.isConfirmed) return
        }
        setBusy(true)
        try {
            const response = await apiInstance.post(`owner/orders/${oid}/action/`, payload)
            setOrder(response.data)
            await loadDispatch()
        } catch (error) {
            Swal.fire({ icon: 'error', title: 'Not done', text: messageOf(error) })
        } finally {
            setBusy(false)
        }
    }

    if (order === null) {
        return <div className="container text-center mt-5"><i className='fas fa-spinner fa-spin'></i> Loading...</div>
    }

    const items = order.orderitem || []
    const isCod = order.payment_method === 'COD'
    const cancelled = order.order_status === 'Cancelled'
    const furthest = items.reduce((max, item) => Math.max(max, DELIVERY_STEPS.indexOf(item.delivery_status)), 0)
    const delivered = items.length > 0 && items.every((item) => item.delivery_status === 'Delivered')
    const canShip = !cancelled && ['paid', 'pending'].includes(order.payment_status)

    const setDelivery = (status) => act({
        action: 'set_delivery', status,
        ...(trackingId ? { tracking_id: trackingId } : {}),
        ...(courierId ? { courier_id: courierId } : {}),
    })

    return (
        <div className="container-fluid" id="main">
            <div className="row row-offcanvas row-offcanvas-left h-100">
                <Sidebar />
                <div className="col-md-9 col-lg-10 main mt-4" data-testid="owner-order">
                    <p><Link to="/admin-area/owner/orders/">&larr; All orders</Link></p>
                    <h4>Order #{order.oid}</h4>
                    <p className="text-muted">{moment(order.date).format('DD MMM YYYY, h:mm a')}</p>

                    {order.needs_attention &&
                        <div className="alert alert-danger d-flex justify-content-between align-items-center">
                            <span><b>Needs attention:</b> {order.needs_attention}</span>
                            <button className="btn btn-outline-danger btn-sm" disabled={busy} onClick={() => act({ action: 'clear_attention' }, 'Has this been dealt with?')}>Mark as dealt with</button>
                        </div>
                    }

                    <div className="row">
                        <div className="col-lg-6 mb-3">
                            <div className="card h-100"><div className="card-body">
                                <h6>Customer</h6>
                                <p className="mb-1">{order.full_name}</p>
                                <p className="mb-1">{order.email} · {order.mobile}</p>
                                <p className="mb-0">{order.address}, {order.city}, {order.state} {order.pincode}</p>
                            </div></div>
                        </div>
                        <div className="col-lg-6 mb-3">
                            <div className="card h-100"><div className="card-body">
                                <h6>Payment</h6>
                                <p className="mb-1">{isCod ? 'Cash on Delivery' : 'Online (Razorpay)'} · <b data-testid="owner-payment-status">{order.payment_status}</b></p>
                                <p className="mb-1">Order status: <b data-testid="owner-order-status">{order.order_status}</b></p>
                                {isCod &&
                                    <p className="mb-1" data-testid="owner-cod-state">
                                        {order.cod_confirmed_at
                                            ? <>Confirmed with customer on {moment(order.cod_confirmed_at).format('DD MMM YYYY, h:mm a')}</>
                                            : <span className="text-danger">Not confirmed with the customer yet</span>}
                                    </p>
                                }
                                <p className="mb-0">Total: <b>{formatINR(order.total_paise)}</b>{order.saved_paise > 0 ? ` (discount ${formatINR(order.saved_paise)}${order.coupon_code ? `, ${order.coupon_code}` : ''})` : ''}</p>
                                {order.cod_fee_paise > 0 &&
                                    <p className="mb-0" data-testid="owner-cod-fee">Includes Cash on Delivery fee {formatINR(order.cod_fee_paise)}</p>
                                }
                            </div></div>
                        </div>
                    </div>

                    <table className="table">
                        <thead><tr><th>Item</th><th>Qty</th><th>Amount</th><th>Delivery</th><th>Tracking</th></tr></thead>
                        <tbody>
                            {items.map((item) => (
                                <tr key={item.id}>
                                    <td>{item.product?.title}{item.variant?.name && item.variant.name !== 'Default' ? ` (${item.variant.name})` : ''}</td>
                                    <td>{item.qty}</td>
                                    <td>{formatINR(item.total_paise)}</td>
                                    <td data-testid="owner-delivery-status">{item.delivery_status}</td>
                                    <td>{item.tracking_id || '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    {!cancelled && <Packing dispatch={dispatch} reload={loadDispatch} />}
                    {!cancelled && <Samples dispatch={dispatch} oid={oid} reload={loadDispatch} />}

                    <h6 className="mt-4">Actions</h6>
                    <div className="d-flex flex-wrap gap-2 mb-3">
                        {isCod && !order.cod_confirmed_at && !cancelled &&
                            <button className="btn btn-warning" disabled={busy} onClick={() => act({ action: 'confirm_cod' }, 'Have you confirmed this order with the customer by phone or WhatsApp?')}>Confirm COD</button>
                        }
                        {isCod && delivered && order.payment_status === 'pending' &&
                            <button className="btn btn-success" disabled={busy} onClick={() => act({ action: 'mark_paid' }, 'Has the cash been collected?')}>Mark cash collected</button>
                        }
                        {!cancelled &&
                            <button className="btn btn-outline-danger" disabled={busy} onClick={() => act({ action: 'cancel' }, 'Cancel this order and return its stock?')}>Cancel order</button>
                        }
                        {cancelled && order.payment_status === 'paid' &&
                            <button className="btn btn-outline-secondary" disabled={busy} onClick={() => act({ action: 'record_refund' }, 'Have you issued the refund in the Razorpay dashboard?')}>Record refund as issued</button>
                        }
                    </div>

                    {canShip && !delivered &&
                        <div className="card mb-4"><div className="card-body">
                            <h6>Shipping</h6>
                            <div className="row g-2 mb-3">
                                <div className="col-md-4">
                                    <label className="form-label" htmlFor="ownerCourier">Courier</label>
                                    <select id="ownerCourier" className="form-select" value={courierId} onChange={(e) => setCourierId(e.target.value)}>
                                        <option value="">(none)</option>
                                        {couriers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                                    </select>
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label" htmlFor="ownerTracking">Tracking number</label>
                                    <input id="ownerTracking" className="form-control" value={trackingId} onChange={(e) => setTrackingId(e.target.value)} />
                                </div>
                            </div>
                            <div className="d-flex flex-wrap gap-2">
                                {DELIVERY_STEPS.slice(1).map((step, index) => (
                                    index + 1 > furthest &&
                                    <button key={step} className="btn btn-primary" disabled={busy} onClick={() => setDelivery(step)}>
                                        Mark {step === 'Shipping Processing' ? 'as packing' : step.toLowerCase()}
                                    </button>
                                ))}
                            </div>
                            <p className="text-muted mt-2 mb-0"><small>Stock leaves the inventory ledger the first time the order is marked as packing or shipped. The customer is emailed when it is shipped.</small></p>
                        </div></div>
                    }
                </div>
            </div>
        </div>
    )
}

export default OwnerOrderDetail
