import { Fragment, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import apiInstance from '../../utils/axios';
import Sidebar from '../vendor/Sidebar';

// Did the free samples lead to sales? (Ayura phase D.)
//
// For every sample that has gone out: how many orders carried it, and how many of those
// customers later placed an order containing the full-size product. The same customer is
// recognised by their account, or failing that by the email or phone on the order, so a guest
// who comes back with the same details still counts.
//
// Buying something else does not count: only the product the sample is of.

function OwnerSamples() {
    const [rows, setRows] = useState(null)
    const [failed, setFailed] = useState('')
    const [openRow, setOpenRow] = useState(null)

    useEffect(() => {
        apiInstance.get('owner/samples-report/')
            .then((res) => setRows(res.data.rows))
            .catch((error) => setFailed(error?.response?.data?.message || 'The report could not be loaded.'))
    }, [])

    return (
        <div className="container-fluid" id="main">
            <div className="row row-offcanvas row-offcanvas-left h-100">
                <Sidebar />
                <div className="col-md-9 col-lg-10 main mt-4" data-testid="owner-samples">
                    <h4>Samples</h4>
                    <p className="text-subtle"><small>
                        Customers are never told a sample is coming, so this is the only place it shows.
                        Add samples to a parcel on the order's own screen, under "Handle orders".
                    </small></p>

                    {failed && <div className="alert alert-danger" role="alert">{failed}</div>}
                    {rows === null && !failed && <p>Loading...</p>}
                    {rows !== null && rows.length === 0 &&
                        <p data-testid="samples-empty">No samples have gone out yet.</p>
                    }

                    {rows !== null && rows.length > 0 &&
                        <div className="table-responsive">
                            <table className="table">
                                <thead className="table-dark">
                                    <tr><th>Sample</th><th>Orders that got it</th><th>Came back for it</th><th>Conversion</th><th /></tr>
                                </thead>
                                <tbody>
                                    {rows.map((row) => (
                                        <Fragment key={row.variant_id}>
                                            <tr data-testid="sample-row" data-sku={row.sku}>
                                                <td>
                                                    {row.sample}
                                                    <div className="text-subtle"><small>{row.sku}</small></div>
                                                </td>
                                                <td data-testid="sample-given">{row.given}</td>
                                                <td data-testid="sample-converted">{row.converted}</td>
                                                <td data-testid="sample-percent">{row.conversion_percent}%</td>
                                                <td>
                                                    {row.conversions.length > 0 &&
                                                        <button type="button" className="btn btn-sm btn-outline-secondary"
                                                            onClick={() => setOpenRow(openRow === row.variant_id ? null : row.variant_id)}>
                                                            {openRow === row.variant_id ? 'Hide' : 'Which orders'}
                                                        </button>
                                                    }
                                                </td>
                                            </tr>
                                            {openRow === row.variant_id &&
                                                <tr>
                                                    <td colSpan={5}>
                                                        <ul className="list-group" data-testid="sample-conversions">
                                                            {row.conversions.map((conversion) => (
                                                                <li className="list-group-item" key={conversion.sample_order}>
                                                                    Sample went with{' '}
                                                                    <Link to={`/admin-area/owner/orders/${conversion.sample_order}/`}>#{conversion.sample_order}</Link>
                                                                    {' '}&rarr; then bought{' '}
                                                                    {conversion.then_bought.map((order, index) => (
                                                                        <span key={order.oid}>
                                                                            {index > 0 ? ', ' : ''}
                                                                            <Link to={`/admin-area/owner/orders/${order.oid}/`}>#{order.oid}</Link>
                                                                            {' '}({order.total})
                                                                        </span>
                                                                    ))}
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    </td>
                                                </tr>
                                            }
                                        </Fragment>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    }
                </div>
            </div>
        </div>
    )
}

export default OwnerSamples
