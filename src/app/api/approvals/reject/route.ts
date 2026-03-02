import { NextResponse } from "next/server";
import { readFile, writeFile, unlink, mkdir } from "fs/promises";
import { join } from "path";
import { existsSync } from "fs";

const VAULT_BASE = process.env.VAULT_BASE_PATH || join(process.cwd(), "..", "AI_Employee_Vault");
const PENDING_DIR = join(VAULT_BASE, "Pending_Approval");
const REJECTED_DIR = join(VAULT_BASE, "Rejected");
const LOGS_DIR = join(VAULT_BASE, "Logs");

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { id, reason } = body;

    if (!id) {
      return NextResponse.json({ error: "Approval ID is required" }, { status: 400 });
    }

    const pendingFile = join(PENDING_DIR, `${id}.json`);

    if (!existsSync(pendingFile)) {
      return NextResponse.json({ error: "Approval not found" }, { status: 404 });
    }

    // Read the pending approval
    const content = await readFile(pendingFile, "utf-8");
    const approval = JSON.parse(content);

    // Update status
    approval.status = "rejected";
    approval.rejected_at = new Date().toISOString();
    approval.rejection_reason = reason || "No reason provided";

    // Ensure rejected directory exists
    if (!existsSync(REJECTED_DIR)) {
      await mkdir(REJECTED_DIR, { recursive: true });
    }

    // Write to rejected directory
    const rejectedFile = join(REJECTED_DIR, `${id}.json`);
    await writeFile(rejectedFile, JSON.stringify(approval, null, 2));

    // Remove from pending
    await unlink(pendingFile);

    // Log the action
    const logFile = join(LOGS_DIR, `approval_${id}_rejected.json`);
    await writeFile(
      logFile,
      JSON.stringify(
        {
          action: "rejected",
          timestamp: new Date().toISOString(),
          approval_id: id,
          reason,
        },
        null,
        2
      )
    );

    return NextResponse.json({ success: true, message: "Approval rejected" });
  } catch (error) {
    console.error("Error rejecting item:", error);
    return NextResponse.json({ error: "Failed to reject item" }, { status: 500 });
  }
}
