"""In-app notifications.

Persisted, per-user notifications raised by domain events (currently collection-
request status changes). Delivered live over the targeted WebSocket and readable
any time from the DB, so nothing is lost while a user is offline.
"""
