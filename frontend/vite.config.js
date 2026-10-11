import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const here = path.dirname(fileURLToPath(import.meta.url))

// Defaults for the brand values in index.html. Keep them the same as src/utils/constants.js.
const DEFAULT_STORE_NAME = 'Ayura'
const DEFAULT_DESCRIPTION = 'Skin, hair and body care, made fresh in small batches.'
const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api/v1/'

const escapeHtml = (value) => String(value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

// The page background colour from the theme file, so the browser's address bar (theme-color)
// always matches the brand without a second place to edit.
const canvasColour = () => {
    try {
        const css = fs.readFileSync(path.join(here, 'src/theme/brand.css'), 'utf8')
        const match = css.match(/--color-canvas:\s*(#[0-9a-fA-F]{3,8})\s*;/)
        return match ? match[1] : '#ffffff'
    } catch (err) {
        return '#ffffff'
    }
}

// Fills the brand placeholders in index.html (%STORE_NAME%, %STORE_DESCRIPTION%,
// %THEME_COLOR%, %API_PRECONNECT%) from the environment, so a new brand or a new API address
// needs no edit to index.html. The API preconnect is worked out from VITE_API_BASE_URL.
function brandHtml(env) {
    const storeName = env.VITE_STORE_NAME || DEFAULT_STORE_NAME
    const description = env.VITE_STORE_DESCRIPTION || DEFAULT_DESCRIPTION
    let apiOrigin = ''
    try {
        apiOrigin = new URL(env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).origin
    } catch (err) {
        apiOrigin = ''
    }
    // A local API needs no preconnect; a remote one does (it may also be asleep and slow).
    const remote = apiOrigin && !/\/\/(localhost|127\.0\.0\.1)(:|$)/.test(apiOrigin)
    const preconnect = remote
        ? `<link rel="preconnect" href="${escapeHtml(apiOrigin)}" crossorigin />\n    <link rel="dns-prefetch" href="${escapeHtml(apiOrigin)}" />`
        : ''
    return {
        name: 'brand-html',
        transformIndexHtml(html) {
            return html
                .replace(/%STORE_NAME%/g, escapeHtml(storeName))
                .replace(/%STORE_DESCRIPTION%/g, escapeHtml(description))
                .replace(/%THEME_COLOR%/g, escapeHtml(canvasColour()))
                .replace(/%API_PRECONNECT%/g, preconnect)
        },
    }
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
    const env = { ...loadEnv(mode, here, 'VITE_'), ...process.env }
    return {
        build: {
            // Keep the shopper's download small: the heavy admin-only libraries (the rich-text
            // editor, charts) go into their own files, fetched only when the admin area is opened.
            // The rich-text editor is one big library (about 1.2 MB) and cannot usefully be split
            // further. It is only ever fetched when the owner opens Add or Edit Product, so the
            // limit is set above it rather than leaving a warning that means nothing.
            chunkSizeWarningLimit: 1300,
            rollupOptions: {
                output: {
                    manualChunks(id) {
                        if (!id.includes('node_modules')) return undefined;
                        if (id.includes('ckeditor')) return 'editor';
                        if (id.includes('chart.js') || id.includes('react-chartjs')) return 'charts';
                        if (id.includes('sweetalert2')) return 'dialogs';
                        if (id.includes('moment')) return 'dates';
                        return undefined;
                    },
                },
            },
        },
        plugins: [react(), brandHtml(env)],
    }
})
