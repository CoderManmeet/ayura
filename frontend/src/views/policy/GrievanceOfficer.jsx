import Addon from '../plugin/Addon';

// Grievance officer details (Ayura phase F, ROADMAP L4).
//
// EVERY WORD HERE IS THE OWNER'S OWN, typed into Store settings in the admin area. This
// component writes no legal statement: with no name entered it renders NOTHING AT ALL, so the
// store never publishes a claim about who handles grievances, or a promise about how quickly,
// that the owner has not made herself.
//
// Whether these details are required of this business, and in what wording, is a question for
// her professional. The heading below is the only text this file contributes, and it names the
// block rather than asserting anything.

function Line({ label, value }) {
    if (!value || !String(value).trim()) return null;
    return (
        <div className="flex justify-between gap-6 border-b border-line py-3 last:border-0">
            <dt className="text-subtle">{label}</dt>
            <dd className="whitespace-pre-line text-right">{value}</dd>
        </div>
    );
}

function GrievanceOfficer() {
    const addon = Addon();
    const name = addon?.grievance_officer_name;

    // Nothing entered, nothing published.
    if (!name || !String(name).trim()) return null;

    const days = Number(addon?.grievance_response_days || 0);

    return (
        <section className="mt-14" data-testid="grievance-officer">
            <h2 className="font-display text-2xl">Grievance officer</h2>
            <dl className="mt-4 text-sm">
                <Line label="Name" value={name} />
                <Line label="Designation" value={addon?.grievance_officer_designation} />
                <Line label="Email" value={addon?.grievance_officer_email} />
                <Line label="Phone" value={addon?.grievance_officer_phone} />
                <Line label="Address" value={addon?.grievance_officer_address} />
                {days > 0 &&
                    <Line label="We acknowledge within" value={days === 1 ? '1 day' : `${days} days`} />
                }
            </dl>
        </section>
    );
}

export default GrievanceOfficer;
