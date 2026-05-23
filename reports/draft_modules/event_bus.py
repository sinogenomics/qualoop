# -*- coding: utf-8 -*-
"""
Qualoop Event Bus - Draft Implementation
Provides a SQLite-backed publish-subscribe messaging framework.
Enables asynchronous, event-driven decoupled agent execution.
"""
import os
import sys
import sqlite3
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EventBus")

class EventBus(object):
    def __init__(self, db_path="scratch/qualoop_events.db"):
        self.db_path = db_path
        self.subscribers = {}
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite event store table."""
        dir_name = os.path.dirname(self.db_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at REAL NOT NULL,
                processed_at REAL
            )
        """)
        conn.commit()
        conn.close()

    def subscribe(self, event_type, callback):
        """Registers a callback function for a specific event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        logger.info("Subscriber registered for event: %s", event_type)

    def publish(self, event_type, payload_dict):
        """Publishes an event to the persistent SQLite message store."""
        payload_str = json.dumps(payload_dict)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO events (event_type, payload, created_at) VALUES (?, ?, ?)",
            (event_type, payload_str, time.time())
        )
        conn.commit()
        conn.close()
        logger.info("Published event: %s", event_type)

    def process_pending_events(self):
        """Polls and dispatches pending events to registered subscribers."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, event_type, payload FROM events WHERE status = 'PENDING' ORDER BY id ASC")
        rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            return 0

        logger.info("Found %d pending events to process.", len(rows))
        processed_count = 0
        
        for event_id, event_type, payload_str in rows:
            payload = json.loads(payload_str)
            
            # Update status to PROCESSING to prevent double execution
            cursor.execute("UPDATE events SET status = 'PROCESSING' WHERE id = ?", (event_id,))
            conn.commit()
            
            # Dispatch to subscribers
            success = True
            if event_type in self.subscribers:
                for callback in self.subscribers[event_type]:
                    try:
                        logger.info("Dispatching event %s (ID %d) to callback: %s", event_type, event_id, callback.__name__)
                        callback(payload)
                    except Exception as e:
                        logger.error("Error in subscriber callback for %s: %s", event_type, str(e))
                        success = False
            
            # Update status to final state
            final_status = "COMPLETED" if success else "FAILED"
            cursor.execute(
                "UPDATE events SET status = ?, processed_at = ? WHERE id = ?",
                (final_status, time.time(), event_id)
            )
            conn.commit()
            processed_count += 1
            
        conn.close()
        return processed_count

if __name__ == "__main__":
    # Test execution
    bus = EventBus("scratch/qualoop_events.db")
    
    # Define subscriber callbacks mimicking Qualoop roles
    def mock_scorer(payload):
        print("[Scorer Callback] Received issue payload! Scoring issue ID:", payload.get("issue_id"))
        # Publish Scored Event
        bus.publish("issue_scored", {"issue_id": payload.get("issue_id"), "score": 85})

    def mock_scheduler(payload):
        print("[Scheduler Callback] Received scored issue! Score is:", payload.get("score"))

    # Register subscribers
    bus.subscribe("issue_detected", mock_scorer)
    bus.subscribe("issue_scored", mock_scheduler)
    
    # Simulate workflow by publishing initial event
    print("\nStarting event bus simulation...")
    bus.publish("issue_detected", {"issue_id": "QL-BUG-999", "file": "src/main.py", "issue_type": "NullPointer"})
    
    # Run event dispatcher loop
    print("\nProcessing initial events:")
    bus.process_pending_events()
    
    print("\nProcessing cascaded events (should dispatch to Scheduler):")
    bus.process_pending_events()
    
    # Clean up test DB file
    try:
        os.remove("scratch/qualoop_events.db")
        logger.info("Cleaned up test database.")
    except Exception:
        pass
