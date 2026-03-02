import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";

const VAULT_BASE = process.env.VAULT_BASE_PATH || join(process.cwd(), "..", "AI_Employee_Vault");
const LOGS_DIR = join(VAULT_BASE, "Logs");

async function readStatusFile(filename: string): Promise<{ status: string; message: string; last_update: string }> {
  try {
    const filepath = join(LOGS_DIR, filename);
    const content = await readFile(filepath, "utf-8");
    const data = JSON.parse(content);
    return {
      status: data.status || "unknown",
      message: data.message || "No status available",
      last_update: data.timestamp || data.last_update || "",
    };
  } catch {
    return {
      status: "unknown",
      message: "Status not available",
      last_update: "",
    };
  }
}

export async function GET() {
  try {
    const [gmail, filesystem] = await Promise.all([
      readStatusFile("gmail_watcher_status.json"),
      readStatusFile("filesystem_watcher_status.json"),
    ]);

    return NextResponse.json({ gmail, filesystem });
  } catch (error) {
    console.error("Error fetching watcher status:", error);
    return NextResponse.json(
      {
        gmail: { status: "unknown", message: "Error reading status", last_update: "" },
        filesystem: { status: "unknown", message: "Error reading status", last_update: "" },
      },
      { status: 200 }
    );
  }
}
