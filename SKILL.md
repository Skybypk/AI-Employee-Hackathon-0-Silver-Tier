# AI Employee Skills - Silver Tier

## Overview
This document describes all the skills and capabilities of the Personal AI Employee Silver Tier implementation.

---

## Core Skills

### 1. Email Management (`gmail_watcher.py`)
**Purpose**: Monitor and process incoming Gmail messages automatically.

**Capabilities**:
- OAuth2 authenticated Gmail API integration
- Polling for new messages at configurable intervals
- Automatic categorization of emails
- Saving emails to vault in JSON format
- Extracting subject, sender, recipients, date, and body
- Handling attachments (metadata only in Silver Tier)

**Configuration**:
```bash
GMAIL_POLL_INTERVAL=60  # Seconds between checks
```

**Error Recovery**:
- Automatic re-authentication on token expiry
- Retry with exponential backoff on API failures
- Fallback to demo mode when credentials unavailable
- Network error handling with automatic reconnection

---

### 2. File System Monitoring (`filesystem_watcher.py`)
**Purpose**: Watch local directories for file changes and route them appropriately.

**Capabilities**:
- Real-time file system event monitoring using watchdog
- File creation, modification, move, and deletion detection
- Automatic file classification based on type:
  - Config files → Needs_Action
  - Log files → Logs
  - Data files (JSON, CSV, XML) → Inbox
  - Documents (PDF, DOC, XLS) → Inbox
  - Images → Done (archived)
- Event debouncing to prevent duplicate processing
- Detailed event logging

**Configuration**:
```bash
WATCHED_DIRS=/path/to/watch1,/path/to/watch2
```

**Error Recovery**:
- Automatic observer restart on failure
- Graceful degradation to demo mode without watchdog
- Error logging and continuation

---

### 3. Plan Generation (`claude_reasoning.py`)
**Purpose**: Analyze inbox items and generate actionable plans using AI reasoning.

**Capabilities**:
- Claude API integration for intelligent plan generation
- Rule-based fallback when API unavailable
- Automatic detection of items requiring planning
- Structured plan output with:
  - Summary
  - Prioritized action items
  - Effort estimates
  - Dependencies
  - Next steps
- Plan storage in Plans vault

**Configuration**:
```bash
ANTHROPIC_API_KEY=your_key_here
PLANNING_MODE=once|continuous
PLANNING_INTERVAL=300  # Seconds between runs (continuous mode)
```

**Error Recovery**:
- Automatic fallback to rule-based planning
- Error count tracking with recovery attempts
- Graceful degradation when API unavailable

---

### 4. Approval Workflow (`approval_workflow.py`)
**Purpose**: Manage human-in-the-loop approval process for actions.

**Capabilities**:
- Submit items for human approval
- Approve/reject pending items
- Track approval status and history
- Execute approved actions
- Maintain audit logs
- Statistics and reporting

**Commands**:
```bash
# List pending approvals
python approval_workflow.py list

# Approve an item
python approval_workflow.py approve APPROVAL_ID --notes "Optional notes"

# Reject an item
python approval_workflow.py reject APPROVAL_ID --reason "Rejection reason"

# Show statistics
python approval_workflow.py stats

# Execute approved action
python approval_workflow.py execute APPROVAL_ID
```

**Error Recovery**:
- Transactional file operations
- Error logging for failed operations
- Status tracking for recovery

---

### 5. Task Scheduling (`scheduler.py`)
**Purpose**: Run periodic tasks on a configurable schedule.

**Capabilities**:
- Configurable task intervals via environment variables
- Built-in tasks:
  - Gmail check (60s)
  - Filesystem check (30s)
  - Plan generation (300s)
  - Approval check (120s)
  - Log cleanup (3600s)
  - Health check (600s)
- Custom task registration
- Health monitoring and reporting
- Status persistence

**Commands**:
```bash
# Show scheduler status
python scheduler.py status

# Run a specific task
python scheduler.py run-task TASK_NAME

# Enable/disable tasks
python scheduler.py enable TASK_NAME
python scheduler.py disable TASK_NAME
```

**Configuration**:
```bash
SCHEDULER_INTERVAL_GMAIL_CHECK=60
SCHEDULER_INTERVAL_FILESYSTEM_CHECK=30
SCHEDULER_INTERVAL_GENERATE_PLANS=300
SCHEDULER_INTERVAL_APPROVAL_CHECK=120
SCHEDULER_INTERVAL_CLEANUP_LOGS=3600
SCHEDULER_INTERVAL_HEALTH_CHECK=600
```

**Error Recovery**:
- Error count tracking
- Automatic backoff on failures
- Continued operation despite individual task failures

---

### 6. Email MCP Server (`email-mcp/index.js`)
**Purpose**: Provide email sending capabilities via Model Context Protocol.

**Capabilities**:
- MCP-compliant tool interface
- Send email tool with full options:
  - To, CC, BCC recipients
  - Subject and body (text/HTML)
  - Attachments
- Connection testing tool
- SMTP configuration via environment variables
- Automatic logging of sent emails

**Tools**:
- `send_email`: Send an email message
- `test_connection`: Verify SMTP configuration

**Configuration**:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
SMTP_FROM=your_email@gmail.com
```

**Error Recovery**:
- Connection verification before sending
- Detailed error logging
- Graceful failure handling

---

## Vault Operations

### Vault Structure
```
AI_Employee_Vault/
├── Inbox/              # Incoming items awaiting processing
├── Needs_Action/       # Items requiring immediate attention
├── Done/               # Completed items (archive)
├── Logs/               # System logs and audit trails
├── Plans/              # Generated action plans
├── Pending_Approval/   # Items awaiting human approval
├── Approved/           # Approved items ready for execution
└── Rejected/           # Rejected items with reasons
```

### File Operations
All skills follow consistent file operation patterns:
- JSON files for structured data
- Markdown files for plans and documentation
- Timestamp-based naming for logs
- Atomic write operations where possible

---

## API Integration

### Next.js API Routes
The dashboard communicates with the vault through REST APIs:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vault/stats` | GET | Get item counts for all vaults |
| `/api/watchers/status` | GET | Get watcher service status |
| `/api/approvals/pending` | GET | List pending approvals |
| `/api/approvals/approve` | POST | Approve an item |
| `/api/approvals/reject` | POST | Reject an item |

---

## Error Handling Strategy

### General Principles
1. **Log Everything**: All errors are logged with context
2. **Continue Operating**: Individual failures don't stop the system
3. **Automatic Recovery**: Retry logic with backoff
4. **Graceful Degradation**: Fallback modes when services unavailable
5. **Human Notification**: Critical errors routed to Needs_Action

### Error Categories
- **Transient Errors**: Network issues, API rate limits → Retry
- **Configuration Errors**: Missing credentials → Demo mode
- **Data Errors**: Invalid input → Log and skip
- **System Errors**: Disk full, permissions → Alert and pause

### Recovery Mechanisms
- Exponential backoff for retries
- Circuit breaker pattern for external services
- Status file persistence for recovery after restart
- Health checks for self-monitoring

---

## Security Considerations

### Credential Management
- All secrets stored in environment variables
- OAuth2 tokens stored with restricted permissions
- Never log sensitive data

### Access Control
- Human approval required for sensitive operations
- Audit trail for all actions
- Read-only Gmail access by default

### Data Protection
- Local file storage only (no cloud sync in Silver Tier)
- Encrypted connections for API calls
- Regular log rotation and cleanup

---

## Performance Characteristics

### Expected Throughput
- Email processing: ~100 emails/minute
- File events: ~50 events/second
- Plan generation: ~10 plans/minute (API dependent)
- Approval workflow: Instant for file operations

### Resource Usage
- Memory: ~50-100MB base
- CPU: Minimal when idle, spikes during processing
- Disk: Depends on vault content, logs auto-cleaned

---

## Monitoring and Observability

### Status Files
Each skill maintains a status file in the Logs directory:
- `gmail_watcher_status.json`
- `filesystem_watcher_status.json`
- `planning_status.json`
- `scheduler_status.json`
- `health_check.json`

### Log Files
- `gmail_watcher.log`
- `filesystem_watcher.log`
- `claude_reasoning.log`
- `approval_workflow.log`
- `scheduler.log`
- `email_mcp.log`

### Dashboard Metrics
- Vault item counts (real-time)
- Watcher status indicators
- Pending approval count
- Last refresh timestamp

---

## Extensibility

### Adding New Skills
1. Create Python script in `scripts/` directory
2. Register with scheduler for periodic execution
3. Add status file reporting
4. Update Dashboard.md documentation

### Adding New Vaults
1. Create directory in `AI_Employee_Vault/`
2. Update vault counting in API route
3. Add to Dashboard UI if needed

### Adding New API Routes
1. Create route in `src/app/api/`
2. Follow existing patterns for error handling
3. Update dashboard components to use new API

---

## Version Information
- **Tier**: Silver
- **Version**: 1.0.0
- **Last Updated**: February 2026
