import os
from datetime import datetime, timedelta, timezone

import psycopg2
from dotenv import load_dotenv
from model2vec import StaticModel

# small pretrained model, about 30 MB, runs on CPU
model = StaticModel.from_pretrained("minishlab/potion-base-8M")


def to_pg(vec):
    return "[" + ",".join(str(float(x)) for x in vec) + "]"


# word, group, days ago
ROWS = [
    ("man", "people", 1),
    ("woman", "people", 2),
    ("girl", "people", 3),
    ("cat", "animal", 1),
    ("bird", "animal", 30),
    ("car", "thing", 2),
]

load_dotenv()
API_KEY = os.getenv("TD_CLIENT_API_KEY")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")

conn = psycopg2.connect(database=DB_NAME,
                        host=DB_HOST,
                        user=DB_USER,
                        password=DB_PASSWORD,
                        port=DB_PORT)
conn.autocommit = True
cur = conn.cursor()

cur.execute("TRUNCATE word_vectors")
now = datetime.now(timezone.utc)

vectors = model.encode([r[0] for r in ROWS])
print("Numbers per word:", len(vectors[0]))

for (word, kind, days), vec in zip(ROWS, vectors):
    cur.execute(
        "INSERT INTO word_vectors (time, kind, word, embedding) "
        "VALUES (%s, %s, %s, %s::vector)",
        (now - timedelta(days=days), kind, word, to_pg(vec)),
    )
print("Inserted", len(ROWS), "words")


def search(query, extra_filter=""):
    qvec = to_pg(model.encode([query])[0])
    cur.execute(f"""
        SELECT word, kind, embedding <=> %s::vector AS distance
        FROM word_vectors
        WHERE time > now() - interval '7 days' {extra_filter}
        ORDER BY embedding <=> %s::vector
        LIMIT 3
    """, (qvec, qvec))
    print("\nSearch:", query, extra_filter)
    for word, kind, dist in cur.fetchall():
        print(f"  {word:<6} {kind:<7} distance={dist:.3f}")


search("lady")                           # should find woman or girl
search("kitten")                         # should find cat
search("lady", "AND kind = 'people'")    # same, but only people
search("sparrow")                        # bird is 30 days old, so it is hidden

cur.close()
conn.close()