# 🎓 本地 AI 学习助教

一个完全运行在本地的 AI 私人导师。把你的课程 PDF 丢进去，它就能基于你的材料回答问题、记住你的学习进度，并随着你的互动越来越了解你。

**所有数据留在你自己的电脑上，不上传任何内容到云端。**

---

## ✨ 功能特点

- **RAG 检索增强**：只基于你上传的课程材料回答，不胡编乱造
- **学习者画像**：自动记录你的薄弱点和强项，每次对话都会个性化调整
- **长期记忆**：跨 session 记住你学过什么，把历史对话作为上下文
- **自动检测新材料**：往 `materials/` 放新 PDF，下次启动自动重新索引
- **聊天历史**：所有对话本地存储在 SQLite，随时回顾
- **中文优先**：默认用中文回答

---

## 🛠️ 环境要求

- macOS（Apple Silicon 或 Intel 均可）
- [Ollama](https://ollama.com) 已安装
- Python 3.11

---

## 🚀 安装步骤

### 1. 安装 Ollama 并拉取模型

```bash
# 安装 Ollama（如果还没装）
brew install ollama

# 拉取对话模型和 embedding 模型
ollama pull gemma4:e4b
ollama pull nomic-embed-text
```

### 2. 克隆项目

```bash
git clone git@github.com:scorpionfay/local_ai_study_tutor.git
cd local_ai_study_tutor
```

### 3. 创建 Python 虚拟环境并安装依赖

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install langchain langchain-core langchain-community langchain-text-splitters \
            langchain-ollama langchain-classic chromadb pypdf streamlit
```

### 4. 放入你的课程材料

把 PDF 文件复制到 `materials/` 文件夹：

```bash
cp 你的课件.pdf materials/
```

### 5. 启动

```bash
./start.sh
```

第一次启动会自动索引材料，之后每次检测到新 PDF 也会自动重新索引。

---

## 💡 日常使用

```bash
./start.sh
```

或者如果你设置了别名（见下方），直接：

```bash
tutor
```

**设置快捷命令（可选）：**

在 `~/.zshrc` 里加一行：

```bash
alias tutor="/path/to/local_ai_study_tutor/start.sh"
```

---

## 📁 项目结构

```
local_ai_study_tutor/
├── agent.py          # 核心逻辑：RAG 链、学习者画像、长期记忆
├── app.py            # Streamlit 前端界面
├── database.py       # SQLite 聊天历史管理
├── ingest.py         # PDF 索引脚本
├── ingest_new.sh     # 手动强制重新索引
├── start.sh          # 一键启动脚本
└── materials/        # 放你的 PDF 课件（不会提交到 git）
```

---

## 🔄 添加新材料

把新 PDF 放入 `materials/`，下次运行 `./start.sh` 会自动检测并重新索引。

如果想立即强制重建索引：

```bash
./ingest_new.sh
```

---

## ⚙️ 更换模型

在 `agent.py` 里修改模型名称：

```python
llm = OllamaLLM(model="你想用的模型", temperature=0.3)
embeddings = OllamaEmbeddings(model="nomic-embed-text")
```

支持任何 Ollama 上可用的模型，`ollama list` 查看已安装的模型。
