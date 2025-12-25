# Autonomous Product Strategy Agent

An AI-powered autonomous agent that generates comprehensive Market Requirements Documents (MRDs) using LangGraph orchestration, multi-source research, and intelligent synthesis.

## Overview

The Autonomous Product Strategy Agent automates the process of competitive analysis and market research by:

- Conducting multi-source web research using AI-powered search tools
- Mining app store reviews for sentiment and feature insights
- Analyzing influencer and social media presence
- Evaluating regulatory compliance across jurisdictions
- Synthesizing findings into professional MRD reports with PDF export

## Features

- **LangGraph Orchestration**: Stateful agent workflow with human-in-the-loop approval
- **Multi-LLM Support**: OpenAI GPT-4, Groq, and fallback providers
- **Intelligent Research**: Perplexity, Tavily, Firecrawl, and Jina AI integration
- **App Store Mining**: Apple App Store and Google Play review analysis via SerpAPI
- **Sentiment Analysis**: Cohere-powered sentiment classification
- **Regulatory Assessment**: UK/EU gambling and fintech compliance checking
- **Quality Assurance**: Self-correction loop with confidence scoring
- **PDF Generation**: Professional report output with ReportLab

## Architecture

```
┌──────────┐     ┌──────────────┐     ┌──────────┐
│   INIT   │────▶│ HUMAN_REVIEW │────▶│ RESEARCH │
└──────────┘     └──────────────┘     └────┬─────┘
                                          │
                        ┌─────────────────┘
                        ▼
               ┌──────────────┐     ┌──────────┐
               │  SYNTHESIZE  │────▶│    QA    │
               └──────────────┘     └────┬─────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
             confidence >= 0.7    confidence < 0.7     max iterations
                    │              (loop back)               │
                    ▼                    │                   ▼
               ┌──────────┐              │              ┌──────────┐
               │  OUTPUT  │◀─────────────┘              │  OUTPUT  │
               └──────────┘                             └──────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Check environment configuration
python main.py --check

# Start interactive CLI mode
python main.py

# Start API server
python main.py --api
```

## Project Structure

```
autonomous-product-strategy-agent/
├── main.py                 # Entry point (CLI, API modes)
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project configuration
├── .env                    # API keys (create from template below)
│
├── src/
│   ├── models/             # Pydantic data models
│   │   ├── companies.py    # Verified company database
│   │   ├── mrd.py          # MRD output structure
│   │   └── state.py        # LangGraph state management
│   │
│   ├── agents/             # LangGraph orchestration
│   │   ├── orchestrator.py # StateGraph implementation
│   │   ├── researchers.py  # Market/Competitor/Regulatory agents
│   │   ├── synthesizer.py  # MRD synthesis engine
│   │   └── human_review.py # Human-in-the-loop approval
│   │
│   ├── tools/              # Research tools
│   │   ├── web_search.py   # Perplexity, Tavily integration
│   │   ├── web_scraping.py # Firecrawl, Jina AI scraping
│   │   ├── sentiment.py    # Cohere sentiment analysis
│   │   ├── regulatory.py   # Compliance checking
│   │   ├── app_reviews.py  # App Store/Google Play mining
│   │   └── influencer.py   # Social media analysis
│   │
│   ├── llm/
│   │   └── multi_llm.py    # Multi-provider LLM management
│   │
│   ├── output/
│   │   └── pdf_generator.py # Professional PDF reports
│   │
│   └── utils/
│       ├── cost.py         # API cost tracking
│       ├── progress.py     # Progress indicators
│       └── validation.py   # Data quality checks
│
├── api/
│   └── main.py             # FastAPI backend
│
└── frontend/
    ├── index.html          # Web UI
    ├── styles.css          # Styling
    └── app.js              # Frontend logic
```

## Environment Configuration

Create a `.env` file in the project root:

```env
# Required - Primary LLM
OPENAI_API_KEY=sk-...

# Recommended - Enhanced Search
PERPLEXITY_API_KEY=pplx-...
FIRECRAWL_API_KEY=fc-...
TAVILY_API_KEY=tvly-...

# Optional - Extended Features
SERPAPI_KEY=...              # App store reviews
COHERE_API_KEY=...           # Sentiment analysis
GROQ_API_KEY=gsk_...         # Alternative LLM
EXA_API_KEY=...              # Semantic search
JINA_API_KEY=jina_...        # Web scraping fallback
```

## Usage

### Interactive CLI Mode

```bash
python main.py
```

Follow the prompts to:
1. Enter your research request
2. Review and approve the generated research plan
3. Monitor research progress
4. Receive the final MRD report (Markdown, JSON, and PDF)

### API Mode

```bash
python main.py --api
```

- API server runs at `http://localhost:8000`
- Interactive documentation at `http://localhost:8000/docs`
- OpenAPI spec at `http://localhost:8000/openapi.json`

### Programmatic Usage

```python
import asyncio
from src.agents.orchestrator import run_mrd_agent

async def generate_mrd():
    result = await run_mrd_agent(
        prompt="Competitive analysis for mobile gaming market",
        domain="gaming"
    )
    print(result.to_json())

asyncio.run(generate_mrd())
```

## Output Format

The generated MRD includes:

- **Executive Summary**: High-level strategic overview
- **Market Analysis**: Size, growth, trends, and target audience
- **Competitor Profiles**: Detailed analysis with strengths/weaknesses
- **SWOT Analysis**: Comprehensive strategic assessment
- **Feature Recommendations**: Prioritized feature suggestions
- **Regulatory Assessment**: Jurisdiction-specific compliance status
- **Gap Analysis**: Market opportunities and differentiation strategies
- **App Store Insights**: User sentiment and feature requests from reviews

## Technology Stack

| Component | Technologies |
|-----------|-------------|
| Orchestration | LangGraph, LangChain |
| LLM Providers | OpenAI GPT-4, Groq, Anthropic |
| Web Search | Perplexity, Tavily, Exa |
| Web Scraping | Firecrawl, Jina AI |
| Sentiment | Cohere |
| App Reviews | SerpAPI |
| PDF Generation | ReportLab |
| API Framework | FastAPI |
| Data Validation | Pydantic |

## License

MIT License

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.
