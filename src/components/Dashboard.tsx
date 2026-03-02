"use client";

import { useState, useEffect } from "react";
import VaultCard from "./VaultCard";
import ApprovalWorkflow from "./ApprovalWorkflow";
import WatcherStatus from "./WatcherStatus";

// Types
interface VaultStats {
  Inbox: number;
  Needs_Action: number;
  Done: number;
  Logs: number;
  Plans: number;
  Pending_Approval: number;
  Approved: number;
  Rejected: number;
}

interface WatcherStatus {
  gmail: {
    status: string;
    message: string;
    last_update: string;
  };
  filesystem: {
    status: string;
    message: string;
    last_update: string;
  };
}

export default function Dashboard() {
  const [vaultStats, setVaultStats] = useState<VaultStats>({
    Inbox: 0,
    Needs_Action: 0,
    Done: 0,
    Logs: 0,
    Plans: 0,
    Pending_Approval: 0,
    Approved: 0,
    Rejected: 0,
  });

  const [watcherStatus, setWatcherStatus] = useState<WatcherStatus>({
    gmail: { status: "unknown", message: "Loading...", last_update: "" },
    filesystem: { status: "unknown", message: "Loading...", last_update: "" },
  });

  const [activeTab, setActiveTab] = useState<"dashboard" | "approvals">("dashboard");
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Fetch vault stats
  const fetchVaultStats = async () => {
    try {
      const response = await fetch("/api/vault/stats");
      if (response.ok) {
        const data = await response.json();
        setVaultStats(data);
      }
    } catch (error) {
      console.error("Failed to fetch vault stats:", error);
    }
  };

  // Fetch watcher status
  const fetchWatcherStatus = async () => {
    try {
      const response = await fetch("/api/watchers/status");
      if (response.ok) {
        const data = await response.json();
        setWatcherStatus(data);
      }
    } catch (error) {
      console.error("Failed to fetch watcher status:", error);
    }
  };

  // Initial fetch and polling
  useEffect(() => {
    fetchVaultStats();
    fetchWatcherStatus();

    const interval = setInterval(() => {
      fetchVaultStats();
      fetchWatcherStatus();
      setLastRefresh(new Date());
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    fetchVaultStats();
    fetchWatcherStatus();
    setLastRefresh(new Date());
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Personal AI Employee
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Silver Tier Dashboard
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Last refresh: {lastRefresh.toLocaleTimeString()}
              </span>
              <button
                onClick={handleRefresh}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="mt-4 flex space-x-4">
            <button
              onClick={() => setActiveTab("dashboard")}
              className={`px-4 py-2 rounded-t-lg font-medium transition ${
                activeTab === "dashboard"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab("approvals")}
              className={`px-4 py-2 rounded-t-lg font-medium transition ${
                activeTab === "approvals"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
              }`}
            >
              Approvals
              {vaultStats.Pending_Approval > 0 && (
                <span className="ml-2 px-2 py-0.5 text-xs bg-red-500 text-white rounded-full">
                  {vaultStats.Pending_Approval}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === "dashboard" ? (
          <div className="space-y-8">
            {/* Vault Status Grid */}
            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Vault Status
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <VaultCard
                  name="Inbox"
                  count={vaultStats.Inbox}
                  color="blue"
                  description="Incoming items"
                />
                <VaultCard
                  name="Needs Action"
                  count={vaultStats.Needs_Action}
                  color="yellow"
                  description="Requires attention"
                />
                <VaultCard
                  name="Pending Approval"
                  count={vaultStats.Pending_Approval}
                  color="red"
                  description="Awaiting review"
                />
                <VaultCard
                  name="Approved"
                  count={vaultStats.Approved}
                  color="green"
                  description="Ready for execution"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
                <VaultCard
                  name="Done"
                  count={vaultStats.Done}
                  color="gray"
                  description="Completed items"
                />
                <VaultCard
                  name="Rejected"
                  count={vaultStats.Rejected}
                  color="orange"
                  description="Declined items"
                />
                <VaultCard
                  name="Plans"
                  count={vaultStats.Plans}
                  color="purple"
                  description="Generated plans"
                />
                <VaultCard
                  name="Logs"
                  count={vaultStats.Logs}
                  color="indigo"
                  description="System logs"
                />
              </div>
            </section>

            {/* Watcher Status */}
            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Watcher Status
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <WatcherStatus
                  name="Gmail Watcher"
                  status={watcherStatus.gmail.status}
                  message={watcherStatus.gmail.message}
                  lastUpdate={watcherStatus.gmail.last_update}
                />
                <WatcherStatus
                  name="Filesystem Watcher"
                  status={watcherStatus.filesystem.status}
                  message={watcherStatus.filesystem.message}
                  lastUpdate={watcherStatus.filesystem.last_update}
                />
              </div>
            </section>

            {/* Quick Actions */}
            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Quick Actions
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <QuickActionCard
                  title="Review Pending"
                  description="Check items awaiting approval"
                  onClick={() => setActiveTab("approvals")}
                  icon="📋"
                />
                <QuickActionCard
                  title="Generate Plans"
                  description="Create action plans for inbox items"
                  onClick={() => console.log("Generate plans")}
                  icon="📝"
                />
                <QuickActionCard
                  title="View Logs"
                  description="Check system logs"
                  onClick={() => console.log("View logs")}
                  icon="📊"
                />
                <QuickActionCard
                  title="Run Diagnostics"
                  description="Check system health"
                  onClick={() => console.log("Run diagnostics")}
                  icon="🔧"
                />
              </div>
            </section>
          </div>
        ) : (
          <ApprovalWorkflow />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-gray-500 dark:text-gray-400">
            Personal AI Employee - Silver Tier | All systems operational
          </p>
        </div>
      </footer>
    </div>
  );
}

// Quick Action Card Component
function QuickActionCard({
  title,
  description,
  onClick,
  icon,
}: {
  title: string;
  description: string;
  onClick: () => void;
  icon: string;
}) {
  return (
    <button
      onClick={onClick}
      className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition text-left"
    >
      <div className="text-2xl mb-2">{icon}</div>
      <h3 className="font-medium text-gray-900 dark:text-white">{title}</h3>
      <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
    </button>
  );
}
