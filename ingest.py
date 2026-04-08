# ingest.py — 索引 materials/ 下所有文件（含子目录），针对中文优化

import pathlib
import subprocess
import pandas as pd
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

MATERIALS_DIR = pathlib.Path("./materials")
SUPPORTED = {".pdf", ".doc", ".docx", ".xlsx", ".xls"}
EMBED_MODEL = "shaw/dmeta-embedding-zh"

# 中文分句分隔符：优先按段落、句子断开，避免在词语中间切断
CHINESE_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "…", " ", ""]

def load_xlsx(path: pathlib.Path) -> list[Document]:
    docs = []
    try:
        xl = pd.read_excel(path, sheet_name=None, dtype=str)
        for sheet_name, df in xl.items():
            df = df.fillna("")
            text = f"[{path.name} — {sheet_name}]\n"
            text += df.to_string(index=False)
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={"source": str(path), "sheet": sheet_name}
                ))
    except Exception as e:
        print(f"  ⚠️  跳过 {path.name}：{e}")
    return docs

def load_doc(path: pathlib.Path) -> list[Document]:
    """用 macOS 自带 textutil 读取旧版 .doc 文件。"""
    try:
        result = subprocess.run(
            ["textutil", "-convert", "txt", "-stdout", "-encoding", "UTF-8", str(path)],
            capture_output=True, text=True, check=True
        )
        text = result.stdout.strip()
        if text:
            return [Document(page_content=text, metadata={"source": str(path)})]
    except Exception as e:
        print(f"  ⚠️  跳过 {path.name}：{e}")
    return []

def load_all_documents() -> list[Document]:
    all_docs = []
    files = sorted(MATERIALS_DIR.rglob("*"))
    files = [f for f in files if f.is_file() and f.suffix.lower() in SUPPORTED]

    print(f"  找到 {len(files)} 个文件")
    for f in files:
        print(f"  📄 {f.relative_to(MATERIALS_DIR)}")
        try:
            suffix = f.suffix.lower()
            if suffix == ".pdf":
                docs = PyMuPDFLoader(str(f)).load()
            elif suffix == ".docx":
                docs = Docx2txtLoader(str(f)).load()
            elif suffix == ".doc":
                docs = load_doc(f)
            elif suffix in {".xlsx", ".xls"}:
                docs = load_xlsx(f)
            else:
                continue
            all_docs.extend(docs)
        except Exception as e:
            print(f"  ⚠️  跳过 {f.name}：{e}")

    return all_docs

# ── 主流程 ────────────────────────────────────────────────────────────────────

print("📂 扫描 ./materials（含子目录）...")
docs = load_all_documents()
print(f"✅ 共加载 {len(docs)} 个文档片段")

print("✂️  切分 chunks（中文分句模式）...")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,       # 中文字符密度高，400字约等于英文600词的信息量
    chunk_overlap=50,
    separators=CHINESE_SEPARATORS,
)
chunks = splitter.split_documents(docs)
print(f"✅ 共生成 {len(chunks)} 个 chunks")

print("🔢 向量化并存入 ChromaDB ...")
embeddings = OllamaEmbeddings(model=EMBED_MODEL)
db = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./db"
)
print("✅ 索引完成，可以开始学习了！")

pathlib.Path(".last_ingest").touch()
