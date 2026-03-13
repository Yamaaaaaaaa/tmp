import os
import glob
import pandas as pd
from tqdm import tqdm

from langchain.schema import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores.chroma import Chroma

DOCS_PATH = "E:/LegalChatbot/vnlawadvisor/backend/recommendation/data/"
DB_PERSIST_PATH = "./chroma_db_vbqppl"
ST_MODEL_PATH = "keepitreal/vietnamese-sbert"

print("Loading CSV files...")
csv_files = glob.glob(os.path.join(DOCS_PATH, "*.csv"))

documents = []
for file in csv_files:
    print(f"Reading {file}")
    df = pd.read_csv(file, encoding="utf-8-sig")
    for _, row in df.iterrows():
        page_content = str(row.get("noi_dung", ""))
        metadata = {
            "id": str(row.get("id", "")),
            "id_vb": str(row.get("id_vb", "")),
            "chi_muc_cha": str(row.get("chi_muc_cha", "")),
        }
        documents.append(
            Document(
                page_content=page_content,
                metadata=metadata
            )
        )

print(f"Loaded {len(documents)} documents")

print("Splitting documents...")
text_splitter = CharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=100
)
texts = text_splitter.split_documents(documents)

print(f"Total chunks: {len(texts)}")
print("Adding citation metadata...")
for doc in texts:
    doc.metadata["citation"] = doc.page_content

print("Loading embedding model...")
embeddings = HuggingFaceEmbeddings(
    model_name=ST_MODEL_PATH,
    model_kwargs={"device": "cuda"}
)
vectordb = Chroma(
    persist_directory=DB_PERSIST_PATH,
    embedding_function=embeddings
)

batch_size = 64
print("Adding documents to vector database...")
for i in tqdm(range(0, len(texts), batch_size)):
    batch = texts[i:i+batch_size]
    vectordb.add_documents(batch)

vectordb.persist()
print("Vector database created successfully.")