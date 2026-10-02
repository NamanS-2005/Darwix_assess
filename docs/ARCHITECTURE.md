# Architecture

```mermaid
flowchart LR
  subgraph Q2[Q2 · Knowledge base build]
    S[Raw sources<br/>HTML · PDF · CSV · forms · notes · md] --> X[Extract<br/>boilerplate removal, OCR/JS flags]
    X --> N[Normalise<br/>dates · currency · terms · headings]
    N --> P[PII redaction]
    P --> C[Classify + chunk<br/>taxonomy, Q&A / row / section units]
    C --> D[Dedupe + version<br/>near-dup, superseded]
    D --> F[Conflict reconcile<br/>authority ranking]
    F --> R[(records.jsonl<br/>manifest · changelog)]
    R --> I[BM25 index + Gemini embeddings]
  end

  subgraph RT[Runtime retrieval]
    I --> H[Hybrid search<br/>filters → BM25 + dense → RRF → abstain gate]
    H --> G[Grounded answer<br/>NOT_IN_KB fallback, citations]
  end

  subgraph Q1Q3[Q1 + Q3 · Voice agent engine]
    MIC[Browser mic / Vapi phone] --> ASR[Groq Whisper<br/>market-specific language + vocab prompt]
    ASR --> E[Call session<br/>LLM tool loop · Groq Llama 3.3 70B → Gemini fallback]
    E -- search_knowledge_base --> H
    E -- verify / loan details / PTP / paid / callback / escalate / end --> T[Tools = business rules in code<br/>mock CRM · escalation webhook]
    E --> GU[Grounding guard<br/>numbers must exist in KB/CRM/tool output]
    GU --> TTS[Neural TTS<br/>en-IN · fil-PH · id-ID voices]
    TTS --> MIC
    E --> REC[(transcript.md · call.json · recording.mp3 · stereo.wav)]
  end

  subgraph Q4[Q4 · Live insights]
    A[Live audio / real-time replay<br/>100 ms chunks, stereo = speaker] --> V[VAD endpointing per channel]
    V --> SA[Streaming ASR<br/>Whisper turbo per utterance]
    SA --> RU[Tier 1 rules + call-state<br/>µs, compliance fast path]
    SA --> LL[Tier 2 LLM<br/>Llama 3.1 8B JSON: signals, intent, frustration]
    RU --> NE[Nudge engine<br/>threshold · corroboration · grouping · cooldown · TTL · priority]
    LL --> NE
    NE --> WS[WebSocket dashboard / CLI]
  end
  REC -. stereo recordings reusable .-> A
```

## Key design decisions

| Decision | Why | Trade-off |
|---|---|---|
| One engine for web UI and Vapi (`custom-llm` endpoint) | Same tools, KB grounding and guards on every channel; Vapi only adds telephony, barge-in, ASR/TTS | Requires a public URL (tunnel) for Vapi |
| Business rules in tools, not in the prompt | Verification, PTP classification, callback windows, disposition are deterministic and testable | More code than a prompt-only bot |
| KB retrieved per question via a tool | Satisfies "do not hardcode FAQs"; answers carry citations; KB updates need no prompt change | One extra LLM step (~300–600 ms) on policy questions |
| Grounding guard on numbers | Most damaging hallucinations in lending are fees, dates, percentages; checking them is cheap and objective | Doesn't catch non-numeric fabrications (mitigated by tool-only facts + NOT_IN_KB) |
| Fixed, pre-approved lines for disclosure, fallback, escalation, closing | Compliance text must not drift; also guarantees localized fallbacks never switch to English | Less variety |
| Hybrid BM25 + embeddings with RRF + abstention | Lexical handles exact terms (EMI, UTR, BPKB), dense handles paraphrase/code-switching; abstention prevents near-miss answers | Thresholds need calibration per corpus |
| Authority-ranked conflict reconciliation | Real corpora disagree (playbook said 5-day grace, policy says 3); the approved policy wins, original kept for owners | Needs a maintained authority table |
| Q4 two-tier signals | Rules give sub-ms, high-precision compliance nudges; LLM adds recall on fuzzy signals and vetoes false rule hits | LLM path adds ~0.3–0.8 s |
| Nudge text from an approved playbook | Agents receive compliant wording; LLM only detects + quotes evidence | Less tailored phrasing |
