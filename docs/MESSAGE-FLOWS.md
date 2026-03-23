# Message Flows

Living document — cross-module event flows in FluxFinance. Each diagram shows the command → event → handler chain when an action in one module triggers behavior in another via the EventBus.

**Update rule:** When you add, remove, or change an event emission or event handler, update this doc in the same commit.

---

## Event Inventory

| Event                  | Emitted By                                   | Consumed By                        |
| ---------------------- | -------------------------------------------- | ---------------------------------- |
| `MessageCreated`       | TelegramChannel, `FireScheduledTask`         | Poller (notify → early wake)       |
| `OutboundCreated`      | `ProcessMessage`, `SendMessage`              | OutboundWorker (notify → delivery) |
| `TransactionCreated`   | `AddTransaction`                             | *(future subscribers)*             |
| `TransactionUpdated`   | `UpdateTransaction`                          | *(future subscribers)*             |
| `TransactionDeleted`   | `DeleteTransaction`                          | *(future subscribers)*             |
| `MemoryCreated`        | `Remember`                                   | *(future subscribers)*             |
| `SubscriptionCreated`  | `CreateSubscription`                         | *(future subscribers)*             |
| `SavingsCreated`       | `CreateSavings`                              | *(future subscribers)*             |
| `ScheduledTaskCreated` | `CreateScheduledTask`, `ScheduleTask`        | *(future subscribers)*             |
| `ScheduledTaskDue`     | *(not yet emitted — reserved for future use)* | *(future subscribers)*            |

---

## Flow 1 — Telegram Message → AI Response

The primary end-to-end flow: user sends a Telegram message, the agent processes it via Claude + MCP tools, and the response is delivered back.

```mermaid
sequenceDiagram
    participant User as Telegram User
    participant TG as TelegramChannel
    participant DB as bot_messages
    participant EB as EventBus
    participant Poller
    participant Queue as UserQueue
    participant Handler
    participant Runner as ClaudeRunner
    participant MCP as MCP Server
    participant UC as Use Case
    participant UoW as UnitOfWork

    User->>TG: send message
    TG->>DB: INSERT (status=pending)
    TG->>EB: emit(MessageCreated)
    EB->>Poller: notify() → early wake

    Poller->>DB: fetch_pending()
    Poller->>Queue: enqueue(msg)
    Queue->>Handler: handle_message(msg) [per-user serial]

    Handler->>Runner: run(prompt, session_id?)
    Runner->>MCP: claude -p --mcp-config (stdio)

    Note over MCP,UoW: Claude may invoke MCP tools
    MCP->>UC: execute(user_id, ...)
    UC->>UoW: repo.create() + add_vector() + add_event()
    UoW->>UoW: COMMIT (SQLite + zvec)
    UoW->>EB: emit(TransactionCreated / MemoryCreated / ...)

    MCP-->>Runner: result + session_id
    Runner-->>Handler: ResultMessage
```

---

## Flow 2 — Response Delivery (OutboundCreated)

After the handler receives Claude's response, it stores the outbound message and triggers delivery.

```mermaid
sequenceDiagram
    participant Handler
    participant DB_Msg as bot_messages
    participant DB_Out as bot_outbound_messages
    participant DB_Sess as bot_sessions
    participant UoW as UnitOfWork
    participant EB as EventBus
    participant OW as OutboundWorker
    participant TG as Telegram API

    Handler->>UoW: mark_processed(msg_id)
    Handler->>UoW: insert outbound(user_id, text)
    Handler->>UoW: upsert session(user_id, session_id)
    UoW->>DB_Msg: UPDATE status=processed
    UoW->>DB_Out: INSERT (status=pending)
    UoW->>DB_Sess: UPSERT session
    UoW->>UoW: COMMIT
    UoW->>EB: emit(OutboundCreated)

    EB->>OW: notify() → early wake
    OW->>DB_Out: fetch_pending()
    OW->>TG: send_message(platform_id, text)
    OW->>DB_Out: mark_sent(outbound_id)
```

---

## Flow 3 — Scheduled Task Firing (ScheduledTaskCreated → MessageCreated)

MCP tools create scheduled tasks (subscriptions, savings, reminders). The SchedulerWorker polls for due tasks and injects synthetic messages that re-enter the main message flow.

```mermaid
sequenceDiagram
    participant MCP as MCP Tool
    participant UC as CreateScheduledTask / ScheduleTask
    participant UoW as UnitOfWork
    participant EB as EventBus
    participant DB_Task as bot_scheduled_tasks
    participant SW as SchedulerWorker
    participant Fire as FireScheduledTask
    participant DB_Msg as bot_messages
    participant Poller

    MCP->>UC: execute(user_id, schedule, ...)
    UC->>UoW: task_repo.create(task)
    UoW->>DB_Task: INSERT (status=active)
    UoW->>UoW: COMMIT
    UoW->>EB: emit(ScheduledTaskCreated)

    Note over SW: Polls for active tasks where next_run_at <= now

    SW->>DB_Task: fetch due tasks
    SW->>Fire: execute(task_id)
    Fire->>UoW: msg_repo.insert(synthetic message)
    Fire->>UoW: add_event(MessageCreated)
    UoW->>DB_Msg: INSERT (status=pending)
    UoW->>UoW: COMMIT
    UoW->>EB: emit(MessageCreated)

    EB->>Poller: notify() → early wake

    SW->>DB_Task: advance_next_run / mark_completed
```

---

## Flow 4 — Financial Entity Write (Transaction Example)

All write use cases follow the same UoW pattern: SQLite write → zvec write (if embeddings) → COMMIT → emit events.

```mermaid
sequenceDiagram
    participant Client as MCP / API
    participant UC as AddTransaction
    participant UoW as UnitOfWork
    participant SQLite
    participant zvec
    participant EB as EventBus

    Client->>UC: execute(user_id, date, amount, ...)
    UC->>UoW: BEGIN

    UC->>UoW: txn_repo.create(txn)
    UoW->>SQLite: INSERT transaction

    UC->>UoW: add_vector(collection, id, embedding, metadata)
    UC->>UoW: add_event(TransactionCreated)
    UC->>UoW: commit()

    UoW->>zvec: upsert(doc)
    UoW->>SQLite: COMMIT

    Note over UoW: Events emitted only after both stores succeed

    UoW->>EB: emit(TransactionCreated)
```

**Failure / compensation:**

```mermaid
sequenceDiagram
    participant UC as Use Case
    participant UoW as UnitOfWork
    participant SQLite
    participant zvec
    participant EB as EventBus

    UC->>UoW: commit()
    UoW->>zvec: upsert(doc) ✓
    UoW->>SQLite: COMMIT ✗ (error)
    UoW->>zvec: compensate → delete(doc)

    Note over EB: No events emitted on failure
```

---

## Flow 5 — Subscription / Savings Creation (Multi-Table + Scheduled Task)

Creating a subscription or savings asset writes to two tables and creates a scheduled task in the same UoW transaction.

```mermaid
sequenceDiagram
    participant MCP as MCP Tool
    participant UC as CreateSubscription
    participant UoW as UnitOfWork
    participant SQLite
    participant EB as EventBus

    MCP->>UC: execute(user_id, name, amount, frequency, ...)
    UC->>UoW: BEGIN

    UC->>UoW: sub_repo.create(subscription)
    UoW->>SQLite: INSERT subscription

    UC->>UoW: task_repo.create(billing_task)
    UoW->>SQLite: INSERT bot_scheduled_tasks

    UC->>UoW: add_event(SubscriptionCreated)
    UC->>UoW: commit()
    UoW->>SQLite: COMMIT

    UoW->>EB: emit(SubscriptionCreated)

    Note over EB: SchedulerWorker will later fire the billing task<br/>via Flow 3, triggering ProcessSubscriptionBilling
```

---

## Flow 6 — SendMessage (Proactive Outbound)

Use cases or MCP tools can proactively send messages to users (not in response to an inbound message).

```mermaid
sequenceDiagram
    participant Caller as MCP Tool / Use Case
    participant UC as SendMessage
    participant UoW as UnitOfWork
    participant DB as bot_outbound_messages
    participant EB as EventBus
    participant OW as OutboundWorker
    participant TG as Telegram API

    Caller->>UC: execute(user_id, text)
    UC->>UoW: out_repo.insert(user_id, text)
    UoW->>DB: INSERT (status=pending)
    UoW->>UoW: COMMIT
    UoW->>EB: emit(OutboundCreated)

    EB->>OW: notify() → early wake
    OW->>DB: fetch_pending()
    OW->>TG: send_message(platform_id, text)
    OW->>DB: mark_sent(outbound_id)
```

---

## Event Emission Invariants

1. **Events emit only after successful commit** — UoW emits `_pending_events` only after both SQLite COMMIT and zvec writes succeed.
2. **One failure does not block other subscribers** — EventBus catches and logs subscriber errors, then continues to remaining handlers.
3. **No persistence or replay** — events are fire-and-forget in-process signals. If a subscriber is down when the event fires, the event is lost (polling provides the fallback).
4. **Polling as safety net** — Poller and OutboundWorker poll on intervals regardless of events. `notify()` from EventBus provides early wake for lower latency, but correctness does not depend on it.
5. **No ordering guarantees** — multiple subscribers for the same event type may execute in any order.
