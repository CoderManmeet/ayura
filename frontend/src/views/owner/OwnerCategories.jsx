import { useEffect, useMemo, useState } from 'react';

import apiInstance from '../../utils/axios';
import Sidebar from '../vendor/Sidebar';

// Categories and sub-categories (Ayura phase B). A category can sit inside another
// (Skincare › Face). Categories are hidden, never deleted, because products refer to them;
// a hidden category and everything inside it disappears from the shop's filters.

const messageOf = (error) => error?.response?.data?.message || 'Something went wrong. Please try again.';

// The categories as an indented tree: parents first, each followed by its children.
const asTree = (categories) => {
    const children = {};
    categories.forEach((c) => { (children[c.parent ?? 'top'] ||= []).push(c); });
    Object.values(children).forEach((list) => list.sort((a, b) => a.title.localeCompare(b.title)));
    const rows = [];
    const seen = new Set();
    const walk = (key, depth) => {
        (children[key] || []).forEach((c) => {
            if (seen.has(c.id)) return;
            seen.add(c.id);
            rows.push({ ...c, depth });
            walk(c.id, depth + 1);
        });
    };
    walk('top', 0);
    // Anything whose parent is missing from the list still shows, at the top level.
    categories.forEach((c) => { if (!seen.has(c.id)) rows.push({ ...c, depth: 0 }); });
    return rows;
};

function CategoryRow({ category, rows, onSaved }) {
    const [editing, setEditing] = useState(false);
    const [title, setTitle] = useState(category.title);
    const [parent, setParent] = useState(category.parent ?? '');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    const send = async (body) => {
        setBusy(true);
        setError('');
        try {
            await apiInstance.patch(`owner/categories/${category.id}/`, body);
            setEditing(false);
            onSaved();
        } catch (err) {
            setError(messageOf(err));
        } finally {
            setBusy(false);
        }
    };

    return (
        <tr data-testid="category-row" data-slug={category.slug}>
            <td style={{ paddingLeft: `${0.75 + category.depth * 1.5}rem` }}>
                {editing
                    ? <div className="d-flex flex-wrap gap-2">
                        <input className="form-control" value={title} onChange={(event) => setTitle(event.target.value)} aria-label="Category name" />
                        <select className="form-select" value={parent} onChange={(event) => setParent(event.target.value)} aria-label="Inside">
                            <option value="">Top level</option>
                            {rows.filter((row) => row.id !== category.id).map((row) => (
                                <option key={row.id} value={row.id}>{'— '.repeat(row.depth)}{row.title}</option>
                            ))}
                        </select>
                    </div>
                    : <>{category.depth > 0 && <span className="text-muted">↳ </span>}{category.title}</>
                }
                {error && <div className="text-danger" role="alert"><small>{error}</small></div>}
            </td>
            <td><small className="text-muted">{category.slug}</small></td>
            <td>{category.product_count}</td>
            <td>{category.active ? 'Shown' : <span className="badge bg-secondary">Hidden</span>}</td>
            <td>
                {editing
                    ? <>
                        <button type="button" className="btn btn-sm btn-primary me-2 mb-1" disabled={busy}
                            onClick={() => send({ title, parent: parent === '' ? null : parent })}>Save</button>
                        <button type="button" className="btn btn-sm btn-outline-secondary mb-1" onClick={() => setEditing(false)}>Cancel</button>
                    </>
                    : <>
                        <button type="button" className="btn btn-sm btn-outline-secondary me-2 mb-1" onClick={() => setEditing(true)}>Edit</button>
                        <button type="button" className="btn btn-sm btn-outline-secondary mb-1" disabled={busy}
                            onClick={() => send({ active: !category.active })}>{category.active ? 'Hide' : 'Show'}</button>
                    </>
                }
            </td>
        </tr>
    );
}

function OwnerCategories() {
    const [categories, setCategories] = useState(null);
    const [title, setTitle] = useState('');
    const [parent, setParent] = useState('');
    const [busy, setBusy] = useState(false);
    const [notice, setNotice] = useState(null);

    const load = () => apiInstance.get('owner/categories/').then((res) => setCategories(res.data)).catch(() => setCategories([]));

    useEffect(() => { load(); }, []);

    const rows = useMemo(() => asTree(categories || []), [categories]);

    const add = async (event) => {
        event.preventDefault();
        setBusy(true);
        setNotice(null);
        try {
            const res = await apiInstance.post('owner/categories/', { title, parent: parent === '' ? null : parent });
            setNotice({ kind: 'info', text: `"${res.data.title}" added.` });
            setTitle('');
            await load();
        } catch (error) {
            setNotice({ kind: 'error', text: messageOf(error) });
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="container-fluid" id="main">
            <div className="row row-offcanvas row-offcanvas-left h-100">
                <Sidebar />
                <div className="col-md-9 col-lg-10 main mt-4" data-testid="owner-categories">
                    <h4>Categories</h4>
                    <p className="text-muted"><small>
                        Put a category inside another to make a sub-category, for example Face inside Skincare.
                        Shoppers filtering by Skincare see the Face products too. Hide a category instead of deleting it.
                    </small></p>

                    <form className="card mb-4" onSubmit={add} data-testid="add-category-form">
                        <div className="card-body">
                            <h6>Add a category</h6>
                            {notice &&
                                <div className={`alert ${notice.kind === 'error' ? 'alert-danger' : 'alert-info'}`} role={notice.kind === 'error' ? 'alert' : 'status'}>{notice.text}</div>
                            }
                            <div className="row">
                                <div className="col-lg-6 mb-2">
                                    <label className="form-label" htmlFor="newCategoryTitle">Name</label>
                                    <input id="newCategoryTitle" className="form-control" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={100} />
                                </div>
                                <div className="col-lg-6 mb-2">
                                    <label className="form-label" htmlFor="newCategoryParent">Inside</label>
                                    <select id="newCategoryParent" className="form-select" value={parent} onChange={(event) => setParent(event.target.value)}>
                                        <option value="">Top level</option>
                                        {rows.map((row) => <option key={row.id} value={row.id}>{'— '.repeat(row.depth)}{row.title}</option>)}
                                    </select>
                                </div>
                            </div>
                            <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? 'Adding...' : 'Add category'}</button>
                        </div>
                    </form>

                    {categories === null && <p>Loading...</p>}
                    {categories !== null && categories.length === 0 && <p>No categories yet.</p>}
                    {rows.length > 0 &&
                        <div className="table-responsive">
                            <table className="table">
                                <thead className="table-dark">
                                    <tr><th>Name</th><th>Address</th><th>Products</th><th>In the shop</th><th>Actions</th></tr>
                                </thead>
                                <tbody>
                                    {rows.map((category) => (
                                        <CategoryRow key={`${category.id}-${category.title}-${category.parent}-${category.active}`}
                                            category={category} rows={rows} onSaved={load} />
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    }
                </div>
            </div>
        </div>
    );
}

export default OwnerCategories;
