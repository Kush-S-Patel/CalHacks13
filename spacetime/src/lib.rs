//! SwarmCFO SpacetimeDB — shared system of work (Hyphenate Build 1–4).
//! Systems of record stay external. This module is the execution platform:
//! work items, policies, precedents, audit diffs, multiplayer subscriptions.

use spacetimedb::{reducer, table, ReducerContext, Table, Timestamp};

#[table(name = room, public)]
pub struct Room {
    #[primary_key]
    pub id: String,
    pub owner_name: String,
    pub business_name: String,
    pub cash_balance_cents: i64,
    pub daily_burn_cents: i64,
    pub runway_days: f64,
    pub hyphenate_score: i32,
    pub updated_at: Timestamp,
}

#[table(name = golden_record, public)]
pub struct GoldenRecord {
    #[primary_key]
    pub id: String,
    pub room_id: String,
    pub kind: String, // bank_transaction | invoice | vendor | customer
    pub source: String,
    pub raw_ref: String,
    pub data_json: String,
}

#[table(name = work_item, public)]
pub struct WorkItem {
    #[primary_key]
    pub id: String,
    pub room_id: String,
    pub kind: String,
    pub state: String, // NEW|PROPOSED|NEEDS_INFO|HELD|BLOCKED|APPROVED|REJECTED|POSTED
    pub subject: String,
    pub title: String,
    pub amount_cents: i64,
    pub proposed_by: Option<String>,
    pub approved_by: Option<String>,
    pub policy_id: Option<String>,
    pub question: Option<String>,
    pub answer: Option<String>,
    pub payload_json: String,
    pub evidence_json: String,
    pub updated_at: Timestamp,
}

#[table(name = policy, public)]
pub struct Policy {
    #[primary_key]
    pub id: String,
    pub room_id: String,
    pub version: i32,
    pub title: String,
    pub rule: String,
    pub status: String, // needs_approval | active | rejected
    pub proposed_by: Option<String>,
    pub approved_by: Option<String>,
    pub evidence_json: String,
}

#[table(name = precedent, public)]
pub struct Precedent {
    #[primary_key]
    pub id: String,
    pub room_id: String,
    pub kind: String,
    pub summary: String,
    pub subject: String,
    pub tags_json: String,
    pub correction_json: String,
}

#[table(name = audit_event, public)]
pub struct AuditEvent {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    pub room_id: String,
    pub at: Timestamp,
    pub actor: String,
    pub action: String,
    pub subject: String,
    pub allowed: bool,
    pub reason: String,
    pub diff_json: String,
    pub evidence_json: String,
}

fn runway(cash: i64, burn: i64) -> f64 {
    if burn <= 0 {
        999.0
    } else {
        cash as f64 / burn as f64
    }
}

#[reducer]
pub fn seed_maya_bakery(ctx: &ReducerContext) {
    let room_id = "maya-bakery".to_string();
    if ctx.db.room().id().find(&room_id).is_some() {
        return;
    }
    let cash = 1_840_000_i64;
    let burn = 165_000_i64;
    ctx.db.room().insert(Room {
        id: room_id,
        owner_name: "Maya".into(),
        business_name: "Maya's Bakery".into(),
        cash_balance_cents: cash,
        daily_burn_cents: burn,
        runway_days: runway(cash, burn),
        hyphenate_score: 0,
        updated_at: ctx.timestamp,
    });
}

#[reducer]
pub fn upsert_work_item(
    ctx: &ReducerContext,
    id: String,
    room_id: String,
    kind: String,
    state: String,
    subject: String,
    title: String,
    amount_cents: i64,
    proposed_by: Option<String>,
    approved_by: Option<String>,
    policy_id: Option<String>,
    question: Option<String>,
    answer: Option<String>,
    payload_json: String,
    evidence_json: String,
) {
    let row = WorkItem {
        id: id.clone(),
        room_id,
        kind,
        state,
        subject,
        title,
        amount_cents,
        proposed_by,
        approved_by,
        policy_id,
        question,
        answer,
        payload_json,
        evidence_json,
        updated_at: ctx.timestamp,
    };
    if ctx.db.work_item().id().find(&id).is_some() {
        ctx.db.work_item().id().update(row);
    } else {
        ctx.db.work_item().insert(row);
    }
}

#[reducer]
pub fn append_audit(
    ctx: &ReducerContext,
    room_id: String,
    actor: String,
    action: String,
    subject: String,
    allowed: bool,
    reason: String,
    diff_json: String,
    evidence_json: String,
) {
    ctx.db.audit_event().insert(AuditEvent {
        id: 0,
        room_id,
        at: ctx.timestamp,
        actor,
        action,
        subject,
        allowed,
        reason,
        diff_json,
        evidence_json,
    });
}

#[reducer]
pub fn upsert_policy(
    ctx: &ReducerContext,
    id: String,
    room_id: String,
    version: i32,
    title: String,
    rule: String,
    status: String,
    proposed_by: Option<String>,
    approved_by: Option<String>,
    evidence_json: String,
) {
    let row = Policy {
        id: id.clone(),
        room_id,
        version,
        title,
        rule,
        status,
        proposed_by,
        approved_by,
        evidence_json,
    };
    if ctx.db.policy().id().find(&id).is_some() {
        ctx.db.policy().id().update(row);
    } else {
        ctx.db.policy().insert(row);
    }
}

#[reducer]
pub fn set_runway(ctx: &ReducerContext, room_id: String, cash_balance_cents: i64, hyphenate_score: i32) {
    if let Some(mut room) = ctx.db.room().id().find(&room_id) {
        room.cash_balance_cents = cash_balance_cents;
        room.runway_days = runway(cash_balance_cents, room.daily_burn_cents);
        room.hyphenate_score = hyphenate_score;
        room.updated_at = ctx.timestamp;
        ctx.db.room().id().update(room);
    }
}

#[reducer]
pub fn owner_approve(ctx: &ReducerContext, work_item_id: String, actor: String) {
    if let Some(mut item) = ctx.db.work_item().id().find(&work_item_id) {
        if item.state != "HELD" && item.state != "PROPOSED" {
            return;
        }
        let before = item.state.clone();
        item.state = "APPROVED".into();
        item.approved_by = Some(actor.clone());
        item.updated_at = ctx.timestamp;
        let room_id = item.room_id.clone();
        ctx.db.work_item().id().update(item);

        ctx.db.audit_event().insert(AuditEvent {
            id: 0,
            room_id,
            at: ctx.timestamp,
            actor,
            action: "approve".into(),
            subject: work_item_id,
            allowed: true,
            reason: "owner one-tap".into(),
            diff_json: format!(r#"{{"state":{{"from":"{}","to":"APPROVED"}}}}"#, before),
            evidence_json: "[]".into(),
        });
    }
}