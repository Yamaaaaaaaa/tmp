"""
Parse phap-dien HTML files (legal codification) into ChromaDB vector store.
Each article (Điều) becomes a separate document with title + content.
"""

import os
import json
import torch
from bs4 import BeautifulSoup
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Paths — adjust DEMUC_HTML_DIR to where your phap-dien HTML files live
DEMUC_HTML_DIR = os.path.join("..", "..", "law-crawler", "phap-dien", "demuc")
DEMUC_JSON_PATH = os.path.join("..", "..", "law-crawler", "phap-dien", "demuc.json")
DB_PERSIST_PATH = "./chroma_db_demuc"
ST_MODEL_PATH = "keepitreal/vietnamese-sbert"

# ---- Load đề mục metadata (UUID → topic name) ----
demuc_names = {}
if os.path.exists(DEMUC_JSON_PATH):
    with open(DEMUC_JSON_PATH, "r", encoding="utf-8-sig") as f:
        for item in json.load(f):
            demuc_names[item["Value"]] = item["Text"]

# ---- Parse HTML files into LangChain Documents ----
documents = []
html_dir = os.path.abspath(DEMUC_HTML_DIR)
if not os.path.isdir(html_dir):
    raise FileNotFoundError(f"HTML directory not found: {html_dir}")

html_files = sorted(f for f in os.listdir(html_dir) if f.endswith(".html"))
print(f"Found {len(html_files)} HTML files in {html_dir}")

for filename in html_files:
    demuc_id = filename.replace(".html", "")
    demuc_name = demuc_names.get(demuc_id, "Unknown")
    filepath = os.path.join(html_dir, filename)

    with open(filepath, "r", encoding="utf-8-sig") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Each article: pDieu (title) → pGhiChu (source ref) → pNoiDung (content)
    for dieu_tag in soup.find_all("p", class_="pDieu"):
        title = dieu_tag.get_text(strip=True)

        # Source reference
        ghi_chu = dieu_tag.find_next_sibling("p", class_="pGhiChu")
        source = ghi_chu.get_text(strip=True) if ghi_chu else ""

        # Content
        noidung = dieu_tag.find_next("p", class_="pNoiDung")
        content = noidung.get_text("\n", strip=True) if noidung else ""

        if not content or len(content) < 50:
            continue

        full_text = f"{title}\n{source}\n\n{content}"
        metadata = {
            "demuc_id": demuc_id,
            "demuc_name": demuc_name,
            "dieu_title": title,
            "source": filename,
        }
        documents.append(Document(page_content=full_text, metadata=metadata))

print(f"Extracted {len(documents)} articles from {len(html_files)} files")

# ---- Split long articles ----
text_splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=200)
texts = text_splitter.split_documents(documents)
print(f"Split into {len(texts)} chunks")

# ---- Create embeddings & persist to ChromaDB ----
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

embeddings = HuggingFaceEmbeddings(model_name=ST_MODEL_PATH, model_kwargs={"device": device})

# Process in batches to avoid OOM
import time
BATCH_SIZE = 256
start_time = time.time()
for i in range(0, len(texts), BATCH_SIZE):
    batch = texts[i:i + BATCH_SIZE]
    if i == 0:
        vectordb = Chroma.from_documents(
            documents=batch,
            embedding=embeddings,
            persist_directory=DB_PERSIST_PATH,
        )
    else:
        vectordb.add_documents(batch)
    elapsed = time.time() - start_time
    done = min(i + BATCH_SIZE, len(texts))
    rate = done / elapsed if elapsed > 0 else 0
    remaining = (len(texts) - done) / rate if rate > 0 else 0
    print(f"  [{done}/{len(texts)}] {elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining")

vectordb.persist()
print(f"Done! ChromaDB saved to {DB_PERSIST_PATH} in {time.time()-start_time:.0f}s")