# MRD Agent v2.0

AI-powered Market Requirements Document (MRD) generator with LangGraph orchestration.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Check environment
python main.py --check

# Run tests
python main.py --test

# Start CLI mode
python main.py

# Start API server
python main.py --api
```

## Task 4 Requirements Met

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| LangGraph StateGraph | ✅ | `src/agents/orchestrator.py` |
| Pydantic models (100%) | ✅ | `src/models/` |
| Human-in-the-loop | ✅ | Research plan approval |
| Self-correction loop | ✅ | QA → Research if confidence < 0.7 |
| Company disambiguation | ✅ | triumpharcade.com not Triumph Motorcycles |
| App Store review mining | ✅ | `src/tools/app_reviews.py` |
| TikTok/Influencer data | ✅ | `src/tools/influencer.py` |
| Regulatory compliance | ✅ | UK/EU gambling laws |
| Data quality validation | ✅ | $, €, Billion keyword checks |

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

## Project Structure

```
mrd-agent/
├── main.py                 # Entry point (CLI, API, tests)
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project configuration
├── .env                    # API keys (create from .env.example)
│
├── src/
│   ├── models/             # 100% Pydantic models
│   │   ├── companies.py    # Verified company database
│   │   ├── mrd.py          # MRD output structure
│   │   └── state.py        # LangGraph state
│   │
│   ├── agents/             # LangGraph orchestration
│   │   ├── orchestrator.py # StateGraph implementation
│   │   ├── researchers.py  # Market/Competitor/Regulatory agents
│   │   ├── synthesizer.py  # MRD synthesis
│   │   └── human_review.py # Human-in-the-loop
│   │
│   ├── tools/              # Research tools
│   │   ├── web_search.py   # Perplexity, Tavily
│   │   ├── web_scraping.py # Firecrawl, Jina
│   │   ├── sentiment.py    # Sentiment analysis
│   │   ├── regulatory.py   # Compliance checking
│   │   ├── app_reviews.py  # App Store/Google Play
│   │   └── influencer.py   # TikTok/Instagram/YouTube
│   │
│   └── utils/
│       ├── cost.py         # API cost tracking
│       └── validation.py   # Data quality checks
│
├── api/
│   └── main.py             # FastAPI backend
│
└── frontend/
    ├── index.html          # Web UI
    ├── styles.css
    └── app.js
```

## Environment Variables

Create a `.env` file:

```env
# Required
OPENAI_API_KEY=sk-...

# Recommended
PERPLEXITY_API_KEY=pplx-...
FIRECRAWL_API_KEY=fc-...

# Optional
TAVILY_API_KEY=tvly-...
SERPAPI_KEY=...
```

## Usage Examples

### CLI Mode
```bash
python main.py
# Follow prompts, approve research plan, review output
```

### API Mode
```bash
python main.py --api
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Programmatic Usage
```python
import asyncio
from src.agents.orchestrator import run_mrd_agent

async def generate_mrd():
    result = await run_mrd_agent(
        prompt="Competitive analysis of Triumph vs Skillz",
        domain="gambling"
    )
    print(result.to_json())

asyncio.run(generate_mrd())
```

## Focus Companies

This agent is configured to research:

1. **Triumph** (triumpharcade.com) - Real-money skill gaming app
2. **Skillz** (skillz.com) - Mobile esports platform (SKLZ)

The company database ensures searches target the correct entities:
- ❌ NOT Triumph Motorcycles
- ❌ NOT Skillz training platforms
- ✅ Real-money gaming companies only

## Output Format

The MRD output includes (all Pydantic validated):

- **Strategic Analysis**: Executive summary, market size, target audience
- **Competitor Profiles**: Strengths, weaknesses, positioning
- **SWOT Analysis**: Minimum 2 items per category
- **Feature Recommendations**: Minimum 3 recommendations
- **Regulatory Assessment**: UK, EU, US jurisdiction status
- **Gap Analysis**: Market opportunities

## Development

```bash
# Run tests
python main.py --test

# Check environment
python main.py --check

# View help
python main.py --help
```

## License

MIT License

## Author

MRD Agent Team - Task 4 Implementation
