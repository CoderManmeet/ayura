// The brand's typefaces, bundled with the site (npm @fontsource packages) so no request goes to
// a font service. Only the weights the theme uses are imported. The names these files declare
// are the ones used by --font-display and --font-body in src/theme/brand.css.
//
// Imported from main.jsx before the theme. Kept out of brand.css on purpose: Tailwind inlines
// CSS @imports but leaves the font files' relative addresses pointing at the wrong folder.
import '@fontsource-variable/bricolage-grotesque/index.css';
