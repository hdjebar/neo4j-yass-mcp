# How to Add Your Favorite LLM Provider

Complete guide to integrating any LangChain-supported LLM into Neo4j YASS MCP.

---

## 🎯 Overview

Neo4j YASS MCP currently supports OpenAI, Anthropic, and Google GenAI. However, LangChain supports 300+ AI models across dozens of providers. This guide shows you how to add support for any of them.

---

## 📋 Prerequisites

Before adding a new provider, ensure:

1. ✅ The provider has a **LangChain integration package**
2. ✅ You have an **API key** (or can run locally if using Ollama/LM Studio)
3. ✅ The provider supports **chat models** (not just completion models)

---

## 🚀 Step-by-Step Guide

### Step 1: Find the LangChain Package

Check if your provider has a LangChain integration:

**Option A: Official LangChain Packages** (Recommended)
```bash
# Check PyPI for official packages
pip search langchain-mistralai
pip search langchain-cohere
pip search langchain-groq
```

**Option B: Community Integrations**
```bash
# Some providers are in langchain-community
pip install langchain-community
```

**Common Packages:**
| Provider | Package Name | Installation |
|----------|-------------|--------------|
| Mistral AI | `langchain-mistralai` | `pip install langchain-mistralai` |
| Cohere | `langchain-cohere` | `pip install langchain-cohere` |
| Groq | `langchain-groq` | `pip install langchain-groq` |
| Ollama | `langchain-ollama` | `pip install langchain-ollama` |
| Hugging Face | `langchain-huggingface` | `pip install langchain-huggingface` |
| Together AI | `langchain-together` | `pip install langchain-together` |
| Fireworks AI | `langchain-fireworks` | `pip install langchain-fireworks` |

---

### Step 2: Add Package to Dependencies

Edit `pyproject.toml` to include the new provider:

```toml
[project]
dependencies = [
    "fastmcp>=0.1.3",
    "neo4j>=5.15.0",
    "langchain>=0.3.7",
    "langchain-openai>=0.2.8",
    "langchain-anthropic>=0.3.0",
    "langchain-google-genai>=2.0.3",
    "langchain-mistralai>=0.2.0",  # ← Add your provider here
    # ... other dependencies
]
```

**Or install directly:**
```bash
pip install langchain-mistralai
# or
uv pip install langchain-mistralai
```

---

### Step 3: Update `config.py`

Add your provider to the `chatLLM()` function in [config.py](../config.py).

**Example: Adding Mistral AI**

```python
def chatLLM(config: LLMConfig) -> Any:
    """
    Create a chat LLM instance based on the provider configuration.
    """
    if config.provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            openai_api_key=config.api_key,
            streaming=config.streaming
        )

    elif config.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=config.model,
            temperature=config.temperature,
            anthropic_api_key=config.api_key,
            streaming=config.streaming
        )

    elif config.provider == "google-genai":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=config.model,
            temperature=config.temperature,
            google_api_key=config.api_key,
            streaming=config.streaming
        )

    # ← Add your provider here
    elif config.provider == "mistralai":
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(
            model=config.model,
            temperature=config.temperature,
            mistral_api_key=config.api_key,
            streaming=config.streaming
        )

    else:
        raise ValueError(f"Unknown provider: {config.provider}. Supported providers: openai, anthropic, google-genai, mistralai")
```

**Important Notes:**
- Always use the **chat model class** (e.g., `ChatMistralAI`, not `MistralAI`)
- Include `streaming=config.streaming` for streaming support
- Check the provider's documentation for the correct API key parameter name:
  - OpenAI: `openai_api_key`
  - Anthropic: `anthropic_api_key`
  - Google: `google_api_key`
  - Mistral: `mistral_api_key` (pattern: `{provider}_api_key`)

---

### Step 4: Update `.env.example`

Add configuration examples for your provider:

```bash
# =============================================================================
# LLM PROVIDER CONFIGURATION
# =============================================================================

# --- Provider Selection ---
# Choose ONE provider: openai, anthropic, google-genai, mistralai
LLM_PROVIDER=openai

# ... existing providers ...

# --- Mistral AI ---
# https://console.mistral.ai/
# Models: mistral-large-latest, mistral-medium-latest, mistral-small-latest
# LLM_PROVIDER=mistralai
# LLM_MODEL=mistral-large-latest
# LLM_API_KEY=your-mistral-api-key

# Temperature (0.0 = deterministic, 1.0 = creative)
LLM_TEMPERATURE=0.0

# Streaming (token-by-token responses)
LLM_STREAMING=false
```

---

### Step 5: Update Documentation

Create or update documentation for your provider:

**Option A: Update `docs/LLM_PROVIDERS.md`**

Add a new section following the existing format:

```markdown
## 4️⃣ Mistral AI

### Configuration

\`\`\`bash
# .env file
LLM_PROVIDER=mistralai
LLM_MODEL=mistral-large-latest
LLM_TEMPERATURE=0.0
LLM_API_KEY=your-mistral-api-key
\`\`\`

### Available Models

| Model | Context | Cost | Best For |
|-------|---------|------|----------|
| `mistral-large-latest` | 32k tokens | $$$ | Most capable, complex tasks |
| `mistral-medium-latest` | 32k tokens | $$ | Balanced performance |
| `mistral-small-latest` | 32k tokens | $ | Fast, cost-effective |

### Get API Key

1. Visit: https://console.mistral.ai/
2. Sign up / create account
3. Go to "API Keys" section
4. Click "Create new key"
5. Copy key

### Code Reference

In [config.py:XXX-YYY](../config.py):

\`\`\`python
elif config.provider == "mistralai":
    from langchain_mistralai import ChatMistralAI
    return ChatMistralAI(
        model=config.model,
        temperature=config.temperature,
        mistral_api_key=config.api_key,
        streaming=config.streaming
    )
\`\`\`
```

---

### Step 6: Test Your Integration

Test the new provider to ensure it works:

```bash
# Set up test environment
export NEO4J_URI=bolt://localhost:7687
export NEO4J_PASSWORD=your-password
export LLM_PROVIDER=mistralai
export LLM_MODEL=mistral-large-latest
export LLM_API_KEY=your-mistral-api-key
export LLM_TEMPERATURE=0.0

# Run the server
python server.py
```

**Test query:**
```bash
# In another terminal, test with the query_graph tool
# (method depends on your MCP client)
```

---

## 🎨 Real-World Examples

### Example 1: Mistral AI (API-based)

```python
# config.py addition
elif config.provider == "mistralai":
    from langchain_mistralai import ChatMistralAI
    return ChatMistralAI(
        model=config.model,
        temperature=config.temperature,
        mistral_api_key=config.api_key,
        streaming=config.streaming
    )
```

```bash
# .env configuration
LLM_PROVIDER=mistralai
LLM_MODEL=mistral-large-latest
LLM_API_KEY=your-mistral-api-key
```

---

### Example 2: Groq (Ultra-Fast Inference)

```python
# config.py addition
elif config.provider == "groq":
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=config.model,
        temperature=config.temperature,
        groq_api_key=config.api_key,
        streaming=config.streaming
    )
```

```bash
# .env configuration
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile  # Or mixtral-8x7b-32768
LLM_API_KEY=your-groq-api-key
```

---

### Example 3: Ollama (Local, No API Key)

```python
# config.py addition
elif config.provider == "ollama":
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=config.model,
        temperature=config.temperature,
        base_url=config.api_key or "http://localhost:11434",  # Reuse api_key field for base_url
        streaming=config.streaming
    )
```

```bash
# .env configuration
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2  # Or mistral, codellama, etc.
LLM_API_KEY=http://localhost:11434  # Optional: custom Ollama server URL
LLM_TEMPERATURE=0.0

# Prerequisites: Install Ollama and pull a model
# curl -fsSL https://ollama.com/install.sh | sh
# ollama pull llama3.2
```

---

### Example 4: Cohere (RAG-Optimized)

```python
# config.py addition
elif config.provider == "cohere":
    from langchain_cohere import ChatCohere
    return ChatCohere(
        model=config.model,
        temperature=config.temperature,
        cohere_api_key=config.api_key,
        streaming=config.streaming
    )
```

```bash
# .env configuration
LLM_PROVIDER=cohere
LLM_MODEL=command-r-plus  # Or command-r, command-nightly
LLM_API_KEY=your-cohere-api-key
```

---

### Example 5: Hugging Face (Self-Hosted)

```python
# config.py addition
elif config.provider == "huggingface":
    from langchain_huggingface import ChatHuggingFace
    from langchain_huggingface import HuggingFaceEndpoint

    # For Inference API
    llm = HuggingFaceEndpoint(
        repo_id=config.model,
        temperature=config.temperature,
        huggingfacehub_api_token=config.api_key
    )
    return ChatHuggingFace(llm=llm, streaming=config.streaming)
```

```bash
# .env configuration
LLM_PROVIDER=huggingface
LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.2
LLM_API_KEY=your-hf-token
```

---

## 🔍 Finding Provider-Specific Parameters

Each provider may have unique parameters. Check the LangChain documentation:

1. **Visit LangChain Docs:** https://python.langchain.com/docs/integrations/chat/
2. **Find your provider** (e.g., "Mistral AI")
3. **Check the constructor parameters:**

```python
# Example from Mistral AI docs
ChatMistralAI(
    model="mistral-large-latest",
    temperature=0.0,
    mistral_api_key="your-key",
    streaming=True,
    max_tokens=None,         # Optional: max output tokens
    safe_mode=False,         # Optional: enable content filtering
    random_seed=None,        # Optional: reproducibility
)
```

**Common Optional Parameters:**
- `max_tokens`: Maximum output length
- `top_p`: Nucleus sampling parameter
- `timeout`: Request timeout
- `max_retries`: Retry failed requests
- `base_url`: Custom API endpoint (self-hosted)

Add these to `LLMConfig` if needed:

```python
@dataclass
class LLMConfig:
    provider: str
    model: str
    temperature: float
    api_key: str
    streaming: bool = False
    max_tokens: Optional[int] = None  # Add optional params
    base_url: Optional[str] = None
```

---

## 📝 Quick Reference Checklist

- [ ] Install LangChain package: `pip install langchain-{provider}`
- [ ] Update `pyproject.toml` dependencies
- [ ] Add provider to `config.py` → `chatLLM()` function
- [ ] Update `.env.example` with provider configuration
- [ ] Update `docs/LLM_PROVIDERS.md` with provider documentation
- [ ] Test with your Neo4j database
- [ ] Update error message in `chatLLM()` to include new provider
- [ ] Commit changes to git

---

## 🛠️ Troubleshooting

### Issue: "Unknown provider: myProvider"

**Solution:** Update the error message in `config.py`:

```python
else:
    raise ValueError(
        f"Unknown provider: {config.provider}. "
        f"Supported providers: openai, anthropic, google-genai, mistralai, groq, ollama"
    )
```

---

### Issue: "Module not found: langchain_provider"

**Solution:** Install the package and rebuild:

```bash
pip install langchain-provider
# or
uv pip install langchain-provider

# If using Docker, rebuild the image
docker compose build
```

---

### Issue: "API key invalid"

**Solution:** Check the API key parameter name in the provider's documentation:

```python
# Common patterns:
openai_api_key=config.api_key      # OpenAI
anthropic_api_key=config.api_key   # Anthropic
google_api_key=config.api_key      # Google
mistral_api_key=config.api_key     # Mistral AI
groq_api_key=config.api_key        # Groq
cohere_api_key=config.api_key      # Cohere
huggingfacehub_api_token=config.api_key  # Hugging Face (different!)
```

---

### Issue: "Streaming not working"

**Solution:** Ensure:
1. `streaming=config.streaming` is passed to the chat model
2. Your MCP transport supports streaming (HTTP mode recommended)
3. The provider supports streaming (check their docs)

---

## 🌟 Recommended Providers for Cypher Generation

Based on our testing, these providers work well for Neo4j Cypher query generation:

### 🥇 Best for Production

1. **Claude Sonnet 4.5** (Anthropic) - World's best coding model
2. **GPT-4o** (OpenAI) - Excellent instruction-following
3. **Gemini 2.5 Flash** (Google) - Great balance of speed and quality

### 💰 Best for Cost

1. **Gemini 2.5 Flash** (Google) - Fast and cheap
2. **GPT-4o-mini** (OpenAI) - Budget-friendly
3. **Ollama** (Local) - Free, runs on your hardware

### ⚡ Best for Speed

1. **Groq** - Same models, 10x faster inference
2. **Gemini 2.5 Flash** - Optimized for speed
3. **Ollama** - Local, no network latency

### 🔒 Best for Privacy

1. **Ollama** - Fully local, no data leaves your machine
2. **Azure OpenAI** - Enterprise compliance, data residency
3. **Self-hosted models** - Full control

---

## 📚 Additional Resources

- **LangChain Chat Model Integrations:** https://python.langchain.com/docs/integrations/chat/
- **LangChain Provider List:** https://python.langchain.com/docs/integrations/providers/
- **Neo4j YASS MCP Main Docs:** [README.md](../README.md)
- **LLM Provider Config Guide:** [LLM_PROVIDERS.md](LLM_PROVIDERS.md)

---

## 🤝 Contributing Your Provider

If you add a popular provider, consider contributing back:

1. Fork the repository
2. Add your provider following this guide
3. Test thoroughly
4. Update documentation
5. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

---

**Happy integrating!** 🚀

If you run into issues or have questions, please open an issue on GitHub.
