# SCARAG Reference Frontend State Model

This document describes the state that powers the React reference frontend in `frontend/src/App.jsx`.

It is a reference model, not a prescribed production architecture.

## 1. State Atoms

The current reference UI maintains these local state atoms:

- `query`: the current prompt text in the input box
- `messages`: ordered chat history with user and assistant messages
- `loading`: whether a request is in flight
- `drawerOpen`: whether the evidence drawer is visible
- `sidebarCollapsed`: whether the left navigation rail is collapsed
- `theme`: the current visual theme selection
- `feedbackDrafts`: draft free-text feedback keyed by assistant message id
- `activeView`: the main workspace mode, currently `chat` or `faq`
- `selectedEvalSignal`: currently selected evaluation chip key for optional advanced diagnostics

## 2. Message Model

The reference UI renders a single message list where each entry has a role.

### Assistant message shape

Assistant messages currently support these fields:

- `id`
- `role`
- `content`
- `citations`
- `confidence`
- `score`
- `evaluation` (optional per-response diagnostics with compact signals + detailed payload)
- `feedback`

The initial assistant message is a ready-state placeholder with empty citations, a `Ready` confidence label, and no score or feedback.

The in-flight assistant placeholder uses the same shape and is replaced once the API response returns.

### User message shape

User messages currently use:

- `id`
- `role`
- `content`

User messages do not carry evidence, confidence, score, or feedback state.

## 3. Derived State

The main derived value is `activeMessage`, which is selected as the most recent assistant message.

If no assistant message exists, the UI falls back to the last message in the array.

This derived state drives the evidence drawer, confidence badge, score badge, and evaluation strip so the drawer always reflects the currently active assistant response.

## 4. State Transitions

### Query submission

When the user submits a non-empty prompt:

1. a user message is appended to `messages`
2. an assistant placeholder is appended immediately after it
3. `query` is cleared
4. `loading` is set to `true`
5. `drawerOpen` is set to `true`
6. the `/api/chat` request is issued

When the response arrives:

1. the assistant placeholder is replaced with the answer payload
2. citations are normalized to a small reference-card structure, preferring `citations` and falling back to legacy `sources` when present
3. confidence and score are copied into the assistant message
4. optional evaluation diagnostics are normalized into compact chips and hidden advanced details

If the request fails, the assistant placeholder is replaced with an offline state and a connection-failure citation stub.
An informational fallback evaluation chip is shown to indicate diagnostics are unavailable.

### Feedback handling

Thumbs up/down feedback updates the selected assistant message in-place.

- thumbs up stores `feedback: 'up'`
- thumbs down stores `feedback: 'down'` and opens a draft feedback field

Draft text is held in `feedbackDrafts` until a future persistence layer is added.

### View and shell state

- `activeView` switches between the chat workspace and the FAQ view
- `drawerOpen` toggles the evidence drawer
- `sidebarCollapsed` toggles the left rail
- `theme` cycles through `default`, `light`, and `dark`

## 5. UI Mapping

The state atoms map to the visible interface as follows:

- `messages` renders the conversation stack
- `activeView` controls whether the chat or FAQ surface is visible
- `drawerOpen` controls the evidence drawer width/state
- `sidebarCollapsed` controls left-rail density
- `theme` controls the CSS theme variant
- `loading` disables the submit button and changes the button label
- assistant `confidence` renders as a badge in the answer chrome and a value in the drawer
- assistant `score` renders as an optional badge and a drawer metric
- assistant `citations` render as the visible citation cards in the drawer
- assistant `evaluation.signals` render as compact clickable chips in the drawer's evaluation strip
- assistant `evaluation.details` render only inside the collapsed advanced diagnostics section beneath citations
- `feedback` renders the thumbs state and feedback text area

## 6. Persistence Boundaries

The current reference frontend keeps all of this state in component-local React state.

No persistence exists yet for:

- chat history across reloads
- feedback capture
- FAQ customization
- theme preference storage

Those behaviors are intentionally left to implementation-specific layers.

## 7. Contract Coupling

This state model is coupled to the backend response shape documented in [reference-ui-contract.md](reference-ui-contract.md).

The reference frontend also preserves a narrow legacy-compatibility path for older payloads that provide `sources` instead of `citations`.

If either the frontend state shape or the backend response envelope changes, update both documents in the same change set.