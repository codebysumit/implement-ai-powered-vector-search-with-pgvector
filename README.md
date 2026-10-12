# AI Powered Vector Search with pgvector on Tiger Cloud

A small project for the MLH Global Hack Week Hacktoberfest challenge: **Implement AI Powered Vector Search with pgvector**.

It stores word embeddings inside a TimescaleDB hypertable on Tiger Cloud. Then it searches by meaning, and filters by time range and metadata in the same SQL query. No separate vector database is needed.

## What this project shows

1. Vectors stored inside PostgreSQL using **pgvector**.
2. A **hypertable** for time based data using TimescaleDB.
3. A fast **diskann** index from **pgvectorscale**.
4. **Hybrid search**: meaning (cosine distance) plus a time filter plus a metadata filter.
5. A **small pretrained model** (model2vec), so it runs on a low end computer with no GPU.

## How it works

1. A few simple words (man, woman, girl, cat, bird, car) are turned into 256 numbers each by the model.
2. The numbers are saved in the `word_vectors` table with a time and a group name (`kind`).
3. A search word like `lady` is turned into numbers the same way.
4. PostgreSQL finds the closest vectors using the `<=>` cosine distance operator.
5. The `WHERE` part removes old rows and rows from other groups.

## Files

| File | Purpose |
|---|---|
| `main.py` | The Python script that creates embeddings, inserts rows, and runs the searches |
| `requirements.txt` | Python packages needed |
| `.env` | Your private database link (not uploaded to GitHub) |
| `README.md` | This guide |

## Requirements

1. Python 3.9 or newer
2. A free Tiger Cloud service (TimescaleDB with pgvector and pgvectorscale)
3. Internet for the first run only, to download the small model (about 30 MB)

Install the packages:

```bash
pip install -r requirements.txt
```

## Setup

### 1. Create the `.env` file

Copy the connection string from your Tiger Cloud service page and save it like this:

```
DATABASE_URL=postgres://tsdbadmin:YOUR_PASSWORD@YOUR_HOST:YOUR_PORT/tsdb?sslmode=require
```

Add `.env` to your `.gitignore` so your password is never uploaded.

### 2. Set up TimescaleDB (run this in the Tiger Cloud SQL editor)

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;

DROP TABLE IF EXISTS word_vectors;

CREATE TABLE word_vectors (
  time TIMESTAMPTZ NOT NULL,
  kind TEXT,
  word TEXT,
  embedding VECTOR(256)
);

SELECT create_hypertable('word_vectors', 'time');

CREATE INDEX ON word_vectors
USING diskann (embedding vector_cosine_ops);
```

What each part does:

1. `vector` turns on pgvector. `vectorscale` adds the diskann index.
2. `word_vectors` is the table. The `embedding` column holds 256 numbers per word.
3. `create_hypertable` makes the table a time series table, split by the `time` column.
4. The diskann index makes similarity search fast.

The size `256` must match the model output. If you use another model, change this number.

### 3. Run the script

```bash
python main.py
```

## Useful SQL queries

Run these in the Tiger Cloud SQL editor after the script finishes.

**See all rows (the vector is cut short for reading):**

```sql
SELECT time, kind, word, left(embedding::text, 40) AS embedding_preview
FROM word_vectors
ORDER BY time DESC;
```

**Count the rows:**

```sql
SELECT count(*) FROM word_vectors;
```

**Confirm the table is a hypertable:**

```sql
SELECT hypertable_name, num_dimensions
FROM timescaledb_information.hypertables
WHERE hypertable_name = 'word_vectors';
```

**Confirm the diskann index exists:**

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'word_vectors';
```

**Hybrid search: closest to woman, last 7 days, only people:**

```sql
SELECT word, kind,
       embedding <=> (SELECT embedding FROM word_vectors WHERE word = 'woman' LIMIT 1) AS distance
FROM word_vectors
WHERE time > now() - interval '7 days'
  AND kind = 'people'
ORDER BY distance
LIMIT 3;
```

**Same search, but no filters (to see the difference):**

```sql
SELECT word, kind,
       embedding <=> (SELECT embedding FROM word_vectors WHERE word = 'woman' LIMIT 1) AS distance
FROM word_vectors
ORDER BY distance
LIMIT 5;
```

A smaller distance means a closer meaning. A distance of 0 means the same vector.

## Expected results

1. Searching `lady` returns **woman** and **girl** near the top.
2. Searching `kitten` returns **cat** first.
3. Adding the `people` filter shows only people rows.
4. Searching `sparrow` does not return **bird**, because the bird row is 30 days old and the time filter removes it.

Exact distance numbers can differ a little. The order should look the same.

## Troubleshooting

1. **Error: type vector does not exist.** Run the two `CREATE EXTENSION` lines first.
2. **Dimension mismatch error.** The number in `VECTOR(256)` must match the number of values the model gives. The script prints this number when it runs.
3. **Model download fails.** Check your internet. You only need it for the first run.
4. **Connection error.** Check `DATABASE_URL` in your `.env` file and make sure it ends with `sslmode=require`.

## Tech used

1. Tiger Cloud (TimescaleDB on PostgreSQL)
2. pgvector and pgvectorscale
3. model2vec with the `minishlab/potion-base-8M` model
4. Python with psycopg2

## Challenge links

1. [Turning PostgreSQL Into a Vector Database](https://www.mlh.com/events/global-hack-week-open-source-90/challenges/ghwHF1026-tigerdata-pgvector)
2. [Deploying TimescaleDB Vector Search](https://mlh.link/ghwHF1026-tigerdata-vector)
