#!/usr/bin/env python3
"""
Claude Reasoning Loop - Generates Plan.md files automatically using AI reasoning
Part of the Personal AI Employee Silver Tier implementation

This script analyzes items in the vault and generates actionable plans.
It can use Claude API or fall back to rule-based planning when API is unavailable.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
import re

# Try to import anthropic for Claude API
try:
    from anthropic import Anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    print("Warning: anthropic not installed, using rule-based planning")
    print("Install with: pip install anthropic")
    CLAUDE_AVAILABLE = False

# Configuration
VAULT_BASE = Path(__file__).parent / "AI_Employee_Vault"
INBOX_DIR = VAULT_BASE / "Inbox"
NEEDS_ACTION_DIR = VAULT_BASE / "Needs_Action"
PLANS_DIR = VAULT_BASE / "Logs"
LOGS_DIR = VAULT_BASE / "Logs"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "claude_reasoning.log" if LOGS_DIR.exists() else "claude_reasoning.log")
    ]
)
logger = logging.getLogger(__name__)


class PlanGenerator:
    """Generates actionable plans from vault items using AI reasoning."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        self.error_count = 0
        self.max_errors = 3
        
        if CLAUDE_AVAILABLE and self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
                logger.info("Claude client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Claude client: {e}")
                self.client = None
    
    def analyze_inbox(self) -> List[Dict[str, Any]]:
        """Analyze items in the inbox that need planning."""
        items = []
        
        try:
            if not INBOX_DIR.exists():
                logger.warning("Inbox directory does not exist")
                return items
            
            # Find JSON files (emails, data)
            for file_path in INBOX_DIR.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    items.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "type": "email" if "from" in data else "data",
                        "data": data,
                        "needs_plan": self._requires_planning(data)
                    })
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
            
            # Find markdown files
            for file_path in INBOX_DIR.glob("*.md"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    items.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "type": "document",
                        "data": {"content": content},
                        "needs_plan": self._requires_planning({"snippet": content, "body": content})
                    })
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
                    
        except Exception as e:
            logger.error(f"Error analyzing inbox: {e}")
        
        return [item for item in items if item.get("needs_plan")]
    
    def _requires_planning(self, data: Dict[str, Any]) -> bool:
        """Determine if an item requires planning."""
        # Check for action keywords
        action_keywords = [
            "action required", "please", "need to", "should", "must",
            "task", "deadline", "urgent", "priority", "review",
            "approve", "create", "update", "fix", "implement"
        ]
        
        text = ""
        if "subject" in data:
            text += data["subject"].lower() + " "
        if "snippet" in data:
            text += data["snippet"].lower() + " "
        if "body" in data:
            text += data["body"].lower() + " "
        if "content" in data:
            text += data["content"].lower() + " "
        
        # Check for action keywords
        for keyword in action_keywords:
            if keyword in text:
                return True
        
        # Check for questions
        if "?" in text:
            return True
        
        return False
    
    def generate_plan_claude(self, item: Dict[str, Any]) -> Optional[str]:
        """Generate a plan using Claude AI."""
        if not self.client:
            return None
        
        try:
            # Prepare context
            context = self._prepare_context(item)
            
            # Create prompt
            prompt = f"""You are an AI Employee assistant. Analyze the following item and create an actionable plan.

Item Type: {item['type']}
Item Name: {item['name']}

Content:
{context}

Create a detailed plan in Markdown format with:
1. Summary of what needs to be done
2. Specific action items with priorities (High/Medium/Low)
3. Estimated effort for each action
4. Any dependencies or prerequisites
5. Suggested next steps

Format the plan as follows:

# Plan: [Brief Title]

## Summary
[2-3 sentence summary]

## Action Items
| Priority | Action | Effort | Dependencies |
|----------|--------|--------|--------------|
| High | [action] | [time] | [deps] |

## Next Steps
1. [First step]
2. [Second step]
3. [Third step]

## Notes
[Any additional context or considerations]
"""
            
            # Call Claude API
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            plan_content = response.content[0].text
            logger.info("Plan generated using Claude")
            return plan_content
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            self.error_count += 1
            return None
    
    def generate_plan_rule_based(self, item: Dict[str, Any]) -> str:
        """Generate a plan using rule-based logic (fallback)."""
        try:
            # Extract key information
            subject = item["data"].get("subject", item["name"])
            snippet = item["data"].get("snippet", "")[:200]
            from_addr = item["data"].get("from", "Unknown")
            
            # Determine priority based on keywords
            priority = "Medium"
            text = (subject + " " + snippet).lower()
            if any(word in text for word in ["urgent", "asap", "immediately", "critical"]):
                priority = "High"
            elif any(word in text for word in ["when possible", "sometime", "low priority"]):
                priority = "Low"
            
            # Generate plan template
            plan = f"""# Plan: {subject}

## Summary
This item requires attention and action. Based on the content analysis, 
the following plan has been automatically generated.

**Source:** {item['name']}
**From:** {from_addr}
**Priority:** {priority}

## Action Items
| Priority | Action | Effort | Dependencies |
|----------|--------|--------|--------------|
| {priority} | Review and understand the request | 15 min | None |
| {priority} | Determine required response/action | 30 min | Understanding |
| Medium | Execute required actions | TBD | Analysis complete |
| Low | Document outcomes | 15 min | Actions complete |

## Next Steps
1. Review the original item in the Inbox
2. Determine the specific action required
3. If approval needed, move to Pending_Approval
4. Execute approved actions
5. Move completed items to Done

## Notes
- This plan was auto-generated using rule-based analysis
- Review and adjust priorities as needed
- Add specific details based on full content review

---
*Generated: {datetime.now().isoformat()}
*Generator: Rule-Based Plan Generator v1.0*
"""
            
            logger.info("Plan generated using rule-based logic")
            return plan
            
        except Exception as e:
            logger.error(f"Error generating rule-based plan: {e}")
            return self._generate_fallback_plan(item)
    
    def _generate_fallback_plan(self, item: Dict[str, Any]) -> str:
        """Generate a minimal fallback plan."""
        return f"""# Plan: Review {item['name']}

## Summary
This item requires manual review. Please examine the contents and determine appropriate actions.

## Action Items
| Priority | Action | Effort | Dependencies |
|----------|--------|--------|--------------|
| High | Manual review required | 30 min | None |

## Next Steps
1. Open the original file from Inbox
2. Review contents thoroughly
3. Determine required actions
4. Move to appropriate vault folder

---
*Generated: {datetime.now().isoformat()}
*Note: Auto-generation failed, manual review required*
"""
    
    def _prepare_context(self, item: Dict[str, Any]) -> str:
        """Prepare context string for Claude."""
        data = item["data"]
        context_parts = []
        
        if "subject" in data:
            context_parts.append(f"Subject: {data['subject']}")
        if "from" in data:
            context_parts.append(f"From: {data['from']}")
        if "to" in data:
            context_parts.append(f"To: {data['to']}")
        if "date" in data:
            context_parts.append(f"Date: {data['date']}")
        if "snippet" in data:
            context_parts.append(f"Snippet: {data['snippet'][:500]}")
        if "body" in data:
            context_parts.append(f"Body: {data['body'][:1000]}")
        if "content" in data:
            context_parts.append(f"Content: {data['content'][:1000]}")
        
        return "\n".join(context_parts) if context_parts else str(data)[:1000]
    
    def save_plan(self, plan_content: str, item: Dict[str, Any]) -> Path:
        """Save a generated plan to the Plans directory."""
        try:
            PLANS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r'[^\w\s-]', '', item['name'])[:30].strip()
            filename = f"Plan_{timestamp}_{safe_name}.md"
            
            filepath = PLANS_DIR / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(plan_content)
            
            logger.info(f"Plan saved to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving plan: {e}")
            # Fallback to logs directory
            try:
                LOGS_DIR.mkdir(parents=True, exist_ok=True)
                filepath = LOGS_DIR / f"plan_fallback_{int(time.time())}.md"
                with open(filepath, "w") as f:
                    f.write(plan_content)
                return filepath
            except:
                raise
    
    def process_inbox(self) -> int:
        """Process all items in inbox that need plans."""
        items = self.analyze_inbox()
        plans_generated = 0
        
        logger.info(f"Found {len(items)} items needing plans")
        
        for item in items:
            try:
                # Try Claude first, fallback to rule-based
                plan = None
                
                if self.client and self.error_count < self.max_errors:
                    plan = self.generate_plan_claude(item)
                
                if not plan:
                    plan = self.generate_plan_rule_based(item)
                
                # Save the plan
                if plan:
                    self.save_plan(plan, item)
                    plans_generated += 1
                    
            except Exception as e:
                logger.error(f"Error processing item {item['name']}: {e}")
                continue
        
        logger.info(f"Generated {plans_generated} plans")
        return plans_generated
    
    def run_once(self) -> Dict[str, Any]:
        """Run a single planning cycle."""
        start_time = time.time()
        
        try:
            plans_generated = self.process_inbox()
            duration = time.time() - start_time
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "plans_generated": plans_generated,
                "duration_seconds": round(duration, 2),
                "status": "success"
            }
            
            self._save_result(result)
            return result
            
        except Exception as e:
            logger.error(f"Planning cycle failed: {e}")
            result = {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
            self._save_result(result)
            return result
    
    def _save_result(self, result: Dict[str, Any]):
        """Save result to status file."""
        try:
            status_file = LOGS_DIR / "planning_status.json"
            
            # Load existing status
            existing = {}
            if status_file.exists():
                try:
                    with open(status_file, "r") as f:
                        existing = json.load(f)
                except:
                    pass
            
            # Update with new result
            existing["last_run"] = result
            existing["total_plans"] = existing.get("total_plans", 0) + result.get("plans_generated", 0)
            
            with open(status_file, "w") as f:
                json.dump(existing, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save result: {e}")


def main():
    """Entry point for Claude Reasoning Loop."""
    import signal
    
    # Get API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, using rule-based planning only")
    
    generator = PlanGenerator(api_key=api_key)
    
    # Handle shutdown signals
    running = True
    def signal_handler(sig, frame):
        nonlocal running
        logger.info("Received shutdown signal")
        running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run once or in loop based on environment
    run_mode = os.environ.get("PLANNING_MODE", "once")
    
    if run_mode == "once":
        # Single run
        result = generator.run_once()
        print(json.dumps(result, indent=2))
    else:
        # Continuous mode
        interval = int(os.environ.get("PLANNING_INTERVAL", "300"))
        logger.info(f"Running in continuous mode (interval: {interval}s)")
        
        while running:
            generator.run_once()
            
            # Sleep with interrupt check
            for _ in range(interval):
                if not running:
                    break
                time.sleep(1)


if __name__ == "__main__":
    main()
