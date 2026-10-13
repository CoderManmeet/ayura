import { useEffect, useState } from 'react';

import apiInstance from '../../utils/axios';
import { formatINR } from '../../utils/money';
import Sidebar from '../vendor/Sidebar';

// Store settings (Ayura phase C): shipping, free shipping, Cash on Delivery and its fee, and the
// label details shown on every product page (Phase B).
//
// Amounts are typed in rupees and sent to the server as TEXT ("79" or "79.50"); the server
// stores integer paise. A change applies to the next price worked out for a cart or an unpaid
// checkout. An order that has been placed keeps the figures it was placed with.

const paiseToRupeesText = (paise) => {
    if (paise === null || paise === undefined) return '';
    const whole = Math.floor(paise / 100);
    const rest = paise % 100;
    return rest === 0 ? String(whole) : `${whole}.${String(rest).padStart(2, '0')}`;
};

const formFrom = (data) => ({
    shipping_enabled: data.shipping_enabled,
    shipping_flat: paiseToRupeesText(data.shipping_flat_paise),
    free_shipping_enabled: data.free_shipping_enabled,
    free_shipping_threshold: paiseToRupeesText(data.free_shipping_threshold_paise),
    cod_enabled: data.cod_enabled,
    cod_fee_enabled: data.cod_fee_enabled,
    cod_fee: paiseToRupeesText(data.cod_fee_paise),
    maker_name: data.maker_name || '',
    maker_address: data.maker_address || '',
    country_of_origin: data.country_of_origin || '',
    consumer_care_contact: data.consumer_care_contact || '',
    grievance_officer_name: data.grievance_officer_name || '',
    grievance_officer_designation: data.grievance_officer_designation || '',
    grievance_officer_email: data.grievance_officer_email || '',
    grievance_officer_phone: data.grievance_officer_phone || '',
    grievance_officer_address: data.grievance_officer_address || '',
    grievance_response_days: String(data.grievance_response_days ?? 0),
});

function Switch({ id, label, hint, checked, onChange, testId }) {
    return (
        <div className="form-check mb-2">
            <input id={id} type="checkbox" className="form-check-input" checked={checked} onChange={(event) => onChange(event.target.checked)} data-testid={testId} />
            <label htmlFor={id} className="form-check-label">{label}</label>
            {hint && <div className="form-text">{hint}</div>}
        </div>
    );
}

function OwnerSettings() {
    const [saved, setSaved] = useState(null)
    const [form, setForm] = useState(null)
    const [busy, setBusy] = useState(false)
    const [notice, setNotice] = useState(null)

    useEffect(() => {
        apiInstance.get('owner/settings/').then((res) => {
            setSaved(res.data)
            setForm(formFrom(res.data))
        }).catch(() => setNotice({ kind: 'error', text: 'The settings could not be loaded.' }))
    }, [])

    const set = (name) => (value) => setForm((current) => ({ ...current, [name]: value }))
    const text = (name) => (event) => set(name)(event.target.value)

    const save = async (event) => {
        event.preventDefault()
        setBusy(true)
        setNotice(null)
        try {
            const res = await apiInstance.patch('owner/settings/', form)
            setSaved(res.data)
            setForm(formFrom(res.data))
            setNotice({ kind: 'info', text: 'Settings saved. They apply to the next cart or checkout; placed orders keep their own figures.' })
        } catch (error) {
            setNotice({ kind: 'error', text: error?.response?.data?.message || 'Something went wrong. Please try again.' })
        } finally {
            setBusy(false)
        }
    }

    return (
        <div className="container-fluid" id="main">
            <div className="row row-offcanvas row-offcanvas-left h-100">
                <Sidebar />
                <div className="col-md-9 col-lg-10 main mt-4" data-testid="owner-settings">
                    <h4>Store settings</h4>
                    {notice &&
                        <div className={`alert ${notice.kind === 'error' ? 'alert-danger' : 'alert-info'}`} role={notice.kind === 'error' ? 'alert' : 'status'}
                            data-testid={notice.kind === 'error' ? 'settings-error' : 'settings-notice'}>{notice.text}</div>
                    }
                    {form === null && !notice && <p>Loading...</p>}
                    {form !== null &&
                        <form onSubmit={save}>
                            <div className="card mb-4"><div className="card-body">
                                <h5 className="card-title">Shipping</h5>
                                <Switch id="setShipping" label="Charge shipping" checked={form.shipping_enabled} onChange={set('shipping_enabled')}
                                    hint="Off: every order ships free." testId="setting-shipping-enabled" />
                                {form.shipping_enabled &&
                                    <div className="row">
                                        <div className="col-lg-4 mb-3">
                                            <label className="form-label" htmlFor="setShippingFlat">Shipping charge per order (₹)</label>
                                            <input id="setShippingFlat" className="form-control" inputMode="decimal" value={form.shipping_flat} onChange={text('shipping_flat')} data-testid="setting-shipping-flat" />
                                        </div>
                                        <div className="col-lg-8 mb-3">
                                            <Switch id="setFreeShipping" label="Free shipping above an order amount" checked={form.free_shipping_enabled} onChange={set('free_shipping_enabled')}
                                                hint="Off: every order pays the shipping charge, whatever its size." testId="setting-free-shipping-enabled" />
                                            {form.free_shipping_enabled &&
                                                <>
                                                    <label className="form-label" htmlFor="setThreshold">Free shipping from (₹, after any discount)</label>
                                                    <input id="setThreshold" className="form-control" inputMode="decimal" value={form.free_shipping_threshold} onChange={text('free_shipping_threshold')} data-testid="setting-threshold" />
                                                </>
                                            }
                                        </div>
                                    </div>
                                }
                            </div></div>

                            <div className="card mb-4"><div className="card-body">
                                <h5 className="card-title">Cash on Delivery</h5>
                                <Switch id="setCod" label="Offer Cash on Delivery" checked={form.cod_enabled} onChange={set('cod_enabled')}
                                    hint="Off: customers can only pay online." testId="setting-cod-enabled" />
                                {form.cod_enabled &&
                                    <>
                                        <Switch id="setCodFee" label="Charge a Cash on Delivery fee" checked={form.cod_fee_enabled} onChange={set('cod_fee_enabled')}
                                            hint="Shown on the payment choice and in the total before the customer places the order. Coupons do not discount it, and it does not count towards free shipping." testId="setting-cod-fee-enabled" />
                                        {form.cod_fee_enabled &&
                                            <div className="row"><div className="col-lg-4 mb-3">
                                                <label className="form-label" htmlFor="setCodFeeAmount">Fee (₹)</label>
                                                <input id="setCodFeeAmount" className="form-control" inputMode="decimal" value={form.cod_fee} onChange={text('cod_fee')} data-testid="setting-cod-fee" />
                                            </div></div>
                                        }
                                    </>
                                }
                            </div></div>

                            <div className="card mb-4"><div className="card-body">
                                <h5 className="card-title">Product information</h5>
                                <p className="text-subtle"><small>Shown on every product page, only when filled in. Which of these the law requires is a question for your professional (L3).</small></p>
                                <div className="row">
                                    <div className="col-lg-6 mb-3">
                                        <label className="form-label" htmlFor="setMaker">Made by</label>
                                        <input id="setMaker" className="form-control" value={form.maker_name} onChange={text('maker_name')} maxLength={200} />
                                    </div>
                                    <div className="col-lg-6 mb-3">
                                        <label className="form-label" htmlFor="setOrigin">Country of origin</label>
                                        <input id="setOrigin" className="form-control" value={form.country_of_origin} onChange={text('country_of_origin')} maxLength={100} />
                                    </div>
                                    <div className="col-lg-6 mb-3">
                                        <label className="form-label" htmlFor="setAddress">Maker's address</label>
                                        <textarea id="setAddress" rows={3} className="form-control" value={form.maker_address} onChange={text('maker_address')} />
                                    </div>
                                    <div className="col-lg-6 mb-3">
                                        <label className="form-label" htmlFor="setCare">Consumer care</label>
                                        <textarea id="setCare" rows={3} className="form-control" value={form.consumer_care_contact} onChange={text('consumer_care_contact')} />
                                    </div>
                                </div>
                            </div></div>

                            <div className="card mb-4"><div className="card-body">
                                <h5 className="card-title">Grievance officer</h5>
                                <p className="text-subtle"><small>
                                    Shown on the Contact page, <b>only once you fill in a name</b>. Every word here is
                                    yours: nothing is published until you type it. Whether these details are required
                                    of your business, and how they should be worded, is a question for your
                                    professional (L4) &mdash; this screen does not decide it.
                                </small></p>
                                <div className="row">
                                    <div className="col-lg-6 mb-3">
                                        <label className="form-label" htmlFor="setGrievanceName">Name</label>
                                        <input id="setGrievanceName" className="form-control" value={form.grievance_officer_name}
                                            onChange={text('grievance_officer_name')} maxLength={200}
                                            data-testid="setting-grievance-name" />
                                    </div>
                                    <div className="col-lg-6 mb-3">
                                        <label className="form-label" htmlFor="setGrievanceRole">Designation</label>
                                        <input id="setGrievanceRole" className="form-control" value={form.grievance_officer_designation}
                                            onChange={text('grievance_officer_designation')} maxLength={200}
                                            data-testid="setting-grievance-designation" />
                                    </div>
                                    <div className="col-lg-6 mb-3">
                                        <label className="form-label" htmlFor="setGrievanceEmail">Email</label>
                                        <input id="setGrievanceEmail" className="form-control" value={form.grievance_officer_email}
                                            onChange={text('grievance_officer_email')} maxLength={254}
                                            data-testid="setting-grievance-email" />
                                    </div>
                                    <div className="col-lg-6 mb-3">
                                        <label className="form-label" htmlFor="setGrievancePhone">Phone</label>
                                        <input id="setGrievancePhone" className="form-control" value={form.grievance_officer_phone}
                                            onChange={text('grievance_officer_phone')} maxLength={40}
                                            data-testid="setting-grievance-phone" />
                                    </div>
                                    <div className="col-lg-6 mb-3">
                                        <label className="form-label" htmlFor="setGrievanceAddress">Address (optional)</label>
                                        <textarea id="setGrievanceAddress" rows={3} className="form-control"
                                            value={form.grievance_officer_address} onChange={text('grievance_officer_address')} />
                                    </div>
                                    <div className="col-lg-6 mb-3">
                                        <label className="form-label" htmlFor="setGrievanceDays">Acknowledge within (days)</label>
                                        <input id="setGrievanceDays" className="form-control" inputMode="numeric"
                                            value={form.grievance_response_days} onChange={text('grievance_response_days')}
                                            data-testid="setting-grievance-days" />
                                        <div className="form-text">0 = do not state a time.</div>
                                    </div>
                                </div>
                            </div></div>

                            {saved &&
                                <p className="text-subtle" data-testid="settings-summary"><small>
                                    Now: {saved.shipping_enabled
                                        ? `shipping ${formatINR(saved.shipping_flat_paise)}${saved.free_shipping_enabled ? `, free from ${formatINR(saved.free_shipping_threshold_paise)}` : ' on every order'}`
                                        : 'free shipping on every order'}
                                    {' · '}
                                    {saved.cod_enabled
                                        ? (saved.cod_fee_enabled ? `Cash on Delivery with a ${formatINR(saved.cod_fee_paise)} fee` : 'Cash on Delivery at no extra cost')
                                        : 'no Cash on Delivery'}
                                </small></p>
                            }
                            <button type="submit" className="btn btn-primary mb-5" disabled={busy} data-testid="save-settings">{busy ? 'Saving...' : 'Save settings'}</button>
                        </form>
                    }
                </div>
            </div>
        </div>
    )
}

export default OwnerSettings
