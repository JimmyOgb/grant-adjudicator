# ⚖️ Grant Adjudicator

> A GenLayer Intelligent Contract that automates DAO milestone-based grant approval — five independent AI validators inspect submitted GitHub repos and live deployments, reaching consensus on approval without human bias or bottlenecks.

[![GenLayer Studio](https://img.shields.io/badge/GenLayer_Studio-Open_Contract-2563eb?style=for-the-badge&logoColor=white)](https://studio.genlayer.com/?import-contract=0x7e018D4b72D22E0De1F9f5C7A5f58661951DD0EB)
[![Network](https://img.shields.io/badge/Network-GenLayer_Studionet-16a34a?style=for-the-badge)](https://studio.genlayer.com)
[![License](https://img.shields.io/badge/License-MIT-7c3aed?style=for-the-badge)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Live Deployment](#-live-deployment)
- [How It Works](#-how-it-works)
- [Contract Architecture](#-contract-architecture)
- [Methods](#-methods)
- [Frontend](#-frontend)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)

---

## 🌐 Overview

**Grant Adjudicator** solves the DAO scaling problem: human grant committees cannot review hundreds of milestone submissions per week without becoming a bottleneck, and are vulnerable to bias, fatigue, or collusion.

This contract replaces manual review with decentralized AI consensus. A funding organization defines a milestone's requirements and payout. A grantee submits their GitHub repository and live deployment URL. Five independent validator nodes each fetch both URLs live, evaluate the evidence against the stated requirements, and must reach identical agreement before the milestone is approved or rejected — fully on-chain, fully auditable.

**Why this matters:**
- **Uncapped scale** — review thousands of submissions without adding reviewers
- **Sybil and collusion resistant** — no committee to bribe, no politics to navigate
- **Fully auditable** — every approval/rejection includes the AI's full reasoning, permanently on-chain

---

## 🚀 Live Deployment

| Resource | Link |
|---|---|
| **Contract on GenLayer Studio** | [0x7e018D4b72D22E0De1F9f5C7A5f58661951DD0EB](https://studio.genlayer.com/?import-contract=0x7e018D4b72D22E0De1F9f5C7A5f58661951DD0EB) |
| **Network** | GenLayer Studionet |
| **Contract Address** | `0x7e018D4b72D22E0De1F9f5C7A5f58661951DD0EB` |

---

## ⚙️ How It Works

```
create_grant(title, milestone_description, payout_amount, consensus_threshold)
        │
        └── grant stored with status = "Active"

submit_milestone(grant_id, github_url, deployment_url)
        │
        ├── status → "Under Review"
        │
        └── run_evaluation() inner function
                │
                ├── gl.nondet.web.render(github_url, mode="text")[:2000]
                ├── gl.nondet.web.render(deployment_url, mode="text")[:2000]
                │
                ├── gl.nondet.exec_prompt(prompt)
                │   5 validator nodes independently evaluate:
                │   · Does the repo implement the required features?
                │   · Is the live deployment functional and accessible?
                │   · Do both sources corroborate milestone completion?
                │
                └── gl.eq_principle.strict_eq()
                    All 5 nodes must return identical JSON
                    {vote, confidence, reasoning}
                            │
                confidence >= consensus_threshold?
                    │                       │
                  YES                      NO
                    │                       │
              status="Approved"      status="Rejected"
              payout authorized      resubmit or reset_grant()
```

### Consensus Model

`gl.eq_principle.strict_eq()` requires all 5 nodes to independently fetch both URLs and run identical LLM analysis, returning the same vote, confidence score, and reasoning. This is fundamentally different from a traditional multi-sig vote — there is no "3 of 5 pass" tally; either all validators agree on one verdict, or the transaction fails and must be resubmitted.

---

## 🏗️ Contract Architecture

```python
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

class GrantAdjudicator(gl.Contract):
    state: TreeMap[str, str]
```

### Storage Design

Single `TreeMap[str, str]` — required because GenLayer only supports one `TreeMap` per contract:

| Key | Value | Description |
|---|---|---|
| `"owner"` | `"0xOwner…"` | Contract deployer — can call `reset_grant()` |
| `"count"` | `"3"` | Total grants created |
| `"grant:{id}"` | JSON string | Full grant record + evaluation report |

### Grant Record Schema

```json
{
  "id": 1,
  "title": "DeFi Frontend Integration",
  "milestone_description": "Build a functional web app...",
  "payout_amount": "5000",
  "consensus_threshold": "0.70",
  "creator": "0xFunder...",
  "status": "Approved",
  "github_url": "https://github.com/example/repo",
  "deployment_url": "https://example.vercel.app",
  "vote": "PASS",
  "confidence": "0.85",
  "reasoning": "Repository structure verified...",
  "evaluation_summary": "APPROVED — confidence 85%. Payout of 5000 authorized."
}
```

---

## 📌 Methods

### Write Methods

#### `create_grant(title, milestone_description, payout_amount, consensus_threshold) → int`
Funder initializes a grant. Returns the new grant ID.

```python
title:                 str   # Short grant title
milestone_description: str   # Detailed requirements
payout_amount:         str   # e.g. "5000"
consensus_threshold:   str   # 0.0-1.0, e.g. "0.70" for 70%
```

#### `submit_milestone(grant_id, github_url, deployment_url) → str`
Grantee submits proof. Triggers immediate 5-node AI evaluation.

```python
grant_id:        u256
github_url:       str
deployment_url:   str
```

Returns an approval or rejection message with confidence score and reasoning.

#### `reset_grant(grant_id) → str`
Owner-only. Resets a rejected grant back to `Active` so the grantee can resubmit after improvements.

### View Methods

#### `get_grant_status(grant_id) → str`
Full JSON grant record.

#### `get_grant_summary(grant_id) → str`
Human-readable summary: `"Grant #1 — DeFi Frontend Integration | Status: Approved | Payout: 5000 | …"`

#### `get_total_grants() → str`
Total grant count.

#### `get_owner() → str`
Contract owner address.

---

## 🖥️ Frontend

Clean SaaS dashboard aesthetic — light theme, sidebar + main layout:

- **Sidebar** — Create Grant, Submit Milestone, Query Grant, Reset Grant panels, each wired to the matching contract method
- **5-node consensus animation** — terminal-style output showing each validator fetching URLs and submitting verdicts
- **Verdict cards** — green/red banners with confidence percentage and full AI reasoning
- **Stats row** — total, active, approved, rejected counts
- **Grant Registry table** — all grants with status pills, confidence bars, and quick action buttons
- **Transaction log** — every call with status and timestamp

### Running locally

```bash
open frontend/index.html
npx serve frontend/
python3 -m http.server 8080 --directory frontend/
```

### Deploying

```bash
netlify deploy --prod --dir frontend/
vercel --prod
```

---

## 🏁 Getting Started

### 1. Open in GenLayer Studio
```
https://studio.genlayer.com/?import-contract=0x7e018D4b72D22E0De1F9f5C7A5f58661951DD0EB
```

### 2. Create a Grant
```
title:                 DeFi Frontend Integration
milestone_description: Build a functional web app frontend with wallet
                       connection support, responsive design, and
                       deployment on a public URL.
payout_amount:          5000
consensus_threshold:    0.70
```

### 3. Submit a Milestone
```
grant_id:        1
github_url:      https://github.com/example/defi-wallet-frontend
deployment_url:  https://defi-wallet-frontend.vercel.app
```

### 4. Query the Result
```
get_grant_summary(1)
→ "Grant #1 — DeFi Frontend Integration | Status: Approved | Payout: 5000 | …"
```

### 5. Reset if Rejected
```
reset_grant(1)
```
Only the owner can call this, and only on grants with `Rejected` status.

---

## 📁 Project Structure

```
grant-adjudicator/
├── contract/
│   └── grant_adjudicator.py   # GenLayer Intelligent Contract
├── frontend/
│   └── index.html             # SaaS dashboard
├── docs/
│   └── architecture.md        # Storage design, consensus notes
├── .gitignore
├── LICENSE
├── package.json
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Blockchain** | GenLayer (L2, Studionet) |
| **Contract Language** | Python (GenLayer Intelligent Contract) |
| **AI Consensus** | `gl.eq_principle.strict_eq` — 5 validator nodes |
| **Web Data** | `gl.nondet.web.render` → GitHub + deployment URLs |
| **LLM Execution** | `gl.nondet.exec_prompt` (multi-model via OpenRouter) |
| **Storage** | `TreeMap[str, str]` with prefixed key namespacing |
| **Frontend** | Vanilla HTML / CSS / JS — zero dependencies |
| **Fonts** | Inter · JetBrains Mono |

---

## 📜 License

MIT — see [LICENSE](LICENSE) for details.
