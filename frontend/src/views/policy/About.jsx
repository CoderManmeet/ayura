import { Link } from 'react-router-dom';

import { STORE_NAME, TAGLINE } from '../../utils/constants';
import usePageTitle from '../../utils/usePageTitle';
import { PageIntro } from '../ui/kit';
import { PLACEHOLDER_COPY } from './policies';

// About page.
//
// ============================  PLACEHOLDER COPY  ============================
// The paragraphs below are draft wording so the page can be laid out. They are NOT the
// brand's approved story, and they deliberately make no claim about ingredients, how or where
// the products are made, or words like "natural" or "Ayurvedic": those are statements the owner
// must supply and stand behind (ROADMAP decision Z9).
// Replace the text, then this page needs no other change.
// ============================================================================
function About() {
    usePageTitle('Our story');
    return (
        <main data-testid="about-page">
            <PageIntro eyebrow="Our story" title="Our story." />
            <div className="mx-auto max-w-3xl px-5 py-12 md:px-10 md:py-20">
                {PLACEHOLDER_COPY &&
                    <p className="mb-8 border border-accent/40 bg-panel px-4 py-3 text-xs text-accent" role="note">
                        Draft text. The final story has not been published yet.
                    </p>
                }
                <div className="flex flex-col gap-6 text-sm leading-7 text-subtle">
                    <p className="font-display text-2xl leading-snug text-ink">{STORE_NAME} began with one rule. {TAGLINE}</p>
                    <p>[PLACEHOLDER] Who makes the products, and how the brand started, goes here.</p>
                    <p>[PLACEHOLDER] How the products are made, and how to use and store them, goes here.</p>
                </div>
                <Link to="/shop" className="ui-btn mt-10">Shop all</Link>
            </div>
        </main>
    );
}

export default About;
