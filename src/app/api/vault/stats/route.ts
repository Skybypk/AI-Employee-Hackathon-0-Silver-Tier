import { NextResponse } from "next/server";
import { readdir } from "fs/promises";
import { join } from "path";

// Vault base path - adjust based on environment
const VAULT_BASE = process.env.VAULT_BASE_PATH || join(process.cwd(), "..", "AI_Employee_Vault");

async function countFiles(dir: string): Promise<number> {
  try {
    const files = await readdir(dir);
    return files.filter((f) => !f.startsWith(".")).length;
  } catch {
    return 0;
  }
}

export async function GET() {
  try {
    const [
      Inbox,
      Needs_Action,
      Done,
      Logs,
      Plans,
      Pending_Approval,
      Approved,
      Rejected,
    ] = await Promise.all([
      countFiles(join(VAULT_BASE, "Inbox")),
      countFiles(join(VAULT_BASE, "Needs_Action")),
      countFiles(join(VAULT_BASE, "Done")),
      countFiles(join(VAULT_BASE, "Logs")),
      countFiles(join(VAULT_BASE, "Plans")),
      countFiles(join(VAULT_BASE, "Pending_Approval")),
      countFiles(join(VAULT_BASE, "Approved")),
      countFiles(join(VAULT_BASE, "Rejected")),
    ]);

    return NextResponse.json({
      Inbox,
      Needs_Action,
      Done,
      Logs,
      Plans,
      Pending_Approval,
      Approved,
      Rejected,
    });
  } catch (error) {
    console.error("Error fetching vault stats:", error);
    return NextResponse.json(
      {
        Inbox: 0,
        Needs_Action: 0,
        Done: 0,
        Logs: 0,
        Plans: 0,
        Pending_Approval: 0,
        Approved: 0,
        Rejected: 0,
      },
      { status: 200 }
    );
  }
}
