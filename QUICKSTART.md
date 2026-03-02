# Quick Start Guide - Personal AI Employee Silver Tier

## Start the Dashboard (Next.js)

```bash
cd Silver
npm run dev
```

The dashboard will be available at http://localhost:3000

## Start the Python Services (in separate terminals)

### Terminal 2 - Gmail Watcher
```bash
cd Silver
python scripts/gmail_watcher.py
```

### Terminal 3 - Filesystem Watcher
```bash
cd Silver
python scripts/filesystem_watcher.py
```

### Terminal 4 - Scheduler (runs periodic tasks)
```bash
cd Silver
python scripts/scheduler.py
```

## Optional: Install Python Dependencies

```bash
cd Silver
pip install -r requirements.txt
```

## Optional: Configure Environment

```bash
cd Silver
cp .env.example .env
# Edit .env with your credentials
```

## Verify Everything is Running

1. Open http://localhost:3000
2. Check that all vault counts show "0 items"
3. Check that watcher status shows "running" or "demo mode"

## CLI Commands

### Approval Workflow
```bash
# List pending approvals
python scripts/approval_workflow.py list

# Show statistics
python scripts/approval_workflow.py stats
```

### Scheduler
```bash
# Show scheduler status
python scripts/scheduler.py status

# Run a specific task
python scripts/scheduler.py run-task generate_plans
```

## Troubleshooting

### Build Errors
If you get build errors, try:
```bash
npm run build
```

### Python Import Errors
Install required dependencies:
```bash
pip install -r requirements.txt
```

### Port Already in Use
If port 3000 is in use, set a different port:
```bash
PORT=3001 npm run dev
```
