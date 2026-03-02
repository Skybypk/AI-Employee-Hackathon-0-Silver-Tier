import { NextResponse } from "next/server";
import { readdir, readFile } from "fs/promises";
import { join } from "path";

const VAULT_BASE = process.env.VAULT_BASE_PATH || join(process.cwd(), "..", "AI_Employee_Vault");
const PENDING_DIR = join(VAULT_BASE, "Pending_Approval");

export async function GET() {
  try {
    const files = await readdir(PENDING_DIR);
    const jsonFiles = files.filter((f) => f.endsWith(".json"));

    const items = await Promise.all(
      jsonFiles.map(async (file) => {
        try {
          const content = await readFile(join(PENDING_DIR, file), "utf-8");
          return JSON.parse(content);
        } catch {
          return null;
        }
      })
    );

    const validItems = items.filter((item) => item !== null);
    return NextResponse.json(validItems);
  } catch (error) {
    console.error("Error fetching pending approvals:", error);
    return NextResponse.json([], { status: 200 });
  }
}
