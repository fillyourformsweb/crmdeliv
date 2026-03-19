"""
Audit Logging Utility
Tracks all changes made in the system
"""
from models import AuditLog, db
from flask_login import current_user
from flask import request
import json
from datetime import datetime


def get_client_ip():
    """Get client IP address from request"""
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    return ip


def log_audit(
    action,
    entity_type,
    entity_id=None,
    entity_name=None,
    old_value=None,
    new_value=None,
    changes=None,
    client_id=None,
    client_name=None,
    order_id=None,
    receipt_number=None,
    due_amount=None,
    notes=None
):
    """
    Log an audit entry
    
    Args:
        action: CREATE, UPDATE, DELETE, PAYMENT, VERIFY, STATUS_CHANGE, ASSIGN, etc.
        entity_type: Order, Client, User, Branch, Pricing, etc.
        entity_id: ID of the entity being changed
        entity_name: Name/identifier of the entity
        old_value: JSON string or dict of old values
        new_value: JSON string or dict of new values
        changes: Human-readable description of changes
        client_id: ID of client (if applicable)
        client_name: Name of client (if applicable)
        order_id: ID of order (if applicable)
        receipt_number: Receipt number (if applicable)
        due_amount: Due amount (for alerts)
        notes: Additional notes
    """
    try:
        # Convert dicts to JSON strings if needed
        if isinstance(old_value, dict):
            old_value = json.dumps(old_value)
        if isinstance(new_value, dict):
            new_value = json.dumps(new_value)
        
        audit_log = AuditLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            username=current_user.username if current_user.is_authenticated else 'system',
            branch_id=current_user.branch_id if current_user.is_authenticated else None,
            branch_name=current_user.branch.name if (current_user.is_authenticated and current_user.branch) else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            old_value=old_value,
            new_value=new_value,
            changes=changes,
            client_id=client_id,
            client_name=client_name,
            order_id=order_id,
            receipt_number=receipt_number,
            due_amount=due_amount,
            ip_address=get_client_ip(),
            notes=notes
        )
        
        db.session.add(audit_log)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error logging audit: {str(e)}")
        db.session.rollback()
        return False


def log_order_creation(order):
    """Log order creation"""
    changes = f"Created new order: {order.receipt_number}"
    log_audit(
        action='CREATE',
        entity_type='Order',
        entity_id=order.id,
        entity_name=order.receipt_number,
        changes=changes,
        client_id=order.client_id,
        client_name=order.customer_name,
        order_id=order.id,
        receipt_number=order.receipt_number,
        due_amount=order.total_amount,
        notes=f"Order Type: {order.order_type}, Amount: ₹{order.total_amount}"
    )


def log_order_update(order, field_changes):
    """
    Log order update
    field_changes: dict of {field_name: (old_value, new_value)}
    """
    changes_list = []
    for field, (old, new) in field_changes.items():
        changes_list.append(f"{field}: {old} → {new}")
    
    changes = ", ".join(changes_list)
    
    log_audit(
        action='UPDATE',
        entity_type='Order',
        entity_id=order.id,
        entity_name=order.receipt_number,
        old_value=json.dumps({k: v[0] for k, v in field_changes.items()}),
        new_value=json.dumps({k: v[1] for k, v in field_changes.items()}),
        changes=changes,
        client_id=order.client_id,
        client_name=order.customer_name,
        order_id=order.id,
        receipt_number=order.receipt_number,
        due_amount=order.total_amount
    )


def log_order_status_change(order, old_status, new_status):
    """Log order status change"""
    changes = f"Status changed: {old_status} → {new_status}"
    log_audit(
        action='STATUS_CHANGE',
        entity_type='Order',
        entity_id=order.id,
        entity_name=order.receipt_number,
        old_value=json.dumps({'status': old_status}),
        new_value=json.dumps({'status': new_status}),
        changes=changes,
        client_id=order.client_id,
        client_name=order.customer_name,
        order_id=order.id,
        receipt_number=order.receipt_number
    )


def log_order_payment(order, amount_paid, payment_mode):
    """Log order payment"""
    changes = f"Payment received: ₹{amount_paid} via {payment_mode}"
    log_audit(
        action='PAYMENT',
        entity_type='Order',
        entity_id=order.id,
        entity_name=order.receipt_number,
        changes=changes,
        client_id=order.client_id,
        client_name=order.customer_name,
        order_id=order.id,
        receipt_number=order.receipt_number,
        due_amount=order.total_amount - amount_paid,
        notes=f"Amount: ₹{amount_paid}, Mode: {payment_mode}"
    )


def log_order_verification(order):
    """Log order verification"""
    changes = f"Order verified and marked as delivered"
    log_audit(
        action='VERIFY',
        entity_type='Order',
        entity_id=order.id,
        entity_name=order.receipt_number,
        changes=changes,
        client_id=order.client_id,
        client_name=order.customer_name,
        order_id=order.id,
        receipt_number=order.receipt_number
    )


def log_delivery_assignment(order, delivery_person_name):
    """Log delivery person assignment"""
    changes = f"Assigned to delivery person: {delivery_person_name}"
    log_audit(
        action='ASSIGN',
        entity_type='Order',
        entity_id=order.id,
        entity_name=order.receipt_number,
        changes=changes,
        client_id=order.client_id,
        client_name=order.customer_name,
        order_id=order.id,
        receipt_number=order.receipt_number,
        notes=f"Delivery Person: {delivery_person_name}"
    )


def log_client_creation(client):
    """Log client creation"""
    changes = f"Created new client: {client.name}"
    log_audit(
        action='CREATE',
        entity_type='Client',
        entity_id=client.id,
        entity_name=client.name,
        changes=changes,
        client_id=client.id,
        client_name=client.name,
        notes=f"Company: {client.company_name}, Email: {client.email}"
    )


def log_client_update(client, field_changes):
    """Log client update"""
    changes_list = []
    for field, (old, new) in field_changes.items():
        changes_list.append(f"{field}: {old} → {new}")
    
    changes = ", ".join(changes_list)
    
    log_audit(
        action='UPDATE',
        entity_type='Client',
        entity_id=client.id,
        entity_name=client.name,
        old_value=json.dumps({k: str(v[0]) for k, v in field_changes.items()}),
        new_value=json.dumps({k: str(v[1]) for k, v in field_changes.items()}),
        changes=changes,
        client_id=client.id,
        client_name=client.name
    )


def log_user_action(user, action, description):
    """Log user-related actions"""
    log_audit(
        action=action,
        entity_type='User',
        entity_id=user.id,
        entity_name=user.username,
        changes=description,
        notes=f"User: {user.username}, Role: {user.role}"
    )


def log_pricing_change(entity_type, entity_id, entity_name, old_pricing, new_pricing):
    """Log pricing changes"""
    changes = "Pricing updated"
    log_audit(
        action='UPDATE',
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        old_value=json.dumps(old_pricing),
        new_value=json.dumps(new_pricing),
        changes=changes,
        notes="Pricing configuration changed"
    )


def log_due_alert(client_id, client_name, total_due):
    """Log due amount alerts"""
    if total_due > 0:
        log_audit(
            action='UPDATE',
            entity_type='Client',
            entity_id=client_id,
            entity_name=client_name,
            changes=f"Client due amount alert: ₹{total_due}",
            client_id=client_id,
            client_name=client_name,
            due_amount=total_due,
            notes=f"Outstanding due: ₹{total_due}"
        )
