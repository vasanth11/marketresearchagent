# Market Research Agent — Competitor Analysis

Project 3A (Mastering Agentic AI Certification, Week 3). A multi-agent system that takes a company name and produces a structured competitor-analysis briefing: top 3 competitors, pricing, core features, market positioning, and recent news for each — with a simple Streamlit front end.

**Build track:** no-code (n8n) + Streamlit UI.

## One-liner

My agent helps a PM, consultant, analyst or founder do competitor research and briefing in a simple Streamlit web app, replacing the 4-6 hours of manual googling, tab-juggling, and note-taking it takes to size up a competitive landscape today. It does competitor discovery, data gathering, and structured extraction on its own using 5 tools (Tavily web search, Tavily news search, and 3 LLM calls), hands off to a human to review the briefing before saving, exporting, or sharing it, and I'll know it works when a user can get a usable competitor briefing for 3 competitors in under 3 minutes, with correct (non-hallucinated) data for at least 8 of 10 test companies.

## Architecture

Pipeline with an orchestrator, all inside one n8n workflow triggered by a webhook:

```
Webhook (company_name)
  -> Normalize Input
  -> Agent 1: Tavily Search + LLM  -> identifies top 3 competitors
  -> [error branch: respond immediately if discovery fails]
  -> Split into 3 competitors, loop:
       Agent 2: Tavily web search + Tavily news search
       -> [fallback branch: mark "Data unavailable" if both come back empty]
       Agent 3: LLM -> extracts pricing, core_features, market_positioning, recent_news (strict JSON)
  -> Aggregate all 3 competitor profiles
  -> Orchestrator: LLM -> compiles one Markdown briefing (exec summary, comparison table, per-competitor detail, data-limitations note)
  -> Respond to webhook
```

Every external call (Tavily, the LLM) has retry-on-fail and a graceful fallback, so one bad API response degrades a single competitor's data instead of failing the whole run.

## Stack

- **Workflow / agents:** n8n (`n8n_market_research_agent.json`)
- **Search:** [Tavily Search API](https://tavily.com) (`topic=general` for web data, `topic=news` for recent news)
- **LLM:** [Nebius Token Factory](https://tokenfactory.nebius.com) (OpenAI-compatible), model `Qwen/Qwen3-30B-A3B-Instruct-2507`
- **UI:** Streamlit (`streamlit_app.py`)

## Setup

### 1. n8n
1. Import `n8n_market_research_agent.json` into n8n (Cloud or self-hosted).
2. Get a Tavily API key at [app.tavily.com](https://app.tavily.com) and a Nebius Token Factory key at [tokenfactory.nebius.com](https://tokenfactory.nebius.com).
3. On n8n Cloud: **Settings -> Variables**, add `TAVILY_API_KEY` and `NEBIUS_API_KEY` with those values. (Self-hosted n8n can use real environment variables and `$env.` instead of `$vars.` in the node expressions.)
4. Confirm the model name in the three LLM HTTP nodes matches a model actually available on your Nebius account — list yours with:
   ```bash
   curl https://api.tokenfactory.nebius.com/v1/models -H "Authorization: Bearer <your-key>"
   ```
5. Flip the workflow to **Active** and copy the **production** webhook URL from the Webhook node (path `/webhook/market-research`, not `/webhook-test/...`).

### 2. Streamlit
```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```
Paste your production webhook URL into the sidebar (or edit the `default_url` in `streamlit_app.py` to hardcode it). Type a company name and click **Run Research**.

> **Corporate network note:** if requests fail with `SSLError: self signed certificate in certificate chain`, that's an SSL-inspecting corporate proxy — fix with `python -m pip install pip-system-certs` (then restart the app), or use the "Skip SSL verification" checkbox in the sidebar as a fallback for local testing only.

## Sample output

See `Project_3A_Documentation.docx` for the filled agent framework, full architecture writeup, and a sample competitor briefing.

## Notes on the build

The handout's suggested search provider was you.com. During build/testing, you.com's API returned a persistent `403 Forbidden` on every server-to-server call (n8n Cloud and local curl alike), while working fine through you.com's own browser-based docs tester — which ruled out the API key and pointed at a bot/IP-level block on their side that couldn't be resolved before the deadline. The workflow was switched to Tavily instead: same architecture, same Agent 1/2/3 roles, purpose-built for agent/automation traffic.

Two other fixes made along the way:
- Nebius Token Factory's actual endpoint is `https://api.tokenfactory.nebius.com/v1/chat/completions` (not `api.studio.nebius.ai`), and the model ID has to be one that's actually enabled on your account — checked via `GET /v1/models`.
- Tavily's response shape (`results` as a flat array) differs from you.com's original nested `{results: {web, news}}` shape, which required a small type fix in the two "Label Web/News Results" Set nodes.
