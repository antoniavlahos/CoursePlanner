"""
One-time script: generate sentence embeddings for every course and store them
in the database.

Model: all-MiniLM-L6-v2
  - 80 MB download (cached after first run)
  - 384-dimensional vectors
  - Fast on CPU, good quality for semantic similarity

Run:
    python generate_embeddings.py

Re-run any time courses are added or descriptions are updated.
"""

import os
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer

DB_PATH = os.environ.get('DB_PATH', 'purdue_courses.db')
MODEL_NAME = 'all-MiniLM-L6-v2'
BATCH_SIZE = 256


def main():
    conn = sqlite3.connect(DB_PATH)

    # Add the embedding column if it doesn't exist yet
    cols = {r[1] for r in conn.execute('PRAGMA table_info(courses)')}
    if 'embedding' not in cols:
        conn.execute('ALTER TABLE courses ADD COLUMN embedding BLOB')
        print('Added embedding column to courses table.')

    # Load all courses
    rows = conn.execute('SELECT id, title, description FROM courses').fetchall()
    print(f'Loaded {len(rows)} courses from {DB_PATH}')

    # Build the text to embed: "Title. Description"
    ids   = [r[0] for r in rows]
    texts = [
        f"{(r[1] or '').strip()}. {(r[2] or '').strip()}"
        for r in rows
    ]

    # Load model (downloads ~80 MB on first run, then cached)
    print(f'Loading model {MODEL_NAME!r} …')
    model = SentenceTransformer(MODEL_NAME)

    # Encode in batches with a progress bar
    print(f'Encoding {len(texts)} courses (batch size {BATCH_SIZE}) …')
    vectors = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # unit-length → dot product == cosine similarity
    )

    # Store each vector as a raw float32 BLOB
    print('Saving embeddings to database …')
    conn.executemany(
        'UPDATE courses SET embedding = ? WHERE id = ?',
        [(vec.astype(np.float32).tobytes(), cid) for vec, cid in zip(vectors, ids)],
    )
    conn.commit()
    conn.close()

    dims = vectors.shape[1]
    size_mb = vectors.nbytes / 1_048_576
    print(f'Done. {len(ids)} embeddings × {dims} dims stored ({size_mb:.1f} MB in DB).')


if __name__ == '__main__':
    main()
