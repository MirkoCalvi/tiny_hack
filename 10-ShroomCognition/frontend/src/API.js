const BASE_URL = 'http://localhost:8080';
const REMOTE_URL = 'http://10.100.16.76:5000'

export async function getAllScans({ limit = 200, offset = 0 } = {}) {
  const url = `${BASE_URL}/allScans?limit=${limit}&offset=${offset}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch scans');
  return res.json();
}

export async function postScan(scanData) {
  const res = await fetch(`${BASE_URL}/scans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(scanData),
  });
  if (!res.ok) throw new Error('Failed to post scan');
  return res.json();
}

export async function inferImage(withImage = true) {
    try {
        const res = await fetch(`${REMOTE_URL}/infer?image=${withImage}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            new Error(err.error || `Infer failed: ${res.status}`);
        }

        return await res.json();
    } catch (error) {
        console.error("Infer error:", error);
        throw error;
    }
}

export async function fetchImage(filename) {
    try {
        const res = await fetch(`${REMOTE_URL}/images/${encodeURIComponent(filename)}`, {
            method: "GET",
            cache: "no-store",
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            new Error(err.error || `Image fetch failed: ${res.status}`);
        }

        const blob = await res.blob();
        return URL.createObjectURL(blob);
    } catch (error) {
        console.error("Image fetch error:", error);
        throw error;
    }
}