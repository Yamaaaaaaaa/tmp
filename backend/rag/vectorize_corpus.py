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

# ---- Load đề mục metadata (UUID → full metadata) ----
demuc_meta_by_id = {}
if os.path.exists(DEMUC_JSON_PATH):
    with open(DEMUC_JSON_PATH, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
        for item in data:
            # Tùy cấu trúc file JSON, nhưng thường key ID là "Value"
            demuc_id = item.get("Value") or item.get("id") or item.get("demuc_id")
            if not demuc_id:
                continue
            demuc_meta_by_id[demuc_id] = item

# ---- Parse HTML files into LangChain Documents ----
documents = []
html_dir = os.path.abspath(DEMUC_HTML_DIR)
if not os.path.isdir(html_dir):
    raise FileNotFoundError(f"HTML directory not found: {html_dir}")

html_files = sorted(f for f in os.listdir(html_dir) if f.endswith(".html"))
print(f"Found {len(html_files)} HTML files in {html_dir}")

for filename in html_files:
    demuc_id = filename.replace(".html", "")
    demuc_meta = demuc_meta_by_id.get(demuc_id, {}) if isinstance(demuc_meta_by_id, dict) else {}
    demuc_name = (
        demuc_meta.get("Text")
        or demuc_meta.get("demuc_name")
        or "Unknown"
    )
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
        contents = []
        node = dieu_tag.find_next_sibling()
        while node:
            classes = node.get("class", [])
            # stop khi sang điều mới
            if "pDieu" in classes:
                break
            if "pNoiDung" in classes:
                # lấy toàn bộ text kể cả p lồng bên trong
                text = node.get_text("\n", strip=True)
                if text:
                    contents.append(text)
            node = node.find_next_sibling()
        content = "\n".join(contents)

        if not content or len(content) < 50:
            continue

        full_text = f"{title}\n{source}\n\n{content}"

        # Build rich metadata so chat_endpoints.py có thể tạo citations đẹp:
        # - mapc: mã pháp điển / mã điều (dùng làm id khi click vào trích dẫn)
        # - _link: link gốc (nếu có)
        # - chude_id, demuc_id: phân nhóm chủ đề
        # - ten: tên đề mục / tiêu đề hiển thị
        # mapc từ anchor
        anchor = dieu_tag.find("a")
        mapc = anchor.get("name") if anchor else ""
        metadata = {
            "demuc_id": demuc_id,
            "demuc_name": demuc_name,
            "dieu_title": title,
            "source": filename,
            # Các trường bổ sung sẽ có giá trị nếu tồn tại trong demuc.json
            "mapc": mapc,
            "_link": demuc_meta.get("_link") or demuc_meta.get("link") or "",
            "chude_id": demuc_meta.get("ChuDe") or "",
            "ten": demuc_meta.get("Text") or title,
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