# LLM Provider Configuration Guide

Complete reference for configuring LLM providers in Neo4j YASS MCP.

---

## 🎯 Quick Reference

> **Updated: October 2025** - Models reflect latest available versions

| Provider | Package | Provider Name | Current Models (Oct 2025) |
|----------|---------|---------------|---------------------------|
| **OpenAI** | `langchain-openai` | `openai` | `gpt-4o`, `gpt-4o-mini`, `o3`, `o4-mini` |
| **Anthropic** | `langchain-anthropic` | `anthropic` | `claude-sonnet-4-5`, `claude-opus-4-1`, `claude-haiku-4-5` |
| **Google** | `langchain-google-genai` | `google-genai` | `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.0-flash` |

---

## 📝 Important: Provider Names vs Package Names

### ⚠️ Common Confusion

The **Python package name** is different from the **provider configuration value**:

| Python Package | Config Provider Name | ✅/❌ |
|----------------|---------------------|-------|
| `langchain-google-genai` | `google-genai` | ✅ Correct |
| `langchain-google-genai` | `google` | ❌ Wrong |
| `langchain-google-genai` | `gemini` | ❌ Wrong |
| `langchain-openai` | `openai` | ✅ Correct |
| `langchain-anthropic` | `anthropic` | ✅ Correct |

### Example

```bash
# ❌ WRONG - This will NOT work
LLM_PROVIDER=gemini
LLM_PROVIDER=google

# ✅ CORRECT - Use this
LLM_PROVIDER=google-genai
```

---

## 1️⃣ Google Generative AI (Gemini)

### Configuration

```bash
# .env file
LLM_PROVIDER=google-genai         # ⚠️ Use "google-genai", not "gemini" or "google"
LLM_MODEL=gemini-2.5-flash        # Model name (latest stable as of Oct 2025)
LLM_TEMPERATURE=0.0
LLM_API_KEY=AIzaSy...             # Starts with "AIzaSy"
```

### Available Models (Updated October 2025)

| Model | Context | Speed | Best For | Status |
|-------|---------|-------|----------|--------|
| `gemini-2.5-pro` | 1M tokens | Medium | Most complex analytical workloads, adaptive thinking | ✅ GA |
| `gemini-2.5-flash` | 1M tokens | Very Fast | Balanced quality & efficiency (recommended) | ✅ GA |
| `gemini-2.5-flash-lite` | 1M tokens | Ultra Fast | Fast, low-cost, high-performance | ✅ GA |
| `gemini-2.0-flash` | 1M tokens | Very Fast | Enhanced conversational style | ✅ GA |
| `gemini-1.5-pro` | 2M tokens | Medium | Long documents (legacy) | ⚠️ Legacy |
| `gemini-1.5-flash` | 1M tokens | Fast | Legacy fast model | ⚠️ Legacy |

**Recommended for Production:** `gemini-2.5-flash` (best balance) or `gemini-2.5-pro` (most powerful)

### Get API Key

1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Get API key"
4. Copy key (starts with `AIzaSy...`)

### Code Reference

In [config.py:181-187](../config.py):

```python
elif config.provider == "google-genai":  # ⚠️ Must be "google-genai"
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=config.model,
        temperature=config.temperature,
        google_api_key=config.api_key
    )
```

---

## 2️⃣ OpenAI (GPT & Reasoning Models)

### Configuration

```bash
# .env file
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o                  # Latest general-purpose model (Oct 2025)
LLM_TEMPERATURE=0.0
LLM_API_KEY=sk-...                # Starts with "sk-"
```

### Available Models (Updated October 2025)

| Model | Context | Cost | Best For | Status |
|-------|---------|------|----------|--------|
| `gpt-4o` | 128k tokens | $$$ | General tasks, multimodal, smarter coding (recommended) | ✅ GA |
| `gpt-4o-mini` | 128k tokens | $ | Fast, cost-effective, high volume | ✅ GA |
| `o3` | 128k tokens | $$$$ | Most powerful reasoning (coding, math, science, vision) | ✅ GA |
| `o4-mini` | 128k tokens | $$ | Fast, cost-efficient reasoning, best AIME benchmark | ✅ GA |
| `o1` | 128k tokens | $$$$ | Legacy reasoning model | ⚠️ Legacy |
| `gpt-4-turbo` | 128k tokens | $$$ | Legacy general-purpose | ⚠️ Deprecated |

**Recommended for Production:**
- General tasks: `gpt-4o` (improved instruction-following, extended knowledge cutoff to June 2024)
- Reasoning tasks: `o3` (most powerful) or `o4-mini` (cost-effective)

**Note:** Reasoning models (o3, o4-mini) can now use all ChatGPT tools including web search, Python analysis, visual reasoning, and image generation.

### Get API Key

1. Visit: https://platform.openai.com/api-keys
2. Sign in / create account
3. Click "Create new secret key"
4. Copy key (starts with `sk-...`)

### Code Reference

In [config.py:165-171](../config.py):

```python
if config.provider == "openai":
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=config.model,
        temperature=config.temperature,
        openai_api_key=config.api_key
    )
```

---

## 3️⃣ Anthropic (Claude 4.x Family)

### Configuration

```bash
# .env file
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5       # Latest model (Oct 2025)
LLM_TEMPERATURE=0.0
LLM_API_KEY=sk-ant-...            # Starts with "sk-ant-"
```

### Available Models (Updated October 2025)

| Model | Context | Cost | Best For | Status |
|-------|---------|------|----------|--------|
| `claude-sonnet-4-5` | 200k tokens | $$$ | Best coding & agentic tasks (recommended) | ✅ GA |
| `claude-opus-4-1` | 200k tokens | $$$$ | Real-world coding, reasoning, agentic precision | ✅ GA |
| `claude-haiku-4-5` | 200k tokens | $ | Fast, cost-effective, near-frontier intelligence | ✅ GA |
| `claude-3-5-sonnet-20241022` | 200k tokens | $$ | Legacy Sonnet 3.x | ⚠️ Legacy |
| `claude-3-opus-20240229` | 200k tokens | $$$ | Legacy Opus 3 | ⚠️ Legacy |

**Recommended for Production:**

- **Coding & agents:** `claude-sonnet-4-5` - World's best coding model, strongest for complex agents
- **Agentic tasks:** `claude-opus-4-1` - Superior for real-world coding, can work continuously for hours
- **Cost-effective:** `claude-haiku-4-5` - Fast, outperforms larger legacy models

**Key Features:** All Claude 4.x models support hybrid reasoning (toggle between instant responses and extended thinking), text/image input, multilingual capabilities, and vision. Available via Anthropic API, AWS Bedrock, and Google Vertex AI.

### Get API Key

1. Visit: https://console.anthropic.com/settings/keys
2. Sign in / create account
3. Click "Create Key"
4. Copy key (starts with `sk-ant-...`)

### Code Reference

In [config.py:173-179](../config.py):

```python
elif config.provider == "anthropic":
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=config.model,
        temperature=config.temperature,
        anthropic_api_key=config.api_key
    )
```

---

## 🔧 Complete Configuration Examples

### Example 1: Google Gemini 2.5 Flash (Recommended)

```bash
# .env
LLM_PROVIDER=google-genai        # ⚠️ Correct provider name
LLM_MODEL=gemini-2.5-flash       # Latest stable (Oct 2025)
LLM_TEMPERATURE=0.0
LLM_API_KEY=AIzaSyDemoKey12345678901234567890

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your-password
```

### Example 2: OpenAI GPT-4o (Enhanced)

```bash
# .env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o                 # Improved Oct 2025 version
LLM_TEMPERATURE=0.0
LLM_API_KEY=sk-DemoKey1234567890abcdefghijklmnop

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your-password
```

### Example 3: Anthropic Claude Sonnet 4.5 (Best for Coding)

```bash
# .env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5      # World's best coding model
LLM_TEMPERATURE=0.0
LLM_API_KEY=sk-ant-DemoKey1234567890abcdefghijklmnop

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your-password
```

### Example 4: OpenAI o4-mini (Cost-Effective Reasoning)

```bash
# .env
LLM_PROVIDER=openai
LLM_MODEL=o4-mini                # Fast reasoning for Cypher generation
LLM_TEMPERATURE=0.0
LLM_API_KEY=sk-DemoKey1234567890abcdefghijklmnop

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your-password
```

---

## ❓ FAQ

### Q: Why "google-genai" and not "gemini"?

**A:** The LangChain package is called `langchain-google-genai`, so the provider name follows the package naming convention. "Google Generative AI" is the official name of the API that includes Gemini models.

```python
# LangChain uses this naming:
from langchain_google_genai import ChatGoogleGenerativeAI  # Package name
config.provider == "google-genai"  # Provider name matches package
```

### Q: Can I use "gemini" or "google" as the provider?

**A:** No, it will raise an error:

```python
ValueError: Unknown provider: gemini. Supported providers: openai, anthropic, google-genai
```

You must use **`google-genai`** exactly.

### Q: What temperature should I use?

**A:** For Cypher query generation, use **`0.0`** (deterministic):

```bash
LLM_TEMPERATURE=0.0  # ✅ Recommended for queries
LLM_TEMPERATURE=0.3  # ⚠️ Slightly creative
LLM_TEMPERATURE=0.7  # ❌ Too random for queries
```

### Q: How do I know if my API key is correct?

**A:** Check the prefix:

```bash
# OpenAI
echo $LLM_API_KEY | grep "^sk-"          # Should match

# Anthropic
echo $LLM_API_KEY | grep "^sk-ant-"      # Should match

# Google
echo $LLM_API_KEY | grep "^AIzaSy"       # Should match
```

### Q: Can I use multiple providers?

**A:** Not simultaneously, but you can switch by changing `.env`:

```bash
# Use Gemini 2.5
LLM_PROVIDER=google-genai
LLM_MODEL=gemini-2.5-flash
LLM_API_KEY=AIzaSy...

# Switch to GPT-4o (comment Gemini, uncomment OpenAI)
#LLM_PROVIDER=google-genai
#LLM_MODEL=gemini-2.5-flash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-...
```

### Q: Which model is best for Cypher query generation?

**A:** For deterministic Cypher query generation, recommended models (Oct 2025):

1. **Best Overall:** `claude-sonnet-4-5` - World's best coding model
2. **Cost-Effective:** `gpt-4o-mini` or `gemini-2.5-flash`
3. **Complex Reasoning:** `o3` or `claude-opus-4-1`

Always use `LLM_TEMPERATURE=0.0` for deterministic query generation.

---

## 🐛 Troubleshooting

### Error: "Unknown provider: gemini"

```bash
# ❌ Wrong
LLM_PROVIDER=gemini

# ✅ Fix
LLM_PROVIDER=google-genai
```

### Error: "Unknown provider: google"

```bash
# ❌ Wrong
LLM_PROVIDER=google

# ✅ Fix
LLM_PROVIDER=google-genai
```

### Error: "API key invalid"

Check your API key format:

```bash
# Google - should start with AIzaSy
LLM_API_KEY=AIzaSy...

# OpenAI - should start with sk-
LLM_API_KEY=sk-...

# Anthropic - should start with sk-ant-
LLM_API_KEY=sk-ant-...
```

### Error: "Model not found"

Make sure model name is correct (October 2025):

```bash
# ✅ Correct Gemini models (current)
LLM_MODEL=gemini-2.5-pro
LLM_MODEL=gemini-2.5-flash
LLM_MODEL=gemini-2.0-flash

# ✅ Correct OpenAI models (current)
LLM_MODEL=gpt-4o
LLM_MODEL=o3
LLM_MODEL=o4-mini

# ✅ Correct Anthropic models (current)
LLM_MODEL=claude-sonnet-4-5
LLM_MODEL=claude-opus-4-1
LLM_MODEL=claude-haiku-4-5

# ❌ Wrong
LLM_MODEL=gemini  # Too vague
LLM_MODEL=google-gemini  # Wrong prefix
LLM_MODEL=claude-4  # Missing tier specification
```

---

## 📚 Additional Resources

### Official Documentation

- **Google AI**: https://ai.google.dev/docs
- **OpenAI**: https://platform.openai.com/docs
- **Anthropic**: https://docs.anthropic.com/

### LangChain Integration Docs

- **Google GenAI**: https://python.langchain.com/docs/integrations/llms/google_ai
- **OpenAI**: https://python.langchain.com/docs/integrations/llms/openai
- **Anthropic**: https://python.langchain.com/docs/integrations/llms/anthropic

### Getting API Keys

- **Google AI Studio**: https://makersuite.google.com/app/apikey
- **OpenAI Platform**: https://platform.openai.com/api-keys
- **Anthropic Console**: https://console.anthropic.com/settings/keys

---

## ✅ Summary (October 2025)

| Provider | Config Value | Package Name | Key Prefix | Recommended Models |
|----------|-------------|--------------|------------|-------------------|
| **Google** | `google-genai` | `langchain-google-genai` | `AIzaSy` | `gemini-2.5-flash`, `gemini-2.5-pro` |
| **OpenAI** | `openai` | `langchain-openai` | `sk-` | `gpt-4o`, `o4-mini`, `o3` |
| **Anthropic** | `anthropic` | `langchain-anthropic` | `sk-ant-` | `claude-sonnet-4-5`, `claude-haiku-4-5` |

**Key Points:**

- ✅ Always use **`google-genai`** for Google's Gemini models, not "gemini" or "google"
- ✅ Use temperature `0.0` for deterministic Cypher query generation
- ✅ Claude Sonnet 4.5 is the world's best coding model (as of Oct 2025)
- ✅ All current models support extended context (128k-2M tokens)
