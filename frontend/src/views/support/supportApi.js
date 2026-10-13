// Talking to the support endpoints (Ayura phase F).
//
// One place for the three shapes a thread is reached by, so no screen has to remember which:
//
//   * a signed-in customer: the JWT on the shared Axios instance is enough;
//   * a guest: a signed token, which travels as ?token=... on a read and in the body on a write;
//   * photos: multipart, because a JSON body cannot carry a file.
//
// Nothing here stores the token. It lives in the URL the customer was given, so a thread is
// reachable from any device that has the link and from nowhere else.

import apiInstance from '../../utils/axios';

export const messageOf = (error) => error?.response?.data?.message
    || 'Something went wrong. Please try again.';

// A request is multipart when there are photos and plain JSON otherwise.
//
// The shared Axios instance sets `Content-Type: application/json` for every request, so a
// FormData body MUST say multipart for itself or it is sent with a JSON content type and no
// boundary — the files then never arrive, silently. Every upload in this project passes the
// header the same way (see views/vendor/UpdateProduct.jsx).
const MULTIPART = { headers: { 'Content-Type': 'multipart/form-data' } };

const asRequest = (fields, photos) => {
    const files = (photos || []).filter(Boolean);
    if (files.length === 0) return [fields, undefined];
    const form = new FormData();
    Object.entries(fields).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') form.append(key, value);
    });
    files.forEach((file) => form.append('photos', file));
    return [form, MULTIPART];
};

export const openQuery = ({ subject, body, email, phone, orderOid, photos }) => {
    const [data, config] = asRequest({
        subject, body, email: email || '', phone: phone || '', order_oid: orderOid || '',
    }, photos);
    return apiInstance.post('support/queries/', data, config).then((res) => res.data);
};

// A signed-in customer reads their thread by its reference. A guest reads it by their token
// alone, and the server says which thread that is: the link holds no reference to edit.
export const readThread = (ref) =>
    apiInstance.get(`support/queries/${ref}/`).then((res) => res.data);

export const readThreadByLink = (token) =>
    apiInstance.get('support/thread/', { params: { token } }).then((res) => res.data);

export const replyToThread = (ref, { body, photos }) => {
    const [data, config] = asRequest({ body }, photos);
    return apiInstance.post(`support/queries/${ref}/`, data, config).then((res) => res.data);
};

export const replyByLink = (token, { body, photos }) => {
    const [data, config] = asRequest({ body, token }, photos);
    return apiInstance.post('support/thread/', data, config).then((res) => res.data);
};

export const myQueries = () => apiInstance.get('support/queries/mine/').then((res) => res.data);

export const findThread = ({ orderOid, email }) =>
    apiInstance.post('support/find/', { order_oid: orderOid, email }).then((res) => res.data);

export const queriesForOrder = (orderOid) =>
    apiInstance.get(`support/orders/${orderOid}/queries/`).then((res) => res.data);

export const STATUS_LABEL = {
    OPEN: 'Waiting for us',
    ANSWERED: 'Answered',
    CLOSED: 'Closed',
};
