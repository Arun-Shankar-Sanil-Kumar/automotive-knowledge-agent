# PLAN.md — Phase 1: MCP-Based Web Ingestion

## Project

**Automotive Knowledge Ingestion & Intelligence Agent**

## Phase 1 Goal

Build the first working ingestion pipeline where a user provides a web URL and the system uses an **MCP Fetch Server** to retrieve the webpage content.

Phase 1 focuses **only on web acquisition through MCP**. No RAG, Qdrant, PostgreSQL, browser automation, memory, or multi-agent workflow will be implemented yet.

---

## 1. Objective

The system should:

1. Accept a webpage URL from the user.
2. Connect to an external Fetch MCP Server as an MCP client.
3. Discover the tools exposed by the MCP server.
4. Invoke the appropriate Fetch MCP tool.
5. Retrieve webpage content.
6. Return the extracted content to the application.
7. Display basic information about the retrieved source.

### Target Flow

```text
User
 │
 │ URL
 ▼
Python Application
 │
 │ MCP Client
 ▼
Fetch MCP Server
 │
 │ HTTP/Web
 ▼
Target Web Page
 │
 ▼
Extracted Content
 │
 ▼
Python Application
```

---

## 2. Scope

### In Scope

- Python MCP client
- Existing Fetch MCP server
- MCP initialization
- MCP tool discovery
- MCP tool invocation
- URL input
- Webpage retrieval
- Basic content extraction
- Basic error handling
- Display retrieved content
- Source URL tracking

### Out of Scope

The following will **not** be implemented in Phase 1:

- PostgreSQL
- Qdrant
- Embeddings
- RAG
- LLM-based question answering
- Browser automation
- Puppeteer/Playwright MCP
- Google Drive
- OneDrive
- Filesystem MCP
- Memory MCP
- Sequential Thinking MCP
- GitHub MCP
- Subagents
- Complex context engineering
- Production authentication
- Advanced document processing
- OCR
- PDF processing

These belong to later phases.

---

## 3. MCP Architecture

The application will act as the **MCP Client**.

The Fetch server will be an **external MCP Server**.

```text
┌─────────────────────────────┐
│       Our Application       │
│                             │
│       Python MCP Client     │
└──────────────┬──────────────┘
               │
               │ MCP Protocol
               │
┌──────────────▼──────────────┐
│       Fetch MCP Server      │
│                             │
│       Web Fetch Tool        │
└──────────────┬──────────────┘
               │
               │ HTTP
               ▼
        ┌─────────────┐
        │ Web Page    │
        └─────────────┘
```

The application will **not implement its own HTTP scraper** in Phase 1.

The purpose is specifically to demonstrate:

> **AI/application → MCP Client → MCP Server → External capability**

---

## 4. Project Structure

Phase 1 will contain both a **product runtime track** and a **development tracking track**.

```text
automotive-knowledge-agent/
│── DEVELOPMENT_LOG.md
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── backend/
│   └── app.py
│
├── mcp/
│   └── fetch_client.py
│
├── .env
├── .gitignore
└── requirements.txt
```

The structure is intentionally lightweight. We will not add ingestion, RAG, vector database, memory, or other components until later phases.

### Phase 1 Tracks

```text
                         PHASE 1
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
       PRODUCT RUNTIME             DEVELOPMENT TRACK
              │                           │
              ▼                           ▼
          Fetch MCP                  GitHub MCP
              │                           │
              ▼                           ├── Issues
          Web Page                      ├── Project tracking
              │                         ├── Repository
              ▼                         ├── Commits
       Content Preview                  └── Pull Requests
```

The two MCP servers have different responsibilities:

- **Fetch MCP** provides a runtime capability to retrieve web content.
- **GitHub MCP** supports the development workflow used to build and track this project.

GitHub MCP is **not part of the runtime web-ingestion pipeline** in Phase 1.

---

## 5. MCP Client Responsibilities

### 5.1 Start the MCP Server

The client launches the configured Fetch MCP server.

```text
Python
  │
  └── starts Fetch MCP Server
```

### 5.2 Initialize the MCP Session

The client establishes the MCP connection.

```text
Client
  │
  │ initialize
  ▼
Fetch MCP Server
```

### 5.3 Discover Available Tools

The client will call:

```text
tools/list
```

The application should **not hardcode the tool list**.

```text
MCP Client
    │
    │ tools/list
    ▼
Fetch MCP Server
    │
    ▼
Available capabilities
```

### 5.4 Call the Fetch Tool

After identifying the actual tool exposed by the server, the client will invoke it with the user-provided URL.

Conceptually:

```python
session.call_tool(
    "<actual_fetch_tool>",
    {
        "url": "<user URL>"
    }
)
```

The exact tool name and argument schema will be determined from the server's `tools/list` response.

---

## 5B. Development Tracking & Commit Workflow

Phase 1 uses two complementary development-management MCP servers: a local Git MCP server that provides programmatic access to the *local* repository, and a GitHub MCP server that provides programmatic access to the remote GitHub development services. These two MCPs are strictly part of the development tracking workflow and are not part of the product/runtime Fetch MCP capability.

The responsibilities are split as follows:

- Git MCP (local Git operations):
  - Inspect local repository status and uncommitted changes.
  - Show local diffs and file-level changes.
  - Stage/unstage files and create local commits.
  - Push and pull changes to/from remotes.
  - Branch operations (create, checkout, rename, delete, list).
  - Other local Git operations supported by the installed Git MCP server (reflog, stash, reset, etc.).

- GitHub MCP (remote GitHub operations):
  - Create, read and update Issues.
  - Project / task tracking and issue fields.
  - Read remote repository metadata and the remote commit history.
  - Create and manage Pull Requests.
  - Other GitHub development-management operations exposed by the installed GitHub MCP server (labels, releases, comments, reviews).

These MCPs complement each other: the Git MCP enables the assistant to perform precise, semantics-aware local repository operations, while GitHub MCP enables the assistant to manage the team-facing workflow on GitHub. Neither replaces the other.

### Revised Task Lifecycle

The development flow for a Phase 1 task is:

```text
GitHub MCP
    ↓
Read / manage development task
    ↓
AI Development Assistant
    ↓
Implement
    ↓
Test
    ↓
Update DEVELOPMENT_LOG.md
    ↓
Git MCP
    ↓
Commit
    ↓
Push
    ↓
GitHub MCP
    ↓
Update / close GitHub Issue
    ↓
Next task
```

Key rules:

- Do not claim that Git MCP replaces GitHub MCP, and do not claim that GitHub MCP replaces local Git.
- Keep the Fetch MCP as the only MCP server used by the Phase 1 product/runtime.
- Use Git MCP only for local repository operations and GitHub MCP for remote, GitHub-facing operations.
- Update `DEVELOPMENT_LOG.md` before committing so the local commit and remote issue reflect the recorded work.

### Commit Rule & Message Convention

By default each completed Phase 1 task should result in one coherent commit. Use conventional commit prefixes for clarity (example: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).

### Push Requirement

After acceptance criteria are satisfied and the `DEVELOPMENT_LOG.md` update is recorded locally:

1. Use Git MCP to stage the relevant files and create a local commit.
2. Use Git MCP to push the commit to the configured remote.
3. Use GitHub MCP to update or close the corresponding GitHub Issue.

### Safety Rule

Do not commit or push untested or incomplete work. Validate locally (run the runner or tests) before creating a commit. If validation cannot be completed, do not mark the task as done nor push changes.
---

## 5A. GitHub MCP — Development Tracking

GitHub MCP will be used as the team-facing development-management capability. It complements the Git MCP local operations by providing remote, GitHub-hosted services that support issue tracking, pull requests, and repository metadata.

### Purpose

Use GitHub MCP to:

- Create, read, update, and close Issues.
- Manage project/task fields and workflows on GitHub.
- Read remote repository metadata and the remote commit history.
- Create and manage Pull Requests and reviews.
- Manage labels, releases, comments, and other GitHub-hosted development-management features.

### Phase 1 Development Workflow (remote-facing)

```text
Developer
    │
    ▼
AI Development Assistant
    │
    │ GitHub MCP
    ▼
GitHub Repository
    │
    ├── Issues
    ├── Project / Task Tracking
    ├── Repository
    ├── Commits
    └── Pull Requests
```

### Initial Phase 1 Tasks

The project can be tracked through GitHub issues such as:

```text
Phase 1 — Web Ingestion

#1 Setup Python MCP client
#2 Connect Fetch MCP
#3 Discover Fetch tools
#4 Implement URL ingestion
#5 Add error handling
#6 Build frontend
#7 Connect frontend → backend
#8 Phase 1 testing
```

Each task follows the Phase 1 development lifecycle:

```text
Issue
 ↓
Implementation
 ↓
Testing
 ↓
Commit (via Git MCP)
 ↓
Push (via Git MCP)
 ↓
Issue update / closure (via GitHub MCP)
```

### Example Developer Interactions

The development assistant should eventually be able to handle requests such as:

- "What are the remaining Phase 1 tasks?" — (GitHub MCP: list/read issues)
- "Create an issue for adding Browser MCP fallback." — (GitHub MCP: create issue)
- "Mark the Fetch MCP integration task as complete." — (Git MCP: local commit/push + GitHub MCP: update/close issue)
- "What changed in the latest implementation?" — (Git MCP: show local diff / GitHub MCP: show recent commits)
- "Show me the open issues related to the frontend." — (GitHub MCP: search issues)
- "Summarize the latest pull request." — (GitHub MCP: read PR and comments)

### Important Boundary

GitHub MCP is strictly for remote development-management. It does not replace local Git workflows provided by Git MCP, nor does Git MCP replace the need for GitHub MCP. The Fetch MCP remains the only MCP used by the Phase 1 product/runtime.

---
```text
## 5C. Development Log

The project must maintain a `DEVELOPMENT_LOG.md` file that records the
actual development work completed during Phase 1.

The coding assistant must update this file whenever a Phase 1 task is
successfully completed.

### Development Log Requirements

For every completed task, add a dated entry containing:

- Date
- GitHub Issue / Task number
- Task title
- Work performed
- Files created or modified
- Tests/checks performed
- Commit message
- GitHub Issue status

### Example

```text
# Development Log

## 2026-08-12

### TASK-01 — Setup Python MCP Client

**Status:** Completed

**Work Performed:**
- Created Python project structure.
- Added MCP client dependencies.
- Created MCP client foundation.
- Added environment configuration.

**Files Changed:**
- `requirements.txt`
- `mcp/fetch_client.py`
- `.env.example`

**Validation:**
- Python environment verified.
- MCP client initialization tested successfully.

**Commit:**
`abc1234` — `feat: setup Python MCP client`

**GitHub Issue:**
#1 — Closed
```
---

## 6. User Workflow

The Phase 1 interface will initially be CLI-based.

Example:

```text
========================================
Automotive Knowledge Ingestion
========================================

Enter URL:
https://example.com/vehicle-specification
```

The application then performs:

```text
URL
 ↓
Fetch MCP
 ↓
Web Content
```

Output:

```text
Source:
https://example.com/vehicle-specification

Status:
SUCCESS

Content:
----------------------------------------
<retrieved webpage content>
----------------------------------------
```

---

## 7. Error Handling

Phase 1 should handle basic failures.

### Invalid URL

```text
Invalid URL.
```

### MCP Server Unavailable

```text
Unable to connect to Fetch MCP Server.
```

### Fetch Failure

```text
Unable to retrieve webpage.
```

### Empty Content

```text
Webpage retrieved, but no usable content was returned.
```

### Timeout / Network Failure

```text
Unable to retrieve source within the allowed time.
```

The application should fail gracefully instead of crashing.

---

## 8. Content Handling

Phase 1 does **not** attempt sophisticated document understanding.

The retrieved content will simply be captured and displayed.

```text
URL
 ↓
Fetch MCP
 ↓
Retrieved content
 ↓
Basic cleanup
 ↓
Display
```

We are intentionally postponing:

```text
HTML → semantic sections
HTML → metadata
HTML → chunks
HTML → embeddings
```

until later phases.

---

## 9. Phase 1 Success Criteria

Phase 1 is complete when all of the following work:

### Test 1 — MCP Connection

```text
Connected to Fetch MCP Server.
```

### Test 2 — Tool Discovery

The application successfully displays the tools returned by:

```text
tools/list
```

### Test 3 — Basic Webpage

Given:

```text
https://example.com
```

the application retrieves the page successfully.

### Test 4 — Real Automotive Webpage

Given a suitable automotive webpage, the application retrieves usable content.

### Test 5 — Error Handling

Invalid or unreachable URLs do not crash the application.

### Test 6 — GitHub Development Tracking

The development workflow can use GitHub MCP to:

1. Discover relevant repository/project information.
2. Read Phase 1 issues.
3. Create or update development issues.
4. Inspect relevant commits or pull requests.

The exact operations depend on the GitHub MCP tools enabled for the project.

### Test 7 — Frontend

The user can:

1. Open the web application.
2. Enter a URL.
3. Start ingestion.
4. See the ingestion status.
5. See the retrieved content or a clear error.

### Test 8 — No Direct Scraper

The application retrieves the webpage **through the MCP server**, rather than using:

```python
requests.get(...)
```

or another direct HTTP implementation.

This is important because Phase 1 is specifically intended to demonstrate MCP.

---

## 10. Phase 1 User Experience

The intended Phase 1 experience is:

```text
┌─────────────────────────────────────────────┐
│ Automotive Knowledge Ingestion              │
├─────────────────────────────────────────────┤
│                                             │
│ Web Source URL                              │
│ ┌─────────────────────────────────────────┐ │
│ │ https://example.com/...                 │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│              [ Start Ingestion ]            │
│                                             │
│ Status: Fetching source...                  │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Retrieved Content                       │ │
│ │                                         │ │
│ │ <webpage content preview>               │ │
│ └─────────────────────────────────────────┘ │
│                                             │
└─────────────────────────────────────────────┘
```

The UI should make the MCP workflow visible enough for demonstration:

```text
URL submitted
     ↓
Connecting to Fetch MCP
     ↓
Fetching webpage
     ↓
Content retrieved
     ↓
Preview displayed
```

This is a demonstration interface, not a production dashboard.

---

## 11. What Phase 1 Demonstrates

The key learning outcomes are:

> **An application can consume an external capability through MCP without implementing that capability itself.**

and:

> **MCP can also expose development capabilities that an AI assistant can use to work with the project's software-development workflow.**

This gives Phase 1 three distinct MCP demonstrations:

```text
Fetch MCP  → Product/runtime capability
Git MCP    → Local source-control capability
GitHub MCP → Remote development-management capability
```

Instead of:

```text
Our Python application
       │
       └── requests / BeautifulSoup
```

we demonstrate:

```text
Our Python application
       │
       │ MCP
       ▼
Fetch MCP Server
       │
       ▼
Web
```

This becomes the foundation for the larger system.

---

## 12. Future Architecture

### Phase 1

Product runtime:

```text
URL
 ↓
Fetch MCP
 ↓
Content
```

Development workflow:

```text
Developer
 ↓
AI Development Assistant
 ↓
Git MCP (local commits, branches, staging)
 ↓
GitHub MCP (issues, PRs, remote repository)
```

### Phase 2

```text
URL
 ↓
Fetch MCP
 ↓
Content
 ↓
Normalize
 ↓
Chunk
```

### Phase 3

```text
Content
 ↓
PostgreSQL
 +
Qdrant
```

### Phase 4

```text
Question
 ↓
Qdrant
 ↓
Relevant knowledge
 ↓
LLM
 ↓
Answer + sources
```

### Phase 5

```text
Source
 ↓
Agent
 ↓
Should I use Fetch?
       │
       ├── Yes → Fetch MCP
       │
       └── No → Browser MCP
```

This eventually becomes the **adaptive automotive knowledge ingestion agent**.

---

## 13. Phase 1 Principle

**Keep Phase 1 intentionally simple.**

The objective is not to build a scraper.

The objective is to prove the first MCP capability:

```text
APPLICATION
     │
     │ MCP
     ▼
EXTERNAL CAPABILITY
     │
     ▼
WEB
```

Once this works reliably, we build the ingestion intelligence on top of it.
