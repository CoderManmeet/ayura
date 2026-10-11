import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import apiInstance from '../../utils/axios';
import { formatINR } from '../../utils/money';
import Sidebar from '../vendor/Sidebar';

// One product's sizes, stock and care information (Ayura phase B).
//
//   * Details: category, the short benefit line shown on the product tile, how to use,
//     ingredients and cautions. Words that may read as a medical or unproven claim are listed
//     while typing; they are a prompt to check the wording, and saving is never blocked.
//   * Sizes: each size has its own price, MRP, net quantity (g or ml) and packed shipping
//     weight. Sizes are switched off, never deleted, because past orders refer to them.
//   * Stock: stock is added as a batch (how many were made, when, and a use-by date if there
//     is one). Batches past their use-by date are flagged. Quantities are ledger history and
//     cannot be edited here; only the use-by date and notes can be corrected.
//
// Money is typed in rupees and sent to the server as TEXT ("449" or "449.50"). The server
// turns it into integer paise; nothing here does arithmetic on rupee amounts.

const UNITS = [['ml', 'ml'], ['g', 'g']];

// Integer paise -> the rupee text an owner would type ("44900" -> "449", "44950" -> "449.50").
const paiseToRupeesText = (paise) => {
    if (paise === null || paise === undefined) return '';
    const whole = Math.floor(paise / 100);
    const rest = paise % 100;
    return rest === 0 ? String(whole) : `${whole}.${String(rest).padStart(2, '0')}`;
};

const escapeRegExp = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// The same whole-word, case-insensitive check the server makes (backend/catalog/claims.py).
const findClaimWords = (words, ...texts) => {
    const blob = texts.map((text) => text || '').join(' ');
    return words.filter((word) => new RegExp(`(?<![a-z0-9])${escapeRegExp(word)}(?![a-z0-9])`, 'i').test(blob));
};

// "Skincare › Face" for a category, from the flat list the server sends.
const categoryPath = (category, byId) => {
    const names = [];
    const seen = new Set();
    let node = category;
    while (node && !seen.has(node.id)) {
        names.unshift(node.title);
        seen.add(node.id);
        node = node.parent ? byId[node.parent] : null;
    }
    return names.join(' › ');
};

const messageOf = (error) => error?.response?.data?.message || 'Something went wrong. Please try again.';

function Notice({ notice }) {
    if (!notice) return null;
    return (
        <div className={`alert ${notice.kind === 'error' ? 'alert-danger' : 'alert-info'}`} role={notice.kind === 'error' ? 'alert' : 'status'}
            data-testid={notice.kind === 'error' ? 'owner-error' : 'owner-notice'}>
            {notice.text}
        </div>
    );
}

// ------------------------------------------------------------------------------------ details

function DetailsForm({ product, categories, onSaved }) {
    const [form, setForm] = useState(() => ({
        category: product.category ?? '',
        benefit_line: product.benefit_line || '',
        how_to_use: product.how_to_use || '',
        ingredients: product.ingredients || '',
        cautions: product.cautions || '',
    }));
    const [busy, setBusy] = useState(false);
    const [notice, setNotice] = useState(null);

    const byId = useMemo(() => Object.fromEntries(categories.map((c) => [c.id, c])), [categories]);
    const options = useMemo(() => categories
        .map((c) => ({ id: c.id, label: categoryPath(c, byId), active: c.active }))
        .sort((a, b) => a.label.localeCompare(b.label)), [categories, byId]);

    const liveWarnings = findClaimWords(product.claim_words || [], form.benefit_line, form.how_to_use, form.cautions);

    const change = (event) => setForm({ ...form, [event.target.name]: event.target.value });

    const save = async (event) => {
        event.preventDefault();
        setBusy(true);
        setNotice(null);
        try {
            const res = await apiInstance.patch(`owner/products/${product.pid}/`, { ...form, category: form.category === '' ? null : form.category });
            onSaved(res.data);
            setNotice({ kind: 'info', text: 'Details saved.' });
        } catch (error) {
            setNotice({ kind: 'error', text: messageOf(error) });
        } finally {
            setBusy(false);
        }
    };

    return (
        <form className="card mb-4" onSubmit={save} data-testid="details-form">
            <div className="card-body">
                <h5 className="card-title">Details</h5>
                <Notice notice={notice} />
                <div className="row">
                    <div className="col-lg-6 mb-3">
                        <label className="form-label" htmlFor="ownerCategory">Category</label>
                        <select id="ownerCategory" name="category" className="form-select" value={form.category} onChange={change} data-testid="category-select">
                            <option value="">No category</option>
                            {options.map((option) => (
                                <option key={option.id} value={option.id}>{option.label}{option.active ? '' : ' (hidden)'}</option>
                            ))}
                        </select>
                        <p className="form-text"><Link to="/admin-area/owner/categories/">Manage categories</Link></p>
                    </div>
                    <div className="col-lg-6 mb-3">
                        <label className="form-label" htmlFor="ownerBenefit">Benefit line</label>
                        <input id="ownerBenefit" name="benefit_line" className="form-control" value={form.benefit_line} onChange={change}
                            maxLength={product.benefit_line_max || 120} data-testid="benefit-line" />
                        <p className="form-text">Shown on the product tile. {form.benefit_line.length}/{product.benefit_line_max || 120} characters.</p>
                    </div>
                    <div className="col-lg-12 mb-3">
                        <label className="form-label" htmlFor="ownerHowTo">How to use</label>
                        <textarea id="ownerHowTo" name="how_to_use" rows={3} className="form-control" value={form.how_to_use} onChange={change} />
                    </div>
                    <div className="col-lg-12 mb-3">
                        <label className="form-label" htmlFor="ownerIngredients">Ingredients</label>
                        <textarea id="ownerIngredients" name="ingredients" rows={3} className="form-control" value={form.ingredients} onChange={change} />
                        <p className="form-text">The full list, exactly as printed on the label.</p>
                    </div>
                    <div className="col-lg-12 mb-3">
                        <label className="form-label" htmlFor="ownerCautions">Cautions</label>
                        <textarea id="ownerCautions" name="cautions" rows={2} className="form-control" value={form.cautions} onChange={change} />
                    </div>
                </div>
                {liveWarnings.length > 0 &&
                    <div className="alert alert-danger" data-testid="claim-warnings">
                        <b>Check this wording:</b> {liveWarnings.join(', ')}. These words can read as a medical or
                        unproven claim. Use them only if you can back them up; you can still save.
                    </div>
                }
                <button type="submit" className="btn btn-primary" disabled={busy} data-testid="save-details">{busy ? 'Saving...' : 'Save details'}</button>
            </div>
        </form>
    );
}

// -------------------------------------------------------------------------------------- sizes

const emptySize = { label: '', net_quantity: '', net_quantity_unit: 'ml', price: '', mrp: '', weight_grams: '', sku: '' };

function SizeFields({ values, onChange, prefix }) {
    const field = (name, label, props = {}) => (
        <div className="col-lg-2 mb-2">
            <label className="form-label" htmlFor={`${prefix}-${name}`}>{label}</label>
            <input id={`${prefix}-${name}`} name={name} className="form-control" value={values[name]} onChange={onChange}
                data-testid={`${prefix}-${name}`} {...props} />
        </div>
    );
    return (
        <div className="row">
            {field('label', 'Size name', { placeholder: '30 ml' })}
            {field('net_quantity', 'Net quantity', { inputMode: 'numeric' })}
            <div className="col-lg-2 mb-2">
                <label className="form-label" htmlFor={`${prefix}-unit`}>Unit</label>
                <select id={`${prefix}-unit`} name="net_quantity_unit" className="form-select" value={values.net_quantity_unit || 'ml'} onChange={onChange}
                    data-testid={`${prefix}-unit`}>
                    {UNITS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
            </div>
            {field('price', 'Price (₹)', { inputMode: 'decimal' })}
            {field('mrp', 'MRP (₹)', { inputMode: 'decimal' })}
            {field('weight_grams', 'Packed weight (g)', { inputMode: 'numeric', title: 'Weight with packaging, used for shipping' })}
            {field('sku', 'SKU (optional)', { title: 'Leave blank and one is made for you' })}
        </div>
    );
}

function SizeRow({ variant, onProduct }) {
    const [editing, setEditing] = useState(false);
    const [values, setValues] = useState(null);
    const [busy, setBusy] = useState(false);
    const [notice, setNotice] = useState(null);

    const startEdit = () => {
        setValues({
            label: variant.name,
            net_quantity: variant.net_quantity ?? '',
            net_quantity_unit: variant.net_quantity_unit || 'ml',
            price: paiseToRupeesText(variant.price_paise),
            mrp: paiseToRupeesText(variant.mrp_paise),
            weight_grams: variant.weight_grams ?? '',
            sku: variant.sku || '',
        });
        setNotice(null);
        setEditing(true);
    };

    const send = async (body) => {
        setBusy(true);
        setNotice(null);
        try {
            const res = await apiInstance.patch(`owner/variants/${variant.id}/`, body);
            onProduct(res.data);
            return true;
        } catch (error) {
            setNotice({ kind: 'error', text: messageOf(error) });
            return false;
        } finally {
            setBusy(false);
        }
    };

    const save = async (event) => {
        event.preventDefault();
        const ok = await send({ ...values, net_quantity: String(values.net_quantity), weight_grams: String(values.weight_grams) });
        if (ok) setEditing(false);
    };

    const quantity = variant.net_quantity ? `${variant.net_quantity} ${variant.net_quantity_unit}` : 'Not set';

    return (
        <>
            <tr data-testid="size-row" data-size={variant.name}>
                <td>
                    {variant.name}
                    {variant.is_default && <span className="badge bg-success ms-2">Main</span>}
                    {!variant.active && <span className="badge bg-secondary ms-2">Off</span>}
                    <div className="text-muted"><small>{variant.sku}</small></div>
                </td>
                <td data-testid="size-net-quantity">{quantity}</td>
                <td>{formatINR(variant.price_paise)}</td>
                <td>{variant.mrp_paise != null ? formatINR(variant.mrp_paise) : '—'}</td>
                <td>{variant.weight_grams != null ? `${variant.weight_grams} g` : '—'}</td>
                <td data-testid="size-available">{variant.available} <small className="text-muted">of {variant.on_hand}</small></td>
                <td>
                    <button type="button" className="btn btn-sm btn-outline-secondary me-2 mb-1" onClick={startEdit} disabled={busy}>Edit</button>
                    {!variant.is_default && variant.active &&
                        <button type="button" className="btn btn-sm btn-outline-secondary me-2 mb-1" disabled={busy}
                            onClick={() => send({ make_default: true })}>Make main</button>
                    }
                    {!variant.is_default &&
                        <button type="button" className="btn btn-sm btn-outline-secondary mb-1" disabled={busy}
                            onClick={() => send({ active: !variant.active })}>{variant.active ? 'Switch off' : 'Switch on'}</button>
                    }
                </td>
            </tr>
            {(editing || notice) &&
                <tr>
                    <td colSpan={7}>
                        <Notice notice={notice} />
                        {editing &&
                            <form onSubmit={save}>
                                <SizeFields values={values} prefix={`edit-${variant.id}`}
                                    onChange={(event) => setValues({ ...values, [event.target.name]: event.target.value })} />
                                <button type="submit" className="btn btn-sm btn-primary me-2" disabled={busy}>Save size</button>
                                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setEditing(false)}>Cancel</button>
                            </form>
                        }
                    </td>
                </tr>
            }
        </>
    );
}

function SizesPanel({ product, onProduct }) {
    const [values, setValues] = useState(emptySize);
    const [busy, setBusy] = useState(false);
    const [notice, setNotice] = useState(null);

    const add = async (event) => {
        event.preventDefault();
        setBusy(true);
        setNotice(null);
        try {
            const res = await apiInstance.post(`owner/products/${product.pid}/variants/`, values);
            onProduct(res.data);
            setValues({ ...emptySize, net_quantity_unit: values.net_quantity_unit });
            setNotice({ kind: 'info', text: `Size "${values.label}" added.` });
        } catch (error) {
            setNotice({ kind: 'error', text: messageOf(error) });
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="card mb-4" data-testid="sizes-panel">
            <div className="card-body">
                <h5 className="card-title">Sizes</h5>
                <p className="text-muted"><small>
                    Net quantity is what the pack contains, as on the label. Packed weight includes the
                    packaging and is used for shipping. A product made in the old form starts with one size
                    called "Default": the first size you add takes its place and keeps its stock.
                </small></p>
                <div className="table-responsive">
                    <table className="table">
                        <thead className="table-dark">
                            <tr><th>Size</th><th>Net quantity</th><th>Price</th><th>MRP</th><th>Packed weight</th><th>Available</th><th>Actions</th></tr>
                        </thead>
                        <tbody>
                            {product.variants.map((variant) => <SizeRow key={variant.id} variant={variant} onProduct={onProduct} />)}
                        </tbody>
                    </table>
                </div>
                <form onSubmit={add} className="mt-3" data-testid="add-size-form">
                    <h6>Add a size</h6>
                    <Notice notice={notice} />
                    <SizeFields values={values} prefix="new-size" onChange={(event) => setValues({ ...values, [event.target.name]: event.target.value })} />
                    <button type="submit" className="btn btn-primary" disabled={busy} data-testid="add-size">{busy ? 'Adding...' : 'Add size'}</button>
                </form>
            </div>
        </div>
    );
}

// -------------------------------------------------------------------------------------- stock

function BatchRow({ batch, onProduct }) {
    const [bestBefore, setBestBefore] = useState(batch.best_before || '');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    const save = async () => {
        setBusy(true);
        setError('');
        try {
            const res = await apiInstance.patch(`owner/batches/${batch.id}/`, { best_before: bestBefore || null });
            onProduct(res.data);
        } catch (err) {
            setError(messageOf(err));
        } finally {
            setBusy(false);
        }
    };

    return (
        <tr data-testid="batch-row" data-expired={batch.expired ? 'true' : 'false'}>
            <td>{batch.batch_code}{batch.production_notes && <div className="text-muted"><small>{batch.production_notes}</small></div>}</td>
            <td>{batch.manufactured_on}</td>
            <td>
                <div className="d-flex gap-2 align-items-center">
                    <input type="date" className="form-control" value={bestBefore} onChange={(event) => setBestBefore(event.target.value)}
                        aria-label={`Use by for batch ${batch.batch_code}`} />
                    {(bestBefore || '') !== (batch.best_before || '') &&
                        <button type="button" className="btn btn-sm btn-primary" disabled={busy} onClick={save}>Save</button>
                    }
                </div>
                {!batch.best_before && <small className="text-muted">No use-by date recorded yet</small>}
                {error && <small className="text-danger" role="alert">{error}</small>}
            </td>
            <td>
                {batch.remaining} <small className="text-muted">of {batch.quantity_produced}</small>
                {batch.expired && <span className="badge bg-danger ms-2" data-testid="batch-expired">Expired</span>}
            </td>
        </tr>
    );
}

function StockForm({ variant, onProduct }) {
    const blank = { quantity: '', manufactured_on: '', best_before: '', cost_per_unit: '', production_notes: '' };
    const [values, setValues] = useState(blank);
    const [busy, setBusy] = useState(false);
    const [notice, setNotice] = useState(null);

    const change = (event) => setValues({ ...values, [event.target.name]: event.target.value });

    const submit = async (event) => {
        event.preventDefault();
        setBusy(true);
        setNotice(null);
        try {
            const res = await apiInstance.post(`owner/variants/${variant.id}/stock/`, values);
            onProduct(res.data);
            setValues(blank);
            setNotice({ kind: 'info', text: `${values.quantity} added to ${variant.name}.` });
        } catch (error) {
            setNotice({ kind: 'error', text: messageOf(error) });
        } finally {
            setBusy(false);
        }
    };

    const id = (name) => `stock-${variant.id}-${name}`;

    return (
        <form onSubmit={submit} data-testid="stock-form" data-size={variant.name}>
            <Notice notice={notice} />
            <div className="row">
                <div className="col-lg-2 mb-2">
                    <label className="form-label" htmlFor={id('quantity')}>Quantity made</label>
                    <input id={id('quantity')} name="quantity" inputMode="numeric" className="form-control" value={values.quantity} onChange={change} data-testid="stock-quantity" />
                </div>
                <div className="col-lg-2 mb-2">
                    <label className="form-label" htmlFor={id('made')}>Made on</label>
                    <input id={id('made')} name="manufactured_on" type="date" className="form-control" value={values.manufactured_on} onChange={change} />
                </div>
                <div className="col-lg-2 mb-2">
                    <label className="form-label" htmlFor={id('use-by')}>Use by (if known)</label>
                    <input id={id('use-by')} name="best_before" type="date" className="form-control" value={values.best_before} onChange={change} data-testid="stock-use-by" />
                </div>
                <div className="col-lg-2 mb-2">
                    <label className="form-label" htmlFor={id('cost')}>Cost per unit (₹)</label>
                    <input id={id('cost')} name="cost_per_unit" inputMode="decimal" className="form-control" value={values.cost_per_unit} onChange={change} />
                </div>
                <div className="col-lg-4 mb-2">
                    <label className="form-label" htmlFor={id('notes')}>Notes</label>
                    <input id={id('notes')} name="production_notes" className="form-control" value={values.production_notes} onChange={change} />
                </div>
            </div>
            <button type="submit" className="btn btn-sm btn-primary" disabled={busy} data-testid="add-stock">{busy ? 'Adding...' : 'Add stock'}</button>
        </form>
    );
}

function StockPanel({ product, onProduct }) {
    return (
        <div className="card mb-4" data-testid="stock-panel">
            <div className="card-body">
                <h5 className="card-title">Stock</h5>
                <p className="text-muted"><small>
                    Each delivery of made stock is a batch. If you do not know the use-by date yet you can add it
                    later; record it before the order is packed. Batches past their use-by date are marked Expired.
                </small></p>
                {product.variants.map((variant) => (
                    <div key={variant.id} className="mb-4" data-testid="stock-size" data-size={variant.name}>
                        <h6>{variant.name} <small className="text-muted">· {variant.available} available</small></h6>
                        {variant.batches.length > 0 &&
                            <div className="table-responsive">
                                <table className="table">
                                    <thead><tr><th>Batch</th><th>Made on</th><th>Use by</th><th>Left</th></tr></thead>
                                    <tbody>
                                        {variant.batches.map((batch) => <BatchRow key={`${batch.id}-${batch.best_before}`} batch={batch} onProduct={onProduct} />)}
                                    </tbody>
                                </table>
                            </div>
                        }
                        <StockForm variant={variant} onProduct={onProduct} />
                    </div>
                ))}
            </div>
        </div>
    );
}

// --------------------------------------------------------------------------------------- page

function OwnerProduct() {
    const { pid } = useParams();
    const [product, setProduct] = useState(null);
    const [categories, setCategories] = useState([]);
    const [failed, setFailed] = useState('');

    useEffect(() => {
        setProduct(null);
        setFailed('');
        apiInstance.get(`owner/products/${pid}/`).then((res) => setProduct(res.data))
            .catch((error) => setFailed(error?.response?.status === 404 ? 'This product does not exist.' : messageOf(error)));
        apiInstance.get('owner/categories/').then((res) => setCategories(res.data)).catch(() => setCategories([]));
    }, [pid]);

    return (
        <div className="container-fluid" id="main">
            <div className="row row-offcanvas row-offcanvas-left h-100">
                <Sidebar />
                <div className="col-md-9 col-lg-10 main mt-4" data-testid="owner-product">
                    {failed && <div className="alert alert-danger" role="alert">{failed}</div>}
                    {!failed && product === null && <p>Loading...</p>}
                    {product &&
                        <>
                            <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
                                <h4 className="mb-0" data-testid="owner-product-title">{product.title} <small className="text-muted">· sizes &amp; stock</small></h4>
                                <div>
                                    <Link to={`/admin-area/product/update/${product.pid}/`} className="btn btn-outline-secondary btn-sm me-2">Photos &amp; description</Link>
                                    <Link to={`/detail/${product.slug}`} className="btn btn-outline-secondary btn-sm">View in shop</Link>
                                </div>
                            </div>
                            {product.status !== 'published' &&
                                <div className="alert alert-info">This product is not in the shop yet (status: {product.status}).</div>
                            }
                            <DetailsForm key={`details-${product.id}`} product={product} categories={categories} onSaved={setProduct} />
                            <SizesPanel product={product} onProduct={setProduct} />
                            <StockPanel product={product} onProduct={setProduct} />
                        </>
                    }
                </div>
            </div>
        </div>
    );
}

export default OwnerProduct;
