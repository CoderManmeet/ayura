import { useEffect, useState } from 'react';

import apiInstance from '../../utils/axios';
import Sidebar from '../vendor/Sidebar';

// Stock that needs attention, and the recall lookup (Ayura phase D).
//
//   * Expired: past its use-by date and still on the shelf. Write it off.
//   * Due soon: within the store's alert window.
//   * No use-by date: the owner never entered one. Nothing is blocked (ROADMAP Y12); it is
//     listed so the date can be added before the stock goes out.
//
// Writing stock off is a movement in the stock ledger, never an edit, so the batch keeps its
// whole history. Stock already held for a customer's order cannot be written off.
//
// "Find a batch" answers the recall question: who received stock from this batch?

const messageOf = (error) => error?.response?.data?.message || 'Something went wrong. Please try again.';

function WriteOff({ batch, onDone }) {
    const [open, setOpen] = useState(false)
    const [quantity, setQuantity] = useState('')
    const [reason, setReason] = useState('')
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')

    const free = Math.max(batch.on_hand - batch.held, 0)

    const submit = async (event) => {
        event.preventDefault()
        setBusy(true)
        setError('')
        try {
            await apiInstance.post(`owner/batches/${batch.id}/write-off/`, { quantity, reason })
            setOpen(false)
            setQuantity('')
            setReason('')
            onDone()
        } catch (err) {
            setError(messageOf(err))
        } finally {
            setBusy(false)
        }
    }

    if (!open) {
        return (
            <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => setOpen(true)}
                disabled={free < 1} title={free < 1 ? 'Every unit left is held for an order' : undefined}
                data-testid="write-off-open">
                Write off
            </button>
        )
    }
    return (
        <form onSubmit={submit} className="d-flex flex-wrap gap-2 align-items-start" data-testid="write-off-form">
            <div>
                <input className="form-control" inputMode="numeric" value={quantity} placeholder={`up to ${free}`}
                    onChange={(event) => setQuantity(event.target.value)} aria-label="Quantity to write off"
                    data-testid="write-off-quantity" />
            </div>
            <div className="flex-grow-1">
                <input className="form-control" value={reason} placeholder="Why (kept with the stock history)"
                    onChange={(event) => setReason(event.target.value)} aria-label="Reason" data-testid="write-off-reason" />
            </div>
            <button type="submit" className="btn btn-sm btn-danger" disabled={busy} data-testid="write-off-confirm">
                {busy ? 'Writing off...' : 'Confirm'}
            </button>
            <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setOpen(false)}>Cancel</button>
            {error && <div className="text-danger w-100" role="alert"><small>{error}</small></div>}
        </form>
    )
}

function BatchTable({ rows, kind, onDone }) {
    if (rows.length === 0) {
        return <p className="text-subtle"><small>Nothing here.</small></p>
    }
    return (
        <div className="table-responsive">
            <table className="table">
                <thead className="table-dark">
                    <tr><th>Batch</th><th>Product</th><th>Use by</th><th>On hand</th><th>Held</th><th>Actions</th></tr>
                </thead>
                <tbody>
                    {rows.map((batch) => (
                        <tr key={batch.id} data-testid={`${kind}-row`} data-batch={batch.batch_code}>
                            <td>{batch.batch_code}</td>
                            <td>{batch.product}<div className="text-subtle"><small>{batch.variant}</small></div></td>
                            <td>
                                {batch.best_before || <span className="text-subtle">Not recorded</span>}
                                {batch.expired && <span className="badge bg-danger ms-2">Expired</span>}
                            </td>
                            <td>{batch.on_hand}</td>
                            <td>{batch.held}</td>
                            <td><WriteOff batch={batch} onDone={onDone} /></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

function BatchLookup() {
    const [code, setCode] = useState('')
    const [result, setResult] = useState(null)
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')

    const search = async (event) => {
        event.preventDefault()
        setBusy(true)
        setError('')
        setResult(null)
        try {
            const res = await apiInstance.get('owner/batch-lookup/', { params: { code } })
            setResult(res.data)
        } catch (err) {
            setError(messageOf(err))
        } finally {
            setBusy(false)
        }
    }

    return (
        <div className="card mb-4" data-testid="batch-lookup">
            <div className="card-body">
                <h5 className="card-title">Find a batch</h5>
                <p className="text-subtle"><small>
                    Type a batch code to see every order that received stock from it, including orders
                    packed but not yet sent. This is what you need if a batch ever has to be recalled.
                </small></p>
                <form onSubmit={search} className="d-flex flex-wrap gap-2 mb-3">
                    <input className="form-control" style={{ maxWidth: '22rem' }} value={code} placeholder="Batch code"
                        onChange={(event) => setCode(event.target.value)} aria-label="Batch code" data-testid="lookup-code" />
                    <button type="submit" className="btn btn-primary" disabled={busy} data-testid="lookup-go">
                        {busy ? 'Looking...' : 'Look up'}
                    </button>
                </form>
                {error && <div className="alert alert-danger" role="alert">{error}</div>}
                {result && result.found === false &&
                    <p data-testid="lookup-none">{result.message || 'No batch with that code.'}</p>
                }
                {result && result.found &&
                    <>
                        <p className="mb-2">
                            <b>{result.batch.batch_code}</b> · {result.batch.product} {result.batch.variant}
                            {' · '}use by {result.batch.best_before || 'not recorded'}
                            {result.batch.expired && <span className="badge bg-danger ms-2">Expired</span>}
                        </p>
                        {result.orders.length === 0 && <p data-testid="lookup-empty">No order has received stock from this batch.</p>}
                        {result.orders.length > 0 &&
                            <div className="table-responsive">
                                <table className="table">
                                    <thead className="table-dark"><tr><th>Order</th><th>Customer</th><th>Units</th><th>Sent</th><th>Status</th></tr></thead>
                                    <tbody>
                                        {result.orders.map((row) => (
                                            <tr key={row.oid} data-testid="lookup-order">
                                                <td><a href={`/admin-area/owner/orders/${row.oid}/`}>#{row.oid}</a></td>
                                                <td>{row.full_name}</td>
                                                <td>{row.quantity}{row.sample_only && <span className="badge bg-secondary ms-2">Sample only</span>}</td>
                                                <td>{row.dispatched ? 'Yes' : 'Not yet'}</td>
                                                <td>{row.order_status} · {row.payment_status}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        }
                    </>
                }
            </div>
        </div>
    )
}

function OwnerExpiry() {
    const [data, setData] = useState(null)
    const [failed, setFailed] = useState('')

    const load = () => apiInstance.get('owner/expiry/').then((res) => setData(res.data))
        .catch((error) => setFailed(messageOf(error)))

    useEffect(() => { load() }, [])

    return (
        <div className="container-fluid" id="main">
            <div className="row row-offcanvas row-offcanvas-left h-100">
                <Sidebar />
                <div className="col-md-9 col-lg-10 main mt-4" data-testid="owner-expiry">
                    <h4>Stock &amp; expiry</h4>
                    {failed && <div className="alert alert-danger" role="alert">{failed}</div>}
                    {data === null && !failed && <p>Loading...</p>}
                    {data &&
                        <>
                            <div className="card mb-4"><div className="card-body">
                                <h5 className="card-title">Expired, still on the shelf</h5>
                                <p className="text-subtle"><small>
                                    None of this can be sold: expired stock is never put in an order. Write it off so
                                    your stock figures match what is really there.
                                </small></p>
                                <BatchTable rows={data.expired} kind="expired" onDone={load} />
                            </div></div>

                            <div className="card mb-4"><div className="card-body">
                                <h5 className="card-title">Due soon</h5>
                                <p className="text-subtle"><small>Still sells normally. Use it first, or plan a discount.</small></p>
                                <BatchTable rows={data.expiring_soon} kind="soon" onDone={load} />
                            </div></div>

                            <div className="card mb-4"><div className="card-body">
                                <h5 className="card-title">No use-by date recorded</h5>
                                <p className="text-subtle"><small>
                                    This stock sells normally. Add the date on the product's "Sizes &amp; stock" screen,
                                    or on the order before you pack it.
                                </small></p>
                                <BatchTable rows={data.undated} kind="undated" onDone={load} />
                            </div></div>

                            <BatchLookup />
                        </>
                    }
                </div>
            </div>
        </div>
    )
}

export default OwnerExpiry
