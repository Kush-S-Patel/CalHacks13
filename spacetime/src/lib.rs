//! SwarmCFO — SpacetimeDB shared financial world.
//! Claude decides; these reducers execute. Every action is auditable state.

use spacetimedb::{reducer, table, ReducerContext, Table, Timestamp};

// ─── Tables ─────────────────────────────────────────────────────────────────

#[table(name = room, public)]
pub struct Room {
    #[primary_key]
    pub id: String,
    pub owner_name: String,
    pub business_name: String,
    pub cash_balance_cents: i64,
    pub daily_burn_cents: i64,
    pub runway_days: f64,
    pub updated_at: Timestamp,
}

#[table(name = supplier, public)]
pub struct Supplier {
    #[primary_key]
    pub id: String,
    pub room_id: String,
    pub name: String,
    pub category: String,
    pub unit_price_cents: i64,
    pub bank_fingerprint: String,
    pub trust_score: f64,
    pub active: bool,
}

#[table(name = invoice, public)]
pub struct Invoice {
    #[primary_key]
    pub id: String,
    pub room_id: String,
    pub vendor_name: String,
    pub amount_cents: i64,
    pub bank_fingerprint: String,
    pub due_date_iso: String,
    pub status: String, // open | blocked | paid | held | disputed
    pub duplicate_of: Option<String>,
    pub content_hash: String,
    pub created_at: Timestamp,
}

#[table(name = receivable, public)]
pub struct Receivable {
    #[primary_key]
    pub id: String,
    pub room_id: String,
    pub customer_name: String,
    pub amount_cents: i64,
    pub days_late: i32,
    pub status: String, // open | chasing | paid | incentivized
    pub last_chase_at: Option<Timestamp>,
}

#[table(name = agent_action, public)]
#[derive(Clone)]
pub struct AgentAction {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    pub room_id: String,
    pub agent: String, // cfo | risk | procurement | collections | cashier
    pub action_type: String, // block | counter | chase | pay | hold | defer | arbitrate
    pub target_id: String,
    pub rationale: String,
    pub amount_cents: i64,
    pub created_at: Timestamp,
}

#[table(name = approval, public)]
pub struct Approval {
    #[primary_key]
    pub id: String,
    pub room_id: String,
    pub kind: String, // payment
    pub description: String,
    pub amount_cents: i64,
    pub status: String, // waiting | approved | rejected
    pub requested_by: String,
    pub created_at: Timestamp,
    pub resolved_at: Option<Timestamp>,
}

#[table(name = chaos_event, public)]
pub struct ChaosEvent {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    pub room_id: String,
    pub kind: String, // price_spike | duplicate_invoice | late_ar
    pub payload_json: String,
    pub injected_by: String,
    pub created_at: Timestamp,
}

// ─── Helpers ────────────────────────────────────────────────────────────────

fn recompute_runway(cash_cents: i64, burn_cents: i64) -> f64 {
    if burn_cents <= 0 {
        return 999.0;
    }
    cash_cents as f64 / burn_cents as f64
}

fn content_hash(amount_cents: i64, bank_fingerprint: &str, due_date_iso: &str) -> String {
    format!("{}|{}|{}", amount_cents, bank_fingerprint, due_date_iso)
}

// ─── Reducers ───────────────────────────────────────────────────────────────

#[reducer]
pub fn seed_maya_bakery(ctx: &ReducerContext) {
    let room_id = "maya-bakery".to_string();
    if ctx.db.room().id().find(&room_id).is_some() {
        return;
    }

    let cash = 1_840_000_i64; // $18,400
    let burn = 165_000_i64; // $1,650/day
    ctx.db.room().insert(Room {
        id: room_id.clone(),
        owner_name: "Maya".into(),
        business_name: "Maya's Bakery".into(),
        cash_balance_cents: cash,
        daily_burn_cents: burn,
        runway_days: recompute_runway(cash, burn),
        updated_at: ctx.timestamp,
    });

    // Four suppliers
    let suppliers = [
        ("sup-flour-co", "North Bay Flour Co", "flour", 42_00, "bank-nbflour-001", 0.92),
        ("sup-dairy", "Valley Dairy", "dairy", 28_50, "bank-valley-002", 0.88),
        ("sup-packaging", "ClearWrap Packaging", "packaging", 18_00, "bank-clearwrap-003", 0.75),
        ("sup-alt-flour", "Coastal Grain Alt", "flour", 38_00, "bank-coastal-004", 0.70),
    ];
    for (id, name, cat, price, bank, trust) in suppliers {
        ctx.db.supplier().insert(Supplier {
            id: id.into(),
            room_id: room_id.clone(),
            name: name.into(),
            category: cat.into(),
            unit_price_cents: price,
            bank_fingerprint: bank.into(),
            trust_score: trust,
            active: true,
        });
    }
}

#[reducer]
pub fn inject_chaos(ctx: &ReducerContext, room_id: String, kind: String, payload_json: String, injected_by: String) {
    ctx.db.chaos_event().insert(ChaosEvent {
        id: 0,
        room_id: room_id.clone(),
        kind: kind.clone(),
        payload_json: payload_json.clone(),
        injected_by,
        created_at: ctx.timestamp,
    });

    match kind.as_str() {
        "price_spike" => {
            // Default demo: flour supplier +40%
            if let Some(mut s) = ctx.db.supplier().id().find("sup-flour-co") {
                s.unit_price_cents = (s.unit_price_cents as f64 * 1.40) as i64;
                ctx.db.supplier().id().update(s);
            }
        }
        "duplicate_invoice" => {
            let amount = 420_000_i64; // $4,200
            let bank = "bank-nbflour-001".to_string();
            let due = "2026-10-25".to_string();
            let hash = content_hash(amount, &bank, &due);
            // Original already "paid" twin for duplicate detection
            ctx.db.invoice().insert(Invoice {
                id: "inv-dup-original".into(),
                room_id: room_id.clone(),
                vendor_name: "North Bay Flour Co".into(),
                amount_cents: amount,
                bank_fingerprint: bank.clone(),
                due_date_iso: due.clone(),
                status: "paid".into(),
                duplicate_of: None,
                content_hash: hash.clone(),
                created_at: ctx.timestamp,
            });
            ctx.db.invoice().insert(Invoice {
                id: "inv-dup-incoming".into(),
                room_id: room_id.clone(),
                vendor_name: "North Bay Flour Co".into(),
                amount_cents: amount,
                bank_fingerprint: bank,
                due_date_iso: due,
                status: "open".into(),
                duplicate_of: None,
                content_hash: hash,
                created_at: ctx.timestamp,
            });
        }
        "late_ar" => {
            ctx.db.receivable().insert(Receivable {
                id: "ar-big-cafe".into(),
                room_id,
                customer_name: "Harbor Cafe Group".into(),
                amount_cents: 920_000, // $9,200
                days_late: 12,
                status: "open".into(),
                last_chase_at: None,
            });
        }
        _ => {}
    }
}

#[reducer]
pub fn block_invoice(
    ctx: &ReducerContext,
    room_id: String,
    invoice_id: String,
    agent: String,
    rationale: String,
    duplicate_of: Option<String>,
) {
    if let Some(mut inv) = ctx.db.invoice().id().find(&invoice_id) {
        inv.status = "blocked".into();
        inv.duplicate_of = duplicate_of;
        let amount = inv.amount_cents;
        ctx.db.invoice().id().update(inv);

        ctx.db.agent_action().insert(AgentAction {
            id: 0,
            room_id,
            agent,
            action_type: "block".into(),
            target_id: invoice_id,
            rationale,
            amount_cents: amount,
            created_at: ctx.timestamp,
        });
    }
}

#[reducer]
pub fn counter_offer(
    ctx: &ReducerContext,
    room_id: String,
    from_supplier_id: String,
    to_supplier_id: String,
    agent: String,
    rationale: String,
    proposed_price_cents: i64,
) {
    ctx.db.agent_action().insert(AgentAction {
        id: 0,
        room_id,
        agent,
        action_type: "counter".into(),
        target_id: format!("{}→{}", from_supplier_id, to_supplier_id),
        rationale,
        amount_cents: proposed_price_cents,
        created_at: ctx.timestamp,
    });
}

#[reducer]
pub fn chase_ar(ctx: &ReducerContext, room_id: String, receivable_id: String, agent: String, rationale: String) {
    if let Some(mut ar) = ctx.db.receivable().id().find(&receivable_id) {
        ar.status = "chasing".into();
        ar.last_chase_at = Some(ctx.timestamp);
        let amount = ar.amount_cents;
        ctx.db.receivable().id().update(ar);

        ctx.db.agent_action().insert(AgentAction {
            id: 0,
            room_id,
            agent,
            action_type: "chase".into(),
            target_id: receivable_id,
            rationale,
            amount_cents: amount,
            created_at: ctx.timestamp,
        });
    }
}

#[reducer]
pub fn hold_payment(
    ctx: &ReducerContext,
    room_id: String,
    approval_id: String,
    description: String,
    amount_cents: i64,
    agent: String,
    rationale: String,
) {
    ctx.db.approval().insert(Approval {
        id: approval_id.clone(),
        room_id: room_id.clone(),
        kind: "payment".into(),
        description,
        amount_cents,
        status: "waiting".into(),
        requested_by: agent.clone(),
        created_at: ctx.timestamp,
        resolved_at: None,
    });

    ctx.db.agent_action().insert(AgentAction {
        id: 0,
        room_id,
        agent,
        action_type: "hold".into(),
        target_id: approval_id,
        rationale,
        amount_cents,
        created_at: ctx.timestamp,
    });
}

#[reducer]
pub fn pay(
    ctx: &ReducerContext,
    room_id: String,
    target_id: String,
    amount_cents: i64,
    agent: String,
    rationale: String,
) {
    // Autonomy enforced by agent service; reducer records execution.
    if let Some(mut room) = ctx.db.room().id().find(&room_id) {
        room.cash_balance_cents -= amount_cents;
        room.runway_days = recompute_runway(room.cash_balance_cents, room.daily_burn_cents);
        room.updated_at = ctx.timestamp;
        ctx.db.room().id().update(room);
    }

    ctx.db.agent_action().insert(AgentAction {
        id: 0,
        room_id,
        agent,
        action_type: "pay".into(),
        target_id,
        rationale,
        amount_cents,
        created_at: ctx.timestamp,
    });
}

#[reducer]
pub fn approve(ctx: &ReducerContext, approval_id: String) {
    if let Some(mut a) = ctx.db.approval().id().find(&approval_id) {
        if a.status != "waiting" {
            return;
        }
        a.status = "approved".into();
        a.resolved_at = Some(ctx.timestamp);
        let room_id = a.room_id.clone();
        let amount = a.amount_cents;
        let desc = a.description.clone();
        ctx.db.approval().id().update(a);

        if let Some(mut room) = ctx.db.room().id().find(&room_id) {
            room.cash_balance_cents -= amount;
            room.runway_days = recompute_runway(room.cash_balance_cents, room.daily_burn_cents);
            room.updated_at = ctx.timestamp;
            ctx.db.room().id().update(room);
        }

        ctx.db.agent_action().insert(AgentAction {
            id: 0,
            room_id,
            agent: "owner".into(),
            action_type: "approve".into(),
            target_id: approval_id,
            rationale: format!("Owner approved: {}", desc),
            amount_cents: amount,
            created_at: ctx.timestamp,
        });
    }
}

#[reducer]
pub fn defer_spend(
    ctx: &ReducerContext,
    room_id: String,
    amount_cents: i64,
    agent: String,
    rationale: String,
) {
    // Deferring non-critical spend effectively reduces near-term burn / frees cash.
    if let Some(mut room) = ctx.db.room().id().find(&room_id) {
        room.cash_balance_cents += amount_cents; // cash preserved / burn deferred
        room.runway_days = recompute_runway(room.cash_balance_cents, room.daily_burn_cents);
        room.updated_at = ctx.timestamp;
        ctx.db.room().id().update(room);
    }

    ctx.db.agent_action().insert(AgentAction {
        id: 0,
        room_id,
        agent,
        action_type: "defer".into(),
        target_id: "noncritical-spend".into(),
        rationale,
        amount_cents,
        created_at: ctx.timestamp,
    });
}

#[reducer]
pub fn arbitrate(
    ctx: &ReducerContext,
    room_id: String,
    decision: String,
    target_id: String,
    rationale: String,
) {
    ctx.db.agent_action().insert(AgentAction {
        id: 0,
        room_id,
        agent: "cfo".into(),
        action_type: "arbitrate".into(),
        target_id,
        rationale: format!("{} — {}", decision, rationale),
        amount_cents: 0,
        created_at: ctx.timestamp,
    });
}

#[reducer]
pub fn recompute_runway(ctx: &ReducerContext, room_id: String) {
    if let Some(mut room) = ctx.db.room().id().find(&room_id) {
        room.runway_days = recompute_runway(room.cash_balance_cents, room.daily_burn_cents);
        room.updated_at = ctx.timestamp;
        ctx.db.room().id().update(room);
    }
}