# Personal AI Employee - Silver Tier

A comprehensive AI-powered employee assistant with vault management, approval workflows, and automated task processing..

## 🎯 Overview

The Silver Tier implementation provides:

- **Email Monitoring**: Gmail integration with OAuth2 authentication
- **File System Watching**: Real-time monitoring of local directories
- **AI Plan Generation**: Claude-powered automatic plan creation
- **Human-in-the-Loop**: Approval workflow for sensitive actions
- **Dashboard UI**: Real-time status monitoring and approval interface
- **Task Scheduling**: Configurable cron-like job scheduler
- **Email MCP Server**: Model Context Protocol integration for email sending

## 📁 Project Structure

```
Silver/
├── src/
│   ├── app/
│   │   ├── api/              # Next.js API routes
│   │   │   ├── vault/        # Vault statistics
│   │   │   ├── watchers/     # Watcher status
│   │   │   └── approvals/    # Approval workflow
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── Dashboard.tsx     # Main dashboard
│   │   ├── VaultCard.tsx     # Vault status card
│   │   ├── WatcherStatus.tsx # Watcher status display
│   │   └── ApprovalWorkflow.tsx # Approval interface
│   └── lib/
├── scripts/
│   ├── gmail_watcher.py      # Gmail monitoring
│   ├── filesystem_watcher.py # File system monitoring
│   ├── claude_reasoning.py   # Plan generation
│   ├── approval_workflow.py  # Approval management
│   └── scheduler.py          # Task scheduler
├── email-mcp/
│   ├── index.js              # Email MCP server
│   └── package.json
├── AI_Employee_Vault/
│   ├── Inbox/
│   ├── Needs_Action/
│   ├── Done/
│   ├── Logs/
│   ├── Plans/
│   ├── Pending_Approval/
│   ├── Approved/
│   └── Rejected/
├── .env.example
├── package.json
├── README.md
└── SKILL.md
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.10+
- Git (optional)

### 1. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - Gmail OAuth2 credentials
# - Anthropic API key (optional)
# - SMTP settings
```

### 3. Set Up Gmail OAuth2 (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth2 credentials (Desktop app)
5. Download as `gmail_credentials.json`
6. Place in the `Silver/` directory

### 4. Run the Application

```bash
# Start the Next.js dashboard
npm run dev

# In separate terminals, start the watchers:
python scripts/gmail_watcher.py
python scripts/filesystem_watcher.py
python scripts/scheduler.py
```

Open [http://localhost:3000](http://localhost:3000) to see the dashboard.

## 📚 Documentation

- **[SKILL.md](./SKILL.md)**: Complete skill documentation
- **[AI_Employee_Vault/Dashboard.md](./AI_Employee_Vault/Dashboard.md)**: Dashboard overview
- **[AI_Employee_Vault/Company_Handbook.md](./AI_Employee_Vault/Company_Handbook.md)**: Operating guidelines
- **[AI_Employee_Vault/Business_Goals.md](./AI_Employee_Vault/Business_Goals.md)**: Goals and roadmap

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GMAIL_POLL_INTERVAL` | Gmail check interval (seconds) | `60` |
| `ANTHROPIC_API_KEY` | Claude API key | - |
| `PLANNING_MODE` | Plan generation mode | `continuous` |
| `SMTP_HOST` | SMTP server host | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username | - |
| `SMTP_PASS` | SMTP password | - |
| `WATCHED_DIRS` | Directories to monitor | `./watched` |

### Scheduler Intervals

Configure task intervals via environment variables:

```bash
SCHEDULER_INTERVAL_GMAIL_CHECK=60
SCHEDULER_INTERVAL_FILESYSTEM_CHECK=30
SCHEDULER_INTERVAL_GENERATE_PLANS=300
SCHEDULER_INTERVAL_APPROVAL_CHECK=120
```

## 🎨 Features

### Dashboard

- **Vault Status**: Real-time item counts for all vaults
- **Watcher Status**: Live status of Gmail and filesystem watchers
- **Approval Interface**: Review and approve/reject pending actions
- **Quick Actions**: One-click access to common tasks

### Approval Workflow

1. AI submits actions to `Pending_Approval`
2. Human reviews in dashboard or via CLI
3. Move to `Approved` or `Rejected`
4. Approved actions execute automatically

```bash
# CLI usage
python scripts/approval_workflow.py list
python scripts/approval_workflow.py approve APPROVAL_ID --notes "Looks good"
python scripts/approval_workflow.py reject APPROVAL_ID --reason "Not needed"
```

### Plan Generation

Automatic plan generation using Claude AI:

- Analyzes inbox items for action requirements
- Generates structured plans with priorities
- Stores plans in `Plans/` vault
- Falls back to rule-based planning when API unavailable

### Email MCP Server

Model Context Protocol server for email operations:

```bash
cd email-mcp
npm install
npm start
```

Available tools:
- `send_email`: Send emails with full options
- `test_connection`: Verify SMTP configuration

## 🛠️ Scripts

### Gmail Watcher

```bash
python scripts/gmail_watcher.py
```

Monitors Gmail inbox and saves new emails to vault.

### Filesystem Watcher

```bash
python scripts/filesystem_watcher.py
```

Watches directories for file changes and routes them appropriately.

### Claude Reasoning

```bash
# Single run
python scripts/claude_reasoning.py

# Continuous mode
PLANNING_MODE=continuous python scripts/claude_reasoning.py
```

Generates action plans from inbox items.

### Scheduler

```bash
# Run scheduler
python scripts/scheduler.py

# Check status
python scripts/scheduler.py status

# Run specific task
python scripts/scheduler.py run-task generate_plans
```

Runs periodic tasks on a schedule.

### Approval Workflow

```bash
# List pending
python scripts/approval_workflow.py list

# Show stats
python scripts/approval_workflow.py stats
```

Manages the approval process.

## 📊 Vault Structure

| Vault | Purpose |
|-------|---------|
| `Inbox` | Incoming items awaiting processing |
| `Needs_Action` | Items requiring immediate attention |
| `Done` | Completed items (archive) |
| `Logs` | System logs and audit trails |
| `Plans` | Generated action plans |
| `Pending_Approval` | Items awaiting human approval |
| `Approved` | Approved items ready for execution |
| `Rejected` | Rejected items with reasons |

## 🔒 Security

- **Credentials**: Store in environment variables, never commit
- **OAuth2**: Tokens stored with restricted permissions
- **Audit Trail**: All actions logged in `Logs/`
- **Access Control**: Human approval for sensitive operations

## 🐛 Error Handling

The system implements comprehensive error handling:

- **Automatic Recovery**: Retry with exponential backoff
- **Graceful Degradation**: Fallback modes when services unavailable
- **Error Logging**: All errors logged with context
- **Status Persistence**: Recovery after restart

## 📈 Monitoring

### Status Files

Check `AI_Employee_Vault/Logs/` for:
- `gmail_watcher_status.json`
- `filesystem_watcher_status.json`
- `planning_status.json`
- `scheduler_status.json`
- `health_check.json`

### Dashboard

Real-time monitoring at [http://localhost:3000](http://localhost:3000)

## 🔮 Roadmap

### Gold Tier (Next)
- [ ] Multi-channel communication (Slack, Teams)
- [ ] Advanced plan generation
- [ ] Predictive task suggestions
- [ ] Enhanced analytics
- [ ] Mobile notifications

### Platinum Tier
- [ ] Full autonomous operation
- [ ] Natural language commands
- [ ] Cross-platform sync
- [ ] ML-based prioritization
- [ ] Team collaboration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.

## 🆘 Support

For issues or questions:
1. Check the [SKILL.md](./SKILL.md) documentation
2. Review logs in `AI_Employee_Vault/Logs/`
3. Check the dashboard for status information

---

**Version**: 1.0.0 (Silver Tier)  
**Last Updated**: February 2026
