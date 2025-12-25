# MRD Agent - Design Rationale ("The Why")

**Document Version:** 1.0  
**Date:** December 23, 2025  
**Author:** MRD Agent Development Team

---

## Table of Contents

1. [Why This Orchestration Pattern](#1-why-this-orchestration-pattern)
2. [Handling Hallucinations](#2-handling-hallucinations)
3. [Key Architectural Decisions](#3-key-architectural-decisions)
4. [Trade-offs and Alternatives Considered](#4-trade-offs-and-alternatives-considered)

---

## 1. Why This Orchestration Pattern

### Choice: LangGraph StateGraph with Pydantic State Management

We chose **LangGraph's StateGraph** pattern over alternatives like:
- Simple sequential chains (CrewAI Process.sequential)
- Multi-agent swarms (AutoGen)
- Pure DAG executors (Prefect, Airflow)

**Reasons:**

#### 1.1 State Machine Clarity
```
INIT → HUMAN_REVIEW → RESEARCH → CHECK → SYNTHESIZE → QA → OUTPUT
                          ↑                           │
                          └───── (if confidence < 0.7) ──┘
```

The StateGraph provides:
- **Explicit transitions**: Each node function returns state updates, making data flow traceable
- **Conditional routing**: `should_continue_after_qa()` decides whether to loop back
- **Observability**: State can be inspected at any node for debugging

#### 1.2 Self-Correction Loop (Task 4 Requirement)
The key question from Task 4: *"How does the agent correct itself if a tool fails or returns empty data?"*

**Our Answer:**
```python
def should_continue_after_qa(state: dict) -> str:
    """Loop back if confidence < 0.7 and iterations < max."""
    if mrd_state.confidence_score >= 0.7:
        return "output"
    elif mrd_state.iteration < mrd_state.max_iterations:
        return "research"  # Loop back for more data
    else:
        return "output"  # Graceful degradation
```

This is only possible with a graph-based orchestrator where nodes can have conditional outgoing edges.

#### 1.3 Human-in-the-Loop Integration
Task 4 requires: *"Show where the Human in the Loop sits"*

StateGraph makes this natural:
```python
workflow.add_edge("init", "human_review")
workflow.add_conditional_edges("human_review", should_continue_after_review)
```

The human reviews the research plan BEFORE execution, not after.

#### 1.4 Pydantic Type Safety
Unlike TypedDict-based approaches, we use Pydantic models for state:
- Validation happens on every state update
- Fields like `confidence_score: float = Field(ge=0.0, le=1.0)` prevent invalid data
- Serialization to JSON is automatic and guaranteed valid

---

## 2. Handling Hallucinations

### The Problem
Task 4 asks: *"How would you handle a hallucination (e.g., if the agent invents a competitor that doesn't exist)?"*

Real risks we address:
1. LLM invents a company (e.g., "GameSkillz Pro" that doesn't exist)
2. LLM confuses "Triumph" gaming app with Triumph Motorcycles
3. LLM fabricates financial data or app store ratings
4. LLM generates placeholder text like "[NEEDS VERIFICATION]"

### Our Multi-Layer Defense

#### Layer 1: Verified Company Database (Ground Truth)
```python
# src/models/companies.py
TRIUMPH = VerifiedCompany(
    id="triumph",
    official_name="Triumph Labs, Inc.",
    website="https://triumpharcade.com",
    disambiguation="NOT Triumph Motorcycles"
)
```

The agent can ONLY research pre-verified companies. Any mention of an unverified competitor is flagged.

#### Layer 2: Source Tracking (Every claim needs a source)
```python
class DataSource(BaseModel):
    url: Optional[str]  # Where did this come from?
    source_type: str    # "web_search", "app_store", etc.
    confidence: ConfidenceLevel
```

Claims without sources receive `ConfidenceLevel.UNVERIFIED`.

#### Layer 3: Data Quality Validation
```python
# src/utils/data_validator.py
class DataQualityValidator:
    def validate_no_placeholders(self, value: str) -> ValidationResult:
        """Detect [PLACEHOLDER], [NEEDS VERIFICATION], etc."""
        
    def validate_rating(self, rating: float) -> ValidationResult:
        """Ensure 0.0 <= rating <= 5.0"""
        
    def validate_revenue(self, revenue: float) -> ValidationResult:
        """Ensure positive, reasonable range"""
```

#### Layer 4: Website Scraping for Ground Truth
Before LLM synthesis, we scrape official websites:
```python
# In research node
await scrape_firecrawl(TRIUMPH.website)  # Get real data first
await scrape_firecrawl(SKILLZ.website)
```

This establishes facts that the LLM must respect.

#### Layer 5: Confidence Scoring
The QA node calculates a confidence score based on:
- Presence of required sections
- Data quality validation results
- Source availability
- Placeholder detection

If `confidence_score < 0.7`, the agent loops back for more research.

---

## 3. Key Architectural Decisions

### 3.1 Why Pydantic over TypedDict?
Task 4 explicitly requires: *"Use Pydantic models to define the interface between agent steps"*

| Feature | TypedDict | Pydantic |
|---------|-----------|----------|
| Runtime validation | ❌ No | ✅ Yes |
| Default values | ❌ No | ✅ Yes |
| Field constraints | ❌ No | ✅ Yes (ge=0, le=5, min_length, etc.) |
| Serialization | Manual | Automatic |
| IDE autocomplete | Partial | Full |

### 3.2 Why Multiple Search Tools?
We use Perplexity, Tavily, Exa, and Firecrawl because:
- **No single tool is reliable** - APIs fail, rate limit, or return empty
- **Different tools excel at different queries** - Exa for neural search, Tavily for structured data
- **Fallback chains** - If tool A fails, try tool B

```python
# src/tools/web_search.py
async def search_with_fallback(query: str) -> SearchResult:
    """Try multiple providers in sequence."""
```

### 3.3 Why Domain-Specific Company Verification?
Without verification, searches for "Triumph" return:
- Triumph Motorcycles (UK motorcycle manufacturer)
- Triumph Insulation (Texas insulation company)
- Triumph Group (aerospace company)

Our `VerifiedCompany` model enforces:
```python
TRIUMPH = VerifiedCompany(
    id="triumph",
    website="https://triumpharcade.com",  # MUST be this domain
    disambiguation="NOT Triumph Motorcycles, NOT Triumph Group"
)
```

### 3.4 Why Multi-LLM Provider Strategy?
We implemented a dynamic provider selection strategy (`src/llm/multi_llm.py`) because:
- **Rate Limits Happen**: During testing, Gemini Free Tier hit 429 errors.
- **Strength Alignment**: 
  - OpenAI/Groq for structured Pydantic extraction (JSON mode reliability)
  - Gemini/Claude for long-context prose synthesis
- **Automatic Fallback**: If `gpt-4o` fails, system tries `gemini-2.0-flash`, then `llama-3.1`.

### 3.5 Why Redundant App Store Mining?
Task 4 asks for specific competitor insights from reviews. We use a dual-layer strategy (`src/tools/app_reviews.py`):
1.  **Primary**: SerpAPI to get structured JSON from Apple App Store / Google Play.
2.  **Fallback**: If SerpAPI fails (or returns 0 results), we fall back to web search ("Triumph app reviews site:reddit.com").
3.  **Specific Targeting**: We specifically mine 1-star reviews to find "gaps" (bugs, complaints) that generic summaries miss.
4.  **Zombie Detection**: We automatically flag apps with low review counts as `is_zombie_app` to avoid analyzing dead competitors.

---

## 4. Trade-offs and Alternatives Considered

### 4.1 Why Not Multi-Agent Swarm (AutoGen)?
- **Pro**: Agents can debate and verify each other
- **Con**: Unpredictable execution paths, harder to debug
- **Decision**: StateGraph is more deterministic for production use

### 4.2 Why Not Pure Chain (LangChain LCEL)?
- **Pro**: Simpler to implement
- **Con**: No conditional loops, no state persistence
- **Decision**: We need self-correction loops (Task 4 requirement)

### 4.3 Why Not RAG-only Approach?
- **Pro**: Grounds all answers in retrieved documents
- **Con**: Can't synthesize novel insights, limited to existing knowledge
- **Decision**: We use RAG for facts, LLM for synthesis

### 4.4 Why Not Fully Autonomous (No Human)?
- **Pro**: Faster execution
- **Con**: Task 4 explicitly requires human-in-the-loop
- **Decision**: Human approves research plan before execution

---

## Summary

The MRD Agent architecture prioritizes:

1. **Reliability** over speed (multiple fallback tools)
2. **Traceability** over magic (every claim has a source)
3. **Type safety** over flexibility (Pydantic everywhere)
4. **Human oversight** over full autonomy (approval checkpoints)
5. **Self-correction** over single-pass (confidence-based loops)

This makes the system suitable for production use where "vibes" are not acceptable—only verified, structured, source-backed data.

---

*This document addresses Task 4 Deliverable #3: "Short Write-up (The Why)"*
