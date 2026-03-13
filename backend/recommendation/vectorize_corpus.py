import csv
import sys

csv.field_size_limit(100_000_000)

from langchain.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores.chroma import Chroma
from langchain.document_loaders import DirectoryLoader
from tqdm import tqdm

DOCS_PATH = "E:/LegalChatbot/vnlawadvisor/backend/recommendation/data/"
DB_PERSIST_PATH = "./chroma_db_vbqppl"
ST_MODEL_PATH="keepitreal/vietnamese-sbert"


loader = DirectoryLoader(DOCS_PATH, glob="./*.csv", loader_cls=CSVLoader,loader_kwargs={"encoding": "utf-8-sig"})
print("Loading documents...")
results = loader.load()
print(f"Loaded {len(results)} documents")
text_splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=100)
print("Splitting documents...")
texts = text_splitter.split_documents(results)
print(f"Total chunks: {len(texts)}")

print("Embedding model loading...")
embeddings = HuggingFaceEmbeddings(model_name=ST_MODEL_PATH, model_kwargs={"device": "cuda"})
# vectordb = Chroma.from_documents(documents=texts,
#                                  embedding=embeddings,
#                                  persist_directory=DB_PERSIST_PATH)
# vectordb.persist()

vectordb = Chroma(
    persist_directory=DB_PERSIST_PATH,
    embedding_function=embeddings
)

batch_size = 64

for i in tqdm(range(0, len(texts), batch_size)):
    vectordb.add_documents(texts[i:i+batch_size])

vectordb.persist()