import { useEffect, useState } from 'react';

import apiInstance from '../../utils/axios';
import Sidebar from '../vendor/Sidebar';

// The kit builder (Ayura phase E).
//
// A kit is one item on the shelf made out of other sizes: "Face routine: cleanser + serum".
// It holds no stock of its own. How many kits you can sell is decided by the scarcest thing
// inside it, and selling one takes stock off every component.
//
// The kit's PRICE is whatever you set on the kit size itself, on the product's "Sizes & stock"
// screen. It is never added up from the parts (ROADMAP Z7), so a kit can cost less than buying
// everything separately — which is usually the point.
//
// A kit never contains another kit, and never contains a sample: a sample is a gift, not
// something sold inside a box.

const messageOf = (error) => error?.response?.data?.message || 'Something went wrong. Please try again.';

function AddPart({ kit, candidates, onDone }) {
    const [variantId, setVariantId] = useState('')
    const [qty, setQty] = useState('1')
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')

    const inside = new Set(kit.components.map((part) => part.component_variant_id))
    const choices = candidates.filter((option) => !inside.has(option.variant_id))

    const submit = async (event) => {
        event.preventDefault()
        setBusy(true)
        setError('')
        try {
            await apiInstance.post(`owner/kits/${kit.variant_id}/components/`,
                { component_variant_id: variantId, qty })
            setVariantId('')
            setQty('1')
            onDone()
        } catch (err) {
            setError(messageOf(err))
        } finally {
            setBusy(false)
        }
    }

    if (choices.length === 0) {
        return (
            <p className="text-subtle"><small>
                Every other size is already in this kit. Add a new size on a product's
                "Sizes &amp; stock" screen first.
            </small></p>
        )
    }

    return (
        <form onSubmit={submit} className="d-flex flex-wrap gap-2 align-items-start"
            data-testid="kit-add-form" data-kit={kit.sku}>
            <div className="flex-grow-1" style={{ minWidth: '18rem' }}>
                <select className="form-select" value={variantId} aria-label="Size to put in this kit"
                    onChange={(event) => setVariantId(event.target.value)} data-testid="kit-part-select">
                    <option value="">Choose a size...</option>
                    {choices.map((option) => (
                        <option key={option.variant_id} value={option.variant_id}>
                            {option.name} ({option.available} in stock)
                        </option>
                    ))}
                </select>
            </div>
            <div style={{ maxWidth: '7rem' }}>
                <input className="form-control" inputMode="numeric" value={qty} aria-label="How many per kit"
                    onChange={(event) => setQty(event.target.value)} data-testid="kit-part-qty" />
            </div>
            <button type="submit" className="btn btn-primary" disabled={busy || !variantId} data-testid="kit-part-add">
                {busy ? 'Adding...' : 'Add to kit'}
            </button>
            {error && <div className="text-danger w-100" role="alert" data-testid="kit-error"><small>{error}</small></div>}
        </form>
    )
}

function PartRow({ part, onDone }) {
    const [qty, setQty] = useState(String(part.qty))
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')

    const save = async () => {
        setBusy(true)
        setError('')
        try {
            await apiInstance.patch(`owner/kit-components/${part.id}/`, { qty })
            onDone()
        } catch (err) {
            setError(messageOf(err))
        } finally {
            setBusy(false)
        }
    }

    const remove = async () => {
        setBusy(true)
        setError('')
        try {
            await apiInstance.delete(`owner/kit-components/${part.id}/`)
            onDone()
        } catch (err) {
            setError(messageOf(err))
            setBusy(false)
        }
    }

    return (
        <tr data-testid="kit-part" data-sku={part.sku}>
            <td>
                {part.name}
                <div className="text-subtle"><small>{part.net_quantity} · {part.sku}</small></div>
                {!part.active && <span className="badge bg-secondary">Not on sale</span>}
                {error && <div className="text-danger" role="alert"><small>{error}</small></div>}
            </td>
            <td>
                <input className="form-control form-control-sm" style={{ maxWidth: '5.5rem' }} inputMode="numeric"
                    value={qty} aria-label={`How many ${part.name} per kit`} data-testid="kit-part-row-qty"
                    onChange={(event) => setQty(event.target.value)} />
            </td>
            <td data-testid="kit-part-available">{part.available}</td>
            <td data-testid="kit-part-possible">{part.kits_possible}</td>
            <td className="d-flex gap-2">
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={save}
                    disabled={busy || qty === String(part.qty)} data-testid="kit-part-save">Save</button>
                <button type="button" className="btn btn-sm btn-outline-danger" onClick={remove}
                    disabled={busy} data-testid="kit-part-remove">Take out</button>
            </td>
        </tr>
    )
}

function KitCard({ kit, candidates, onDone }) {
    // Which part is the bottleneck, so the owner can see what to make more of.
    const limit = kit.components.reduce(
        (worst, part) => (worst === null || part.kits_possible < worst.kits_possible ? part : worst), null)

    return (
        <div className="card mb-4" data-testid="kit-card" data-sku={kit.sku}>
            <div className="card-body">
                <div className="d-flex flex-wrap justify-content-between align-items-start gap-2">
                    <div>
                        <h5 className="card-title mb-1">{kit.product} · {kit.name}</h5>
                        <p className="text-subtle mb-0"><small>{kit.sku}</small></p>
                    </div>
                    <div className="text-end">
                        <div><b data-testid="kit-price">{kit.price}</b></div>
                        <div className="text-subtle"><small>your price for the kit</small></div>
                    </div>
                </div>

                <p className="mt-3 mb-1">
                    <b data-testid="kit-available">{kit.available}</b> can be sold right now.
                    {!kit.active && <span className="badge bg-secondary ms-2">Not on sale</span>}
                </p>
                {kit.components.length === 0 &&
                    <p className="text-subtle" data-testid="kit-empty"><small>
                        Nothing is in this kit yet, so it shows as sold out in the shop. Add its parts below.
                    </small></p>
                }
                {limit && kit.available === limit.kits_possible &&
                    <p className="text-subtle" data-testid="kit-bottleneck"><small>
                        {limit.name} is what is holding it back.
                    </small></p>
                }
                {kit.components.length > 0 &&
                    <>
                        <div className="table-responsive mt-3">
                            <table className="table">
                                <thead className="table-dark">
                                    <tr><th>What is inside</th><th>Per kit</th><th>In stock</th><th>Kits it allows</th><th>Actions</th></tr>
                                </thead>
                                <tbody>
                                    {kit.components.map((part) => <PartRow key={part.id} part={part} onDone={onDone} />)}
                                </tbody>
                            </table>
                        </div>
                        <p className="text-subtle">
                            <small data-testid="kit-parts-total">
                                Bought separately the parts come to {kit.parts_total_label}. Your kit price is
                                independent of that: change it on the product's "Sizes &amp; stock" screen.
                            </small>
                        </p>
                    </>
                }
                <div className="mt-3">
                    <AddPart kit={kit} candidates={candidates} onDone={onDone} />
                </div>
            </div>
        </div>
    )
}

function OwnerKits() {
    const [data, setData] = useState(null)
    const [failed, setFailed] = useState('')

    const load = () => apiInstance.get('owner/kits/').then((res) => setData(res.data))
        .catch((error) => setFailed(messageOf(error)))

    useEffect(() => { load() }, [])

    return (
        <div className="container-fluid" id="main">
            <div className="row row-offcanvas row-offcanvas-left h-100">
                <Sidebar />
                <div className="col-md-9 col-lg-10 main mt-4" data-testid="owner-kits">
                    <h4>Kits</h4>
                    <p className="text-subtle"><small>
                        A kit is one item made of other sizes. It keeps no stock of its own: how many you can
                        sell is decided by the scarcest thing inside it, and selling one takes stock off every
                        part. To make a new kit, add a size on a product's "Sizes &amp; stock" screen and tick
                        "Kit"; then say here what goes in it.
                    </small></p>

                    {failed && <div className="alert alert-danger" role="alert">{failed}</div>}
                    {data === null && !failed && <p>Loading...</p>}
                    {data && data.kits.length === 0 &&
                        <div className="card"><div className="card-body" data-testid="no-kits">
                            <p className="mb-0">
                                You have no kits yet. Open a product, go to "Sizes &amp; stock", add a size for the
                                kit with the price you want to charge, and tick "Kit".
                            </p>
                        </div></div>
                    }
                    {data && data.kits.map((kit) => (
                        <KitCard key={kit.variant_id} kit={kit} candidates={data.candidates} onDone={load} />
                    ))}
                </div>
            </div>
        </div>
    )
}

export default OwnerKits
