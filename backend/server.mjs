/*const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");
const Database = require("better-sqlite3");
const multer = require("multer");
const fetch = require("node-fetch");*/

// modular imports

import express from "express";
import cors from "cors";
import fs from "fs";
import path from "path";
import Database from "better-sqlite3";
import multer from "multer";
import fetch from "node-fetch";


// --- Config ---
const PORT = process.env.PORT || 8080;
//const IMAGE_DIR = path.join(__dirname, "storage", "images");
const IMAGE_DIR = path.join(process.cwd(), "storage", "images");
fs.mkdirSync(IMAGE_DIR, { recursive: true });

// --- DB ---
const db = new Database(path.join(process.cwd(), "scans.db"));
db.pragma("journal_mode = WAL");
db.exec(`CREATE TABLE IF NOT EXISTS scans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  class INTEGER,
  score REAL,
  latency_us INTEGER,
  ts INTEGER,
  image_filename TEXT,
  source TEXT,
  meta TEXT);`);

// Prepared statements
const insertScan = db.prepare(`
  INSERT INTO scans (class, score, latency_us, ts, image_filename, source, meta)
  VALUES (@class, @score, @latency_us, @ts, @image_filename, @source, @meta)
`);
const selectById = db.prepare(`SELECT * FROM scans WHERE id = ?`);
const selectAll = db.prepare(`
  SELECT * FROM scans ORDER BY ts DESC LIMIT ? OFFSET ?
`);
const deleteById = db.prepare(`DELETE FROM scans WHERE id = ?`);
const countAll = db.prepare(`SELECT COUNT(*) as n FROM scans`);

// --- Express setup ---
const app = express();
app.use(cors());
app.use(express.json({ limit: "15mb" }));
app.use("/images", express.static(IMAGE_DIR, { maxAge: 0, etag: false }));

const upload = multer({ storage: multer.memoryStorage() });

function saveBase64Png(b64) {
    const buf = Buffer.from(b64, "base64");
    const name = `scan_${Date.now()}.png`;
    const full = path.join(IMAGE_DIR, name);
    fs.writeFileSync(full, buf);
    return name;
}

async function downloadToFile(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`download fail ${res.status}`);
    const name = `scan_${Date.now()}.png`;
    const full = path.join(IMAGE_DIR, name);
    const fileStream = fs.createWriteStream(full);
    await new Promise((resolve, reject) => {
        res.body.pipe(fileStream);
        res.body.on("error", reject);
        fileStream.on("finish", resolve);
    });
    return name;
}

/**
 * POST /scans
 * Accetta:
 *  - JSON con { class, score, latency_us, timestamp?, image_url?}
 *  - Oppure multipart con field "image" (file) + JSON fields
 * Opz.: ?download=true -> se arriva image_url, lo scarica e salva localmente
 */
app.post("/scans", upload.single("image"), async (req, res) => {
    try {
        const body = req.body || {};
        const klass = parseInt(body.class);
        const score = parseFloat(body.score);
        const latency = parseInt(body.latency_us);
        const image_url = body.image_url;
        const ts = body.timestamp ? parseInt(body.timestamp) : Date.now();

        const row = {
            class: isNaN(klass) ? null : klass,
            score: isNaN(score) ? null : score,
            latency_us: isNaN(latency) ? null : latency,
            ts,
            image_url: image_url,
        };

        const info = insertScan.run(row);
        const saved = selectById.get(info.lastInsertRowid);

        res.status(201).json(saved);
    } catch (e) {
        console.error(e);
        res.status(400).json({ error: String(e.message || e) });
    }
});

/**
 * GET /allScans  (alias: GET /scans)
 * query: limit, offset
 */
app.get(["/allScans", "/scans"], (req, res) => {
    const limit = Math.min(parseInt(req.query.limit || "200"), 1000);
    const offset = parseInt(req.query.offset || "0");
    const rows = selectAll.all(limit, offset);
    const total = countAll.get().n;
    const withUrls = rows.map(r => ({
        ...r
    }));
    res.json({ total, limit, offset, items: withUrls });
});

app.listen(PORT, () => {
    console.log(`Express listening on http://0.0.0.0:${PORT}`);
});
