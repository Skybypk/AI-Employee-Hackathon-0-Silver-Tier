#!/usr/bin/env python3
"""
Human-in-the-Loop Approval Workflow
Manages the approval process for actions requiring human review
Part of the Personal AI Employee Silver Tier implementation
"""

import os
import sys
import json
import time
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# Configuration
VAULT_BASE = Path(__file__).parent / "AI_Employee_Vault"
INBOX_DIR = VAULT_BASE / "Inbox"
NEEDS_ACTION_DIR = VAULT_BASE / "Needs_Action"
PENDING_APPROVAL_DIR = VAULT_BASE / "Pending_Approval"
APPROVED_DIR = VAULT_BASE / "Approved"
REJECTED_DIR = VAULT_BASE / "Rejected"
DONE_DIR = VAULT_BASE / "Done"
LOGS_DIR = VAULT_BASE / "Logs"
PLANS_DIR = VAULT_BASE / "Plans"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "approval_workflow.log" if LOGS_DIR.exists() else "approval_workflow.log")
    ]
)
logger = logging.getLogger(__name__)


class ApprovalWorkflow:
    """Manages the human-in-the-loop approval workflow."""
    
    def __init__(self):
        self.error_count = 0
        self.max_errors = 5
        
        # Ensure all directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all vault directories exist."""
        dirs = [
            INBOX_DIR, NEEDS_ACTION_DIR, PENDING_APPROVAL_DIR,
            APPROVED_DIR, REJECTED_DIR, DONE_DIR, LOGS_DIR, PLANS_DIR
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def submit_for_approval(self, item: Dict[str, Any], source_path: Optional[Path] = None) -> Path:
        """Submit an item for human approval."""
        try:
            # Create approval request
            approval_request = {
                "id": f"approval_{int(time.time())}",
                "submitted_at": datetime.now().isoformat(),
                "status": "pending",
                "item": item,
                "source_path": str(source_path) if source_path else None,
                "action_required": item.get("action_required", "Review and approve/reject"),
                "priority": item.get("priority", "medium"),
                "deadline": item.get("deadline"),
                "metadata": item.get("metadata", {}),
            }
            
            # Save to pending approval
            filename = f"{approval_request['id']}.json"
            filepath = PENDING_APPROVAL_DIR / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(approval_request, f, indent=2, ensure_ascii=False)
            
            # Copy source file if provided
            if source_path and source_path.exists():
                dest_path = PENDING_APPROVAL_DIR / source_path.name
                shutil.copy2(source_path, dest_path)
                approval_request["attached_file"] = str(dest_path)
                
                # Update the request file
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(approval_request, f, indent=2, ensure_ascii=False)
            
            # Log the submission
            self._log_action("submitted", approval_request)
            
            logger.info(f"Submitted for approval: {approval_request['id']}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error submitting for approval: {e}")
            self.error_count += 1
            raise
    
    def approve(self, approval_id: str, notes: Optional[str] = None) -> bool:
        """Approve a pending item."""
        try:
            # Find the approval request
            request_file = PENDING_APPROVAL_DIR / f"{approval_id}.json"
            
            if not request_file.exists():
                logger.error(f"Approval request not found: {approval_id}")
                return False
            
            # Load the request
            with open(request_file, "r", encoding="utf-8") as f:
                request = json.load(f)
            
            # Update status
            request["status"] = "approved"
            request["approved_at"] = datetime.now().isoformat()
            request["notes"] = notes
            
            # Move to approved directory
            approved_file = APPROVED_DIR / f"{approval_id}.json"
            with open(approved_file, "w", encoding="utf-8") as f:
                json.dump(request, f, indent=2, ensure_ascii=False)
            
            # Remove from pending
            request_file.unlink()
            
            # Move attached file if exists
            if request.get("attached_file"):
                attached = Path(request["attached_file"])
                if attached.exists():
                    dest = APPROVED_DIR / attached.name
                    shutil.copy2(attached, dest)
            
            # Log the approval
            self._log_action("approved", request)
            
            logger.info(f"Approved: {approval_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error approving item: {e}")
            self.error_count += 1
            return False
    
    def reject(self, approval_id: str, reason: str) -> bool:
        """Reject a pending item."""
        try:
            # Find the approval request
            request_file = PENDING_APPROVAL_DIR / f"{approval_id}.json"
            
            if not request_file.exists():
                logger.error(f"Approval request not found: {approval_id}")
                return False
            
            # Load the request
            with open(request_file, "r", encoding="utf-8") as f:
                request = json.load(f)
            
            # Update status
            request["status"] = "rejected"
            request["rejected_at"] = datetime.now().isoformat()
            request["rejection_reason"] = reason
            
            # Move to rejected directory
            rejected_file = REJECTED_DIR / f"{approval_id}.json"
            with open(rejected_file, "w", encoding="utf-8") as f:
                json.dump(request, f, indent=2, ensure_ascii=False)
            
            # Remove from pending
            request_file.unlink()
            
            # Move attached file if exists
            if request.get("attached_file"):
                attached = Path(request["attached_file"])
                if attached.exists():
                    dest = REJECTED_DIR / attached.name
                    shutil.copy2(attached, dest)
            
            # Log the rejection
            self._log_action("rejected", request)
            
            logger.info(f"Rejected: {approval_id}, Reason: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error rejecting item: {e}")
            self.error_count += 1
            return False
    
    def get_pending_items(self) -> List[Dict[str, Any]]:
        """Get all pending approval items."""
        items = []
        
        try:
            for file_path in PENDING_APPROVAL_DIR.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    items.append(data)
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
            
            # Sort by submission time
            items.sort(key=lambda x: x.get("submitted_at", ""))
            
        except Exception as e:
            logger.error(f"Error getting pending items: {e}")
        
        return items
    
    def get_approval_status(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific approval request."""
        try:
            # Check pending
            pending_file = PENDING_APPROVAL_DIR / f"{approval_id}.json"
            if pending_file.exists():
                with open(pending_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            # Check approved
            approved_file = APPROVED_DIR / f"{approval_id}.json"
            if approved_file.exists():
                with open(approved_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            # Check rejected
            rejected_file = REJECTED_DIR / f"{approval_id}.json"
            if rejected_file.exists():
                with open(rejected_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting approval status: {e}")
            return None
    
    def execute_approved_action(self, approval_id: str) -> bool:
        """Execute an approved action."""
        try:
            # Get the approval
            approved_file = APPROVED_DIR / f"{approval_id}.json"
            
            if not approved_file.exists():
                logger.error(f"Approved item not found: {approval_id}")
                return False
            
            with open(approved_file, "r", encoding="utf-8") as f:
                request = json.load(f)
            
            # Check if already executed
            if request.get("executed"):
                logger.warning(f"Action already executed: {approval_id}")
                return True
            
            # Execute based on action type
            action_type = request.get("item", {}).get("action_type", "general")
            result = self._execute_action(action_type, request)
            
            # Update status
            request["executed"] = True
            request["executed_at"] = datetime.now().isoformat()
            request["execution_result"] = result
            
            with open(approved_file, "w", encoding="utf-8") as f:
                json.dump(request, f, indent=2, ensure_ascii=False)
            
            # Move to Done
            done_file = DONE_DIR / f"{approval_id}.json"
            shutil.copy2(approved_file, done_file)
            
            # Log execution
            self._log_action("executed", request)
            
            logger.info(f"Executed approved action: {approval_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing approved action: {e}")
            return False
    
    def _execute_action(self, action_type: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action based on type."""
        result = {
            "action_type": action_type,
            "status": "completed",
            "details": {},
        }
        
        if action_type == "send_email":
            # Would integrate with email MCP
            result["details"] = {"message": "Email action would be executed via MCP"}
        
        elif action_type == "file_operation":
            # Would perform file operations
            result["details"] = {"message": "File operation would be executed"}
        
        elif action_type == "api_call":
            # Would make API calls
            result["details"] = {"message": "API call would be executed"}
        
        else:
            result["details"] = {"message": f"General action '{action_type}' completed"}
        
        return result
    
    def _log_action(self, action: str, data: Dict[str, Any]):
        """Log an approval action."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "approval_id": data.get("id"),
                "status": data.get("status"),
            }
            
            # Append to daily log
            log_file = LOGS_DIR / f"approval_log_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.warning(f"Failed to log action: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get approval workflow statistics."""
        try:
            stats = {
                "pending": len(list(PENDING_APPROVAL_DIR.glob("*.json"))),
                "approved": len(list(APPROVED_DIR.glob("*.json"))),
                "rejected": len(list(REJECTED_DIR.glob("*.json"))),
                "done": len(list(DONE_DIR.glob("*.json"))),
            }
            
            # Calculate approval rate
            total_decided = stats["approved"] + stats["rejected"]
            if total_decided > 0:
                stats["approval_rate"] = round(stats["approved"] / total_decided * 100, 2)
            else:
                stats["approval_rate"] = 0
            
            stats["timestamp"] = datetime.now().isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
    
    def cleanup_old_items(self, days: int = 30) -> int:
        """Clean up old items from approved/rejected directories."""
        try:
            cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
            cleaned = 0
            
            for directory in [APPROVED_DIR, REJECTED_DIR]:
                for file_path in directory.glob("*.json"):
                    try:
                        with open(file_path, "r") as f:
                            data = json.load(f)
                        
                        # Check if old enough
                        timestamp_str = data.get("approved_at") or data.get("rejected_at", "")
                        if timestamp_str:
                            timestamp = datetime.fromisoformat(timestamp_str).timestamp()
                            if timestamp < cutoff:
                                file_path.unlink()
                                cleaned += 1
                    except:
                        continue
            
            logger.info(f"Cleaned up {cleaned} old items")
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
            return 0


def main():
    """Entry point for approval workflow CLI."""
    import argparse
    
    workflow = ApprovalWorkflow()
    
    parser = argparse.ArgumentParser(description="Approval Workflow CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List pending
    list_parser = subparsers.add_parser("list", help="List pending approvals")
    
    # Approve
    approve_parser = subparsers.add_parser("approve", help="Approve an item")
    approve_parser.add_argument("id", help="Approval ID")
    approve_parser.add_argument("--notes", help="Approval notes")
    
    # Reject
    reject_parser = subparsers.add_parser("reject", help="Reject an item")
    reject_parser.add_argument("id", help="Approval ID")
    reject_parser.add_argument("--reason", required=True, help="Rejection reason")
    
    # Stats
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    
    # Execute
    exec_parser = subparsers.add_parser("execute", help="Execute approved action")
    exec_parser.add_argument("id", help="Approval ID")
    
    args = parser.parse_args()
    
    if args.command == "list":
        items = workflow.get_pending_items()
        print(json.dumps(items, indent=2))
    
    elif args.command == "approve":
        success = workflow.approve(args.id, args.notes)
        print(f"Approved: {success}")
    
    elif args.command == "reject":
        success = workflow.reject(args.id, args.reason)
        print(f"Rejected: {success}")
    
    elif args.command == "stats":
        stats = workflow.get_statistics()
        print(json.dumps(stats, indent=2))
    
    elif args.command == "execute":
        success = workflow.execute_approved_action(args.id)
        print(f"Executed: {success}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
