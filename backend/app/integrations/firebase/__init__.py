"""Firebase integration (read-only).

The Raspberry Pi runs the vision model and writes raw per-item detections
(organic "O" / recyclable "R" + confidence) to Firebase Realtime Database. This
package reads that stream and aggregates it into the normalized analysis the
business layer consumes — behind the `RequestDataProvider` interface, so nothing
in the domain knows the data came from Firebase.

Strictly read-only: the backend never writes to Firebase (the Raspberry does).
"""
