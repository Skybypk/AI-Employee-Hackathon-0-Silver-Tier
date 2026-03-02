import { NextResponse } from "next/server";
import { readFile, writeFile, unlink, mkdir } from "fs/promises";
import { join } from "path";
import { existsSync } from "fs";

const VAULT_BASE = process.env.VAULT_BASE_PATH || join(process.cwd(), "..", "AI_Employee_Vault");
const PENDING_DIR = join(VAULT_BASE, "Pending_Approval");
const APPROVED_DIR = join(VAULT_BASE, "Approved");
const LOGS_DIR = join(VAULT_BASE, "Logs");

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { id, notes } = body;

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
    approval.status = "approved";
    approval.approved_at = new Date().toISOString();
    approval.notes = notes || "";

    // Ensure approved directory exists
    if (!existsSync(APPROVED_DIR)) {
      await mkdir(APPROVED_DIR, { recursive: true });
    }

    // Write to approved directory
    const approvedFile = join(APPROVED_DIR, `${id}.json`);
    await writeFile(approvedFile, JSON.stringify(approval, null, 2));

    // Remove from pending
    await unlink(pendingFile);

    // Log the action
    const logFile = join(LOGS_DIR, `approval_${id}_approved.json`);
    await writeFile(
      logFile,
      JSON.stringify(
        {
          action: "approved",
          timestamp: new Date().toISOString(),
          approval_id: id,
          notes,
        },
        null,
        2
      )
    );

    return NextResponse.json({ success: true, message: "Approval granted" });
  } catch (error) {
    console.error("Error approving item:", error);
    return NextResponse.json({ error: "Failed to approve item" }, { status: 500 });
  }
}
