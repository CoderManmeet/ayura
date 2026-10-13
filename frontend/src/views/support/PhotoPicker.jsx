import { useEffect, useRef, useState } from 'react';
import { ImagePlus, X } from 'lucide-react';

// Choosing photos to send with a support message (Ayura phase F).
//
// The limits here are the same ones the server enforces, so an over-limit file is caught before
// the customer waits for an upload — but the server's refusal is the real gate, and its message
// is what the thread screens show if anything slips past.
//
// Previews are object URLs, revoked when the picker lets the file go, so choosing and
// unchoosing photos does not leak memory.

export const MAX_PHOTOS = 3;
export const MAX_MB = 5;

function PhotoPicker({ files, onChange, idPrefix = 'support' }) {
    const [problem, setProblem] = useState('');
    const [previews, setPreviews] = useState([]);
    const input = useRef(null);

    useEffect(() => {
        const urls = files.map((file) => URL.createObjectURL(file));
        setPreviews(urls);
        return () => urls.forEach((url) => URL.revokeObjectURL(url));
    }, [files]);

    const add = (event) => {
        const chosen = Array.from(event.target.files || []);
        if (chosen.length === 0) return;
        setProblem('');

        const tooBig = chosen.find((file) => file.size > MAX_MB * 1024 * 1024);
        if (tooBig) setProblem(`${tooBig.name} is over ${MAX_MB} MB. Please choose a smaller photo.`);
        const notAnImage = chosen.find((file) => !file.type.startsWith('image/'));
        if (notAnImage) setProblem(`${notAnImage.name} is not a photo. Please choose a JPEG or PNG picture.`);

        const usable = chosen.filter((file) => file.size <= MAX_MB * 1024 * 1024 && file.type.startsWith('image/'));
        const next = [...files, ...usable].slice(0, MAX_PHOTOS);
        if (files.length + usable.length > MAX_PHOTOS) {
            setProblem(`You can send up to ${MAX_PHOTOS} photos with one message.`);
        }
        onChange(next);
        // Let the same file be chosen again after it has been removed.
        if (input.current) input.current.value = '';
    };

    const remove = (index) => {
        setProblem('');
        onChange(files.filter((unused, position) => position !== index));
    };

    return (
        <div className="flex flex-col gap-3" data-testid="photo-picker">
            <div className="flex flex-wrap items-center gap-3">
                <label htmlFor={`${idPrefix}-photos`}
                    className="inline-flex cursor-pointer items-center gap-2 border border-line-strong px-4 py-2 text-xs">
                    <ImagePlus className="size-4" aria-hidden="true" />
                    {files.length > 0 ? 'Add another photo' : 'Add a photo'}
                </label>
                <input ref={input} id={`${idPrefix}-photos`} type="file" accept="image/*" multiple
                    onChange={add} className="sr-only" data-testid="photo-input" />
                <span className="text-xs text-subtle">
                    Up to {MAX_PHOTOS} photos, {MAX_MB} MB each. A photo of the problem helps us a lot.
                </span>
            </div>

            {files.length > 0 &&
                <ul className="flex flex-wrap gap-3 p-0">
                    {files.map((file, index) => (
                        <li key={`${file.name}-${index}`} className="relative size-20 overflow-hidden bg-muted"
                            data-testid="photo-chosen">
                            {previews[index] && <img src={previews[index]} alt="" className="size-full object-cover" />}
                            <button type="button" onClick={() => remove(index)} aria-label={`Remove ${file.name}`}
                                className="absolute right-0 top-0 bg-ink/80 p-1 text-white" data-testid="photo-remove">
                                <X className="size-3" aria-hidden="true" />
                            </button>
                        </li>
                    ))}
                </ul>
            }

            {problem && <p className="text-xs text-danger" role="alert" data-testid="photo-problem">{problem}</p>}
        </div>
    );
}

export default PhotoPicker;
