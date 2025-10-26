# 🌉 Dex Bridge

> **Long-term Shared Context Between LLMs**

Dex Bridge is an innovative system that captures, stores, and enables semantic search across conversations from multiple AI assistants (ChatGPT, Claude) using a local vector database. It creates a persistent memory layer that allows different LLMs to access your conversation history through the Model Context Protocol (MCP).

```
         []                     []
       .:[]:                  .:[]:
     .: :[]: :.             .: :[]: :.
   .: : :[]: : :.         .: : :[]: : :.
 .: : : :[]: : : :-.___.-: : : :[]: : : :.
_:_:_:_:_:[]:_:_:_:_:_::_:_:_:_ :[]:_:_:_:_:_
^^^^^^^^^^[]^^^^^^^^^^^^^^^^^^^^^[]^^^^^^^^^^
          []                     []
```

## 🎯 What Problem Does It Solve?

Every time you start a new conversation with an AI assistant, it has **zero context** of your previous conversations. Dex Bridge solves this by:

- 📝 **Capturing** real-time conversations from ChatGPT and Claude
- 💾 **Storing** them in a vector database with semantic search capabilities
- 🔍 **Enabling** any LLM to search and access your entire conversation history
- 🔗 **Bridging** the context gap between different AI assistants

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser / LLM Clients                     │
│              (ChatGPT, Claude, GitHub Copilot)               │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS Traffic
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    MITM Proxy Layer                          │
│              (mitmproxy @ localhost:8080)                    │
│                                                              │
│  ┌──────────────────┐         ┌─────────────────────┐      │
│  │ capture_req.py   │         │ capture_claude.py   │      │
│  │  (ChatGPT)       │         │   (Claude.ai)       │      │
│  └──────────────────┘         └─────────────────────┘      │
└──────────────────────┬──────────────────────────────────────┘
                       │ Intercept & Parse SSE/NDJSON
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  Processing Pipeline                         │
│                                                              │
│  parsed_matches/           merge_conversations.py           │
│    ├─ chatgpt.com/    ─────────────►  merged_conversations/ │
│    │   └─ conv_id__ts.json              ├─ chatgpt.com/    │
│    └─ claude.ai/                         │   └─ merged.json │
│        └─ conv_id__ts.json               └─ claude.ai/      │
└──────────────────────┬──────────────────────────────────────┘
                       │ Merge by conversation_id
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              Vector Database (Qdrant)                        │
│            store_chat_message.py                             │
│                                                              │
│  Collection: chat_messages                                   │
│  ├─ Embeddings (OpenAI text-embedding-3-small)              │
│  ├─ Metadata (role, timestamp, model, conversation_id)      │
│  └─ Content Hash (deduplication)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │ Semantic Search
                       ↓
┌─────────────────────────────────────────────────────────────┐
│            MCP Server (access_llm_memory.py)                 │
│                                                              │
│  Tool: search_memory(query, top_k)                           │
│  ├─ Generate query embedding                                 │
│  ├─ Search Qdrant vector DB                                  │
│  └─ Return relevant conversation snippets                    │
└──────────────────────┬──────────────────────────────────────┘
                       │ MCP Protocol
                       ↓
┌─────────────────────────────────────────────────────────────┐
│            VS Code / AI Clients                              │
│     (GitHub Copilot, Claude Desktop, etc.)                   │
│                                                              │
│  Now can access your entire conversation history!           │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Features

### 1. **Multi-Provider Capture**

- ✅ ChatGPT (chatgpt.com)
- ✅ Claude (claude.ai)
- 🔄 Extensible architecture for other LLMs

### 2. **Intelligent Parsing**

- Handles SSE (Server-Sent Events) streams
- Parses NDJSON (Newline Delimited JSON)
- Extracts text from complex patch events
- Preserves conversation structure and metadata

### 3. **Smart Deduplication**

- SHA-256 content hashing
- Prevents duplicate embeddings
- Efficient storage management

### 4. **Semantic Search**

- Vector embeddings via OpenAI's `text-embedding-3-small`
- Cosine similarity search in Qdrant
- Context-aware retrieval

### 5. **MCP Integration**

- Standard Model Context Protocol server
- Easy integration with any MCP-compatible client
- Accessible from VS Code, Claude Desktop, and more

## 📦 Installation

### Prerequisites

- Python 3.10+
- macOS (for proxy management scripts)
- OpenAI API Key
- Qdrant (local or cloud instance)

### Setup

1. **Clone the repository:**

```bash
git clone https://github.com/Dextron04/dex_bridge.git
cd dex_bridge
```

2. **Create and activate virtual environment:**

```bash
python3 -m venv dexenv
source dexenv/bin/activate  # On macOS/Linux
```

3. **Install dependencies:**

```bash
pip install -r dex_bridge/requirements.txt
```

4. **Configure environment variables:**

```bash
cd dex_bridge
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

5. **Install and start Qdrant:**

```bash
# Using Docker
docker pull qdrant/qdrant
docker run -p 6333:6333 qdrant/qdrant

# Or install locally from https://qdrant.tech/documentation/quick-start/
```

## 🎮 Usage

### Step 1: Start Capture System

```bash
cd dex_bridge
sudo bash dex_bridge.sh
```

This interactive menu lets you:

- ✅ Enable/disable system proxy
- 📡 Start mitmproxy capture
- 🔍 View current status
- 🔐 Manage SSL certificates

### Step 2: Use ChatGPT/Claude Normally

Browse to ChatGPT or Claude and have conversations as usual. Dex Bridge captures everything automatically in the background.

### Step 3: Process Conversations

The system automatically:

1. **Captures** streams to `parsed_matches/{provider}/`
2. **Merges** by conversation ID to `merged_conversations/{provider}/`
3. **Generates** embeddings and stores in Qdrant

You can also manually trigger:

```bash
# Merge conversations
python merge_conversations.py

# Store in vector DB
python store_chat_message.py
```

### Step 4: Search Your Memory

The MCP server is configured in `.vscode/mcp.json`:

```json
{
  "servers": {
    "memory_mcp": {
      "type": "stdio",
      "command": "/path/to/dexenv/bin/python3",
      "args": ["/path/to/dex_bridge/memory_mcp/access_llm_memory.py"]
    }
  }
}
```

Now ask any MCP-compatible AI:

```
"Search my memory for conversations about Python async programming"
```

## 🛠️ Components

### 1. **dex_bridge.sh**

- Main control script
- Manages macOS network proxy settings
- Handles SSL certificate installation
- Interactive TUI for system control

### 2. **MITM Scripts**

- `capture_req.py`: ChatGPT conversation capture
- `capture_claude.py`: Claude conversation capture
- Real-time SSE/NDJSON parsing
- Automatic file organization

### 3. **merge_conversations.py**

- Groups conversations by ID
- Extracts user/assistant exchanges
- Creates structured JSON output
- Supports multiple providers

### 4. **store_chat_message.py**

- Generates embeddings via OpenAI API
- Stores vectors in Qdrant
- Implements content-based deduplication
- Preserves rich metadata

### 5. **access_llm_memory.py**

- MCP server implementation
- `search_memory(query, top_k)` tool
- Returns semantically relevant results
- Includes conversation context

## 📊 Data Flow

```
Raw HTTPS Stream → MITM Capture → Parse Events → Extract Text
                                        ↓
                                   Parsed JSON
                                        ↓
                          Merge by Conversation ID
                                        ↓
                         Structured Conversations
                                        ↓
                            Generate Embeddings
                                        ↓
                          Store in Vector Database
                                        ↓
                         MCP Semantic Search API
                                        ↓
                          Any LLM Client Access
```

## 🔒 Security & Privacy

- **Local First**: All data stored locally by default
- **SSL/TLS**: mitmproxy CA certificate for HTTPS inspection
- **No Cloud**: Conversations never leave your machine (except OpenAI API for embeddings)
- **Content Hash**: Prevents accidental duplicate storage
- **Proxy Control**: Easy on/off toggle for privacy

## 🧪 Example Queries

Once set up, you can ask your AI assistant:

```
"What did I discuss about system architecture last week?"

"Show me all conversations where I talked about Python optimization"

"Find the conversation where I got help with React hooks"

"What database recommendations did I receive recently?"
```

## 📈 Future Enhancements

- [ ] Support for more LLM providers (Gemini, Perplexity, etc.)
- [ ] Web UI for conversation browsing
- [ ] Export to Markdown/PDF
- [ ] Custom embedding models
- [ ] Conversation analytics and insights
- [ ] Multi-user support
- [ ] Cloud sync options
- [ ] Advanced filtering and tagging

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- [mitmproxy](https://mitmproxy.org/) - Powerful HTTP/HTTPS proxy
- [Qdrant](https://qdrant.tech/) - High-performance vector database
- [OpenAI](https://openai.com/) - Embedding models
- [Model Context Protocol](https://modelcontextprotocol.io/) - Standard for AI context sharing

## 📧 Contact

**Tushin Kulshreshtha** - [@Dextron04](https://github.com/Dextron04)

Project Link: [https://github.com/Dextron04/dex_bridge](https://github.com/Dextron04/dex_bridge)

---

**Built with ❤️ to bridge the context gap between AI conversations**
