# Design Doc: AI-Chat Safety Monitoring Tool

**Status:** Draft for review
**Audience:** Sponsoring non-profit, engineering contributors, reviewing counsel
**Scope of this doc:** Architecture and the shared verdict contract. Implementation happens in a separate repo/pass.

---

## 1. Problem & framing

Kids and students increasingly use general-purpose AI chatbots (ChatGPT, Gemini, Grok, Claude, and third-party clients). Model builders' safety training tends toward *refusal or redirection* — tuned for a good product experience, not maximum sensitivity. This tool adds an **opt-in, disclosed guard in front of any chatbot** that flags conversations plausibly indicating intent to harm others, and puts a **responsible adult** (parent or school staff) in the moderator role rather than relying on the model provider to police it.

We are starting **narrow**: a single well-validated category (planning/threat of violence toward others). The system is designed so additional categories can be added later — each one built to the same bar (high accuracy, adult-selectable, transparent) — **not** as a blanket "unsafe content" dragnet.

### Goals

- Flag conversations plausibly indicating intent to harm others, with a **low enough false-positive rate to stay trusted**.
- Put a disclosed human adult in the loop as moderator; notify them when a conversation is verified as concerning.
- Work as a guard in front of **any** chatbot, not a single walled-garden bot.
- Be **open source** and priced **at cost** (backend/LLM/notification costs are real and acknowledged).
- Build a feedback loop where **experts review anonymized flagged traces** to continuously improve detection.

### Non-goals (explicit)

- **Not an emergency-response system.** Notifications are best-effort (email/SMS can be delayed or missed). The tool must never position itself as the thing standing between a child and an imminent act. High-confidence imminent flags surface crisis/authority guidance to the adult rather than implying we've handled it.
- **Not a blanket surveillance dragnet.** Scope grows one validated category at a time. Category is adult-selected, not on by default.
- **Not adversarially robust.** Open-source detection logic is inspectable by a motivated evader. We catch the un-careful majority and act as a disclosed deterrent; we say so plainly rather than overselling.
- **Not covert.** The monitored child knows what is monitored. Disclosed monitoring is both more lawful and more effective.
- **Not a diagnosis or a verdict of guilt.** Output describes an *observation for review*, never a conclusion about a person.

---

## 2. Core principles

These are load-bearing and should survive contact with feature requests and funding incentives.

1. **Verified before alert.** No alert fires to any recipient on the cheap recall stage alone. Both the family tier and the school tier get the same two-stage classification. We tier the *product* (workflow, routing, dashboard, audit), never the *accuracy of the judgment*. A false accusation of planning violence is a uniquely costly error; nobody receives the unverified version of it.
2. **Narrow, then deliberate.** Each category is a separately built, separately validated detector with its own thresholds, routing, and response guidance — not a checkbox on one generic model.
3. **Transparency over stealth.** The child knows. The detection logic is open. Limits are stated, not hidden.
4. **Proportionate capture.** Escalate flagged content; do not warehouse everything a child types. Minimize sensitive data at rest.
5. **Latency is loose, accuracy is tight.** We cannot block the first response (see §4), so the classifier is off the critical path. Optimize for correctness and cost, not milliseconds.
6. **The verdict is the contract.** One structured object is the single source of truth that every surface (lock logic, notifications, dashboard, feedback store, human review) renders from.

---

## 3. Architecture overview

Two clean halves connected by a stable contract:

```
┌────────────────────────┐        ┌──────────────────────────────────────┐
│   CAPTURE FRONT-ENDS    │        │           DETECTION CORE             │
│  (thin, swappable)      │        │                                      │
│                         │  text  │  ┌────────────┐   ┌───────────────┐  │
│  • Chromium extension   │ +ctx   │  │ recall gate│──▶│ tiered LLM    │  │
│  • Firefox extension    ├───────▶│  │ (wordlist, │   │ classifier    │  │
│  • Managed ChromeOS     │        │  │  local)    │   │ (tier-1→tier-2│  │
│  • [future] native agent│        │  └────────────┘   └───────┬───────┘  │
│  • [future] net proxy   │◀───────┤                           │          │
│                         │ verdict│                      VERDICT OBJECT   │
│  (renders lock overlay) │        │                           │          │
└────────────────────────┘        └───────────────────────────┼──────────┘
                                                               │
                        ┌──────────────────────────────────────┼─────────────┐
                        │        ASYNC PIPELINE (off hot path)  ▼             │
                        │  escalation → human review → de-id → feedback store │
                        │  → wordlist maintenance → calibration/eval          │
                        │  (LangGraph orchestration, LangSmith datasets)      │
                        └────────────────────────────────────────────────────┘
```

**The capture ↔ core boundary is the most important design decision.** The core does not know or care where text came from. That is what lets one detection core serve a Chromium extension today and a native agent or proxy later, so we maintain **one product, not four**.

### Capture front-ends (what they do)

- Observe the chatbot input and the rendered turns via the page DOM (SPA-aware: contenteditable/textarea + send events).
- Maintain a small **client-side rolling window** of recent turns (stateless per request — less sensitive data server-side, fewer retention questions).
- Run the local recall gate; on a hit, POST `{ windowed text, category set, client metadata }` to the core.
- Receive a verdict; render the **lock overlay** and block further navigation to the chatbot domain when the verdict crosses the lock threshold.
- Scoped to the specific chatbot domains only (not `<all_urls>`) to keep the permission footprint and install prompt minimal.

### Deployment surfaces (coverage vs. cost)

| Surface | Coverage | Bypass resistance | Build cost | When |
|---|---|---|---|---|
| Chromium extension | Chrome/Edge/Brave/Opera | Low (switch browser/device) | Low | **v1** |
| Firefox extension | Firefox | Low | Low–med | v1/v2 |
| Managed ChromeOS (force-install) | School Chromebooks | **High** (admin controls installable set; domain blocking at policy level) | Low (same ext + deploy profile) | **v1 school** |
| Native endpoint agent | Whole device, any browser/app | High (admin to uninstall) | High (per-OS, signed, privileged, real trust/security burden) | Later, only if a deployment needs it |
| Network/TLS proxy | Device/network, can block first response | High | High (TLS interception, cert pinning, consent burden) | Later, schools only, likely not open-distributed to families |

**Recommendation:** ship the Chromium extension first; use **managed-ChromeOS force-install** as the school story (gets endpoint-level non-bypassability for free via device management); treat native agent and proxy as later heavier front-ends against the same core.

### Third-party chatbot detection

From an extension we can read **which domains** the browser contacts (`webRequest`), so we can **detect and block known third-party LLM endpoints** (e.g. a client calling a provider API host) as deterrence and coverage-widening. We **cannot** read their content — it's TLS-encrypted, and content inspection would require the invasive proxy path. Native-app usage is invisible to the extension entirely; only a device/network agent catches that. On managed Chromebooks, domain blocking via **admin policy** is cleaner than doing it in the extension. Net: **domain-level detection/blocking, not content inspection** of third-party clients.

---

## 4. Detection pipeline

### 4.1 Why the first response can't be blocked

The child's browser talks **directly** to the provider; we observe the DOM, we are not in the request path. Therefore the classifier's output drives actions that happen **after** a response renders (lock the tab, notify the adult). The guarantee we make is **"we catch the conversation, not necessarily the first token."** This is acceptable because the threat model is a *pattern across a session*, not a single one-shot question. Lock-after-first-flag still stops continuation and notifies the adult.

Consequence: **do not attempt a synchronous inline LLM guard.** It would add a round-trip to every innocent message, degrade every conversation to catch the rare bad one (the exact sensitivity trade the model builders declined), and *still* can't hold the first request. Keep the cheap local gate; accept the first-message gap.

### 4.2 Stage 1 — recall gate (local, instant, free)

- A deliberately **over-inclusive wordlist** maintained from the sponsoring non-profit's research + the feedback loop.
- Runs **client-side** on every send with **zero latency and zero cost**. Its only job is **recall** — "is this plausibly worth a classifier call?" Precision is the classifier's job.
- It is tuned **against the classifier bill and latency**, not against final precision. A term earns its place if its flagged-and-later-confirmed rate justifies the classifier calls it triggers. Terms that fire constantly and never confirm are cost with no signal — the feedback loop surfaces them for removal.
- **The wordlist and the feedback pipeline are one loop, not two features.** The pipeline is *how the wordlist is maintained.*

### 4.3 Stage 2 — tiered LLM classifier (backend, off hot path)

- **Tier-1 (fast, cheap, recall-biased):** "is this plausibly concerning?" A tier-1 flag triggers the **lock immediately** (a false lock is recoverable; a missed threat is not) and emits a *pending* verdict. This is the user-visible responsiveness path — one cheap call.
- **Tier-2 (larger, precise, verifying):** produces the **confirmed** verdict that gates any notification. Runs a beat later, behind the lock.
- **Both tiers receive session context** (the rolling window), not just the triggering message — this is what separates the WWII-essay kid from a real threat, and latency budget is loose enough to afford it.
- Implemented as a **thin, stateless structured LLM call** using the provider SDK with structured outputs — **not** a graph. For an open-source safety tool, a minimal, legible critical path (text in → verdict out) is a feature: fewer layers between input and "lock a kid out" for the non-profit, auditors, and contributors to reason about.

### 4.4 Confidence-based suppression (future cost optimization) — with a mandatory guard

Later, a calibrated confidence score may let us **skip tier-2 for some matches** to cut cost. This has a blind spot: **you lose ground truth on exactly the cases you stop checking**, so you can't measure the false-negative rate of a suppressed decision.

**Mandatory mitigation, built before suppression is ever enabled:** always send a **holdout sample** (e.g. 5–10%) through full classification even when confidence says "skip," purely to keep measuring calibration. **Build the sampling before the suppression**, or we fly blind the moment suppression turns on.

---

## 5. The verdict object (the contract)

This is the single source of truth. The lock decision is a threshold on it; the notification is a render of it; the dashboard card is a render of it; the "show raw text or not" choice keys off its imminence; the feedback store logs it; the reviewer confirms or overturns it. **Get this right in one pass** or four inconsistent notions of "how bad is this" leak across the codebase.

### 5.1 Design decisions baked into the shape

- **Category is a first-class dimension**, not a flat "unsafe score." Each category carries its own thresholds, routing, and response guidance. Adding a category does not require schema surgery.
- **Severity, confidence, and imminence are separate axes.** "How bad if true," "how sure are we," and "how soon" are different questions with different consequences. Collapsing them loses the signal that drives correct handling.
- **`directed_at` is explicit** (others / self / fictional-or-academic / ambiguous). This is the field that separates a threat from a book report — and it's the seed of per-category response divergence (violence-toward-others vs. self-harm route completely differently).
- **`recommended_action` is derived but explicit**, so every surface acts on one computed decision rather than re-deriving thresholds independently.
- **Stage and status are represented** so a *pending* (tier-1) verdict and a *confirmed* (tier-2/human) verdict are the same object at different lifecycle points — enabling the honest "locked pending review" vs. "confirmed, adult notified" UX.

### 5.2 Fields

```
Verdict
├── schema_version        str            # contract versioning; every consumer checks this
├── verdict_id            uuid           # stable id across pending→confirmed lifecycle
├── created_at            iso8601
│
├── stage                 enum           # RECALL_GATE | TIER1 | TIER2 | HUMAN
├── status                enum           # PENDING | CONFIRMED | CLEARED | OVERTURNED
│
├── category              enum           # VIOLENCE_TO_OTHERS  (only live category in v1)
│                                        # extensible: SELF_HARM, ... added as validated
├── directed_at           enum           # OTHERS | SELF | FICTIONAL_OR_ACADEMIC | AMBIGUOUS
│
├── severity              enum           # LOW | MODERATE | HIGH | CRITICAL  (how bad if true)
├── confidence            float 0–1      # calibrated; how sure the classifier is
├── imminence             enum           # NONE | SPECULATIVE | DEVELOPING | IMMINENT (how soon)
│
├── recommended_action    enum           # NO_ACTION | LOG_ONLY | LOCK | LOCK_AND_NOTIFY
│                                        #            | LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES
│
├── rationale             str            # short model explanation, for the human reviewer
├── evidence_spans        [span]         # pointers into the windowed text (offsets), not copies
│
├── context
│   ├── window_turn_count int
│   ├── chatbot_host      str            # e.g. "chatgpt.com" (host only, not full URL)
│   ├── capture_surface   enum           # CHROMIUM_EXT | FIREFOX_EXT | MANAGED_CHROMEOS | ...
│   └── monitored_categories [enum]      # which categories this install opted into
│
├── review                              # populated on the async/human path only
│   ├── reviewed_by       str|null       # role/id of expert reviewer (anonymized in store)
│   ├── reviewed_at       iso8601|null
│   ├── reviewer_outcome  enum|null      # CONFIRM | OVERTURN | NEEDS_MORE
│   └── notes             str|null
│
├── sampling
│   ├── is_holdout        bool           # true if force-classified for calibration measurement
│   └── suppression_eligible bool        # would confidence have skipped tier-2?
│
└── privacy
    ├── deidentified      bool           # true once the de-id rewrite has replaced raw text
    ├── retain_as_training bool          # policy decision; imminent real-threat cases may be false
    └── raw_text_ref      str|null       # handle to raw text IF retained; null once de-id'd/purged
```

### 5.3 Per-category response guidance (encoded, not bolted on)

The mapping from verdict → `recommended_action` is **per category**, so divergent handling lives in the contract rather than in scattered conditionals.

**`VIOLENCE_TO_OTHERS` (v1):**

| directed_at | imminence | confidence | → recommended_action |
|---|---|---|---|
| FICTIONAL_OR_ACADEMIC | any | any | `NO_ACTION` / `LOG_ONLY` |
| AMBIGUOUS | ≤ DEVELOPING | any | `LOCK` (pending review; no notify yet) |
| OTHERS | ≤ DEVELOPING | high | `LOCK_AND_NOTIFY` (after tier-2) |
| OTHERS | IMMINENT | high | `LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES` |

**`SELF_HARM` (future — illustrative, do NOT ship without dedicated validation + clinical input):**
Routes *differently by design.* An auto-text to a parent about a child's suicidal ideation can out a vulnerable kid or escalate danger at home. Likely handling: surface crisis resources to the child, gentler human-in-the-loop path, and in schools route to a **counselor**, not an auto-alert. This row exists to prove the schema carries the divergence; the category is **not** in v1.

---

## 6. Product tiers

Same detection brain; different nervous system. We tier on workflow and accountability, **never** on judgment accuracy.

### Family tier

- Verified flag → **SMS** (faster/less spam-filed than email; email as fallback). Best-effort, framed as awareness.
- **Adult-selected categories** (v1: the one category). Consent + proportionality feature, not just UX.
- Notification content: describes an **observation**, not a conclusion ("flagged for review because it may involve X" — never "your child is planning X"); gives enough context to judge **without necessarily dumping raw private text** (resolve the child-privacy vs. parent-need tension by imminence — a *maybe* shows less; a high-confidence imminent flag shows more); tells the adult what to do next; for imminent/high-confidence, surfaces crisis-line + contact-authorities guidance rather than implying we handled it.
- Low fixed price (SMS provider cost is real).

### School tier

- Verified flag → **case in a triage queue** → reviewer confirms → routed notification → **audit trail**.
- **Dashboard** = lightweight case-management: flags with status (pending/cleared/confirmed/escalated), conversation context, who reviewed & when, action taken, immutable audit log.
- Roles/SSO, multi-recipient escalation, retention & access controls shaped by FERPA/COPPA/CIPA.
- Deployed via managed-ChromeOS force-install; domain blocking at admin-policy level.
- Fixed pricing.

---

## 7. Feedback & learning loop (async, off hot path)

This is where LangGraph and LangSmith earn their place — latency is irrelevant here, state and durability matter.

- **LangGraph** orchestrates the stateful, branching workflow: flag → fast classify → (if ambiguous) escalate to larger model → route to human reviewer → write **de-identified, holdout-tagged** result to the feedback store → feed wordlist maintenance.
- **LangSmith** across both hot and async paths (it traces raw-SDK calls too, so we keep it even with a non-LangChain hot path). Its real value is **datasets + eval**, which map onto our two hardest measurement problems:
  - **Calibration** of the confidence score before it's ever allowed to suppress tier-2.
  - **Standing red-team recall test:** the non-profit's researchers phrase oblique intent; measured as a growing dataset over time. This is our **honest false-negative estimate** — false negatives are invisible by construction (we only see flagged-confirmed and flagged-cleared; *missed entirely* never enters the funnel), so we must generate them deliberately.
- **Expert review of anonymized traces is the core engine of improving detection.** Confirmed/overturned reviewer outcomes are the ground-truth labels that (a) retrain the wordlist toward terms that actually confirm and (b) build the calibration set.

---

## 8. Data, privacy, retention, legal

The flagged-content store is the highest-stakes artifact: *text from minors flagged as possible planning of violence.* It is both a privacy liability and a target.

- **Real de-identification, not field-stripping.** Free-form text contains names, friends, school, teacher, classroom. Reliable scrubbing from natural language is its own NLP problem — prior art in clinical NLP (HIPAA-driven de-id, e.g. Philter, i2b2 de-id research). Approach: have the classifier stage also emit a **de-identified rewrite** that preserves linguistic signal while dropping specifics, and store **that**, not raw text.
- **Retention policy is a governance decision, not a code decision** (and this is open source — governance can't live in the code; it lives in the deployment policy the non-profit publishes with counsel). Key question: what happens to a genuine **imminent-threat** case — it likely should route to the adult and **not** sit in a training corpus (`retain_as_training = false`). There's a real difference between "kid workshopping a threat" as training data and text that could become part of an investigation.
- **Minimize at rest:** proportionate capture (only escalate flagged content, don't warehouse everything); client-side stateless windows; purge raw text once de-identified.
- **Consent & disclosure** carry legal weight: FERPA, COPPA, CIPA, state wiretapping/two-party-consent statutes all touch this. Disclosed monitoring on managed devices (schools) and a parent monitoring their own minor (families) are the two lawful footings we build for. **Counsel reviews the policy layer**; engineering builds the toggles and the audit trail that make the policy enforceable.

---

## 9. Measurement

- **Flagged-confirmed** and **flagged-cleared**: available from the pipeline.
- **Missed-entirely (false negatives):** invisible by construction → estimated via the **standing red-team dataset** (§7). This is the number that matters most for a safety tool and the hardest to see; report it honestly rather than a survivorship-biased "accuracy."
- **Calibration holdout** (§4.4): keeps the confidence score honest before/while suppression is enabled.
- **Wordlist health:** per-term fire rate vs. confirm rate; prune terms that fire and never confirm.

---

## 10. Phasing

- **v1 (narrow, families):** Chromium extension + local recall gate + two-stage classifier (SDK hot path) + verdict contract + SMS/email notify + de-id + feedback store + LangSmith eval scaffolding. Single category: `VIOLENCE_TO_OTHERS`.
- **v1 (schools):** same core + managed-ChromeOS deploy profile + triage dashboard + audit + roles.
- **v2:** Firefox front-end; domain-level third-party detection/blocking; confidence calibration + holdout sampling (before any suppression).
- **Later, deliberately:** additional categories (each separately validated, adult-selectable), native endpoint agent, network proxy — each only when it clears the accuracy/consent bar.

---

## 11. Open decisions for the non-profit + counsel

1. Retention policy for confirmed vs. imminent-threat cases (what's `retain_as_training` by default, and the purge SLA).
2. What raw context, if any, a family notification may include — resolved by imminence, but the exact thresholds need sign-off.
3. Whether the family tier surfaces "contact authorities" guidance directly, and the liability framing around it.
4. De-id approach acceptance (LLM rewrite vs. dedicated de-id tooling vs. both) and its validated scrub rate.
5. The disclosure/consent artifacts (acceptable-use language for schools; parent-and-child disclosure for families).
6. Governance for the open-source release: what ships in the repo vs. what's deployment policy the non-profit publishes.
