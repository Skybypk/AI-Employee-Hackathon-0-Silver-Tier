"use client";

import { useState, useEffect } from "react";

interface ApprovalItem {
  id: string;
  submitted_at: string;
  status: string;
  item: {
    action_required: string;
    priority: string;
    metadata: Record<string, any>;
  };
  notes?: string;
  rejection_reason?: string;
}

export default function ApprovalWorkflow() {
  const [pendingItems, setPendingItems] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [rejectionReason, setRejectionReason] = useState<Record<string, string>>({});
  const [showRejectModal, setShowRejectModal] = useState<string | null>(null);

  const fetchPendingItems = async () => {
    try {
      const response = await fetch("/api/approvals/pending");
      if (response.ok) {
        const data = await response.json();
        setPendingItems(data);
      }
    } catch (error) {
      console.error("Failed to fetch pending items:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPendingItems();
  }, []);

  const handleApprove = async (id: string) => {
    setActionLoading(id);
    try {
      const response = await fetch("/api/approvals/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, notes: notes[id] || "" }),
      });

      if (response.ok) {
        setPendingItems((items) => items.filter((item) => item.id !== id));
        setNotes((prev) => {
          const next = { ...prev };
          delete next[id];
          return next;
        });
      }
    } catch (error) {
      console.error("Failed to approve:", error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (id: string) => {
    setActionLoading(id);
    try {
      const response = await fetch("/api/approvals/reject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, reason: rejectionReason[id] || "No reason provided" }),
      });

      if (response.ok) {
        setPendingItems((items) => items.filter((item) => item.id !== id));
        setShowRejectModal(null);
        setRejectionReason((prev) => {
          const next = { ...prev };
          delete next[id];
          return next;
        });
      }
    } catch (error) {
      console.error("Failed to reject:", error);
    } finally {
      setActionLoading(null);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-200";
      case "medium":
        return "text-yellow-600 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-200";
      case "low":
        return "text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-200";
      default:
        return "text-gray-600 bg-gray-100 dark:bg-gray-900 dark:text-gray-200";
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="text-gray-500 dark:text-gray-400">Loading pending items...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Pending Approvals
        </h2>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {pendingItems.length} item(s) awaiting review
        </span>
      </div>

      {pendingItems.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="text-4xl mb-4">✅</div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            All Caught Up!
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            No pending approvals at this time
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {pendingItems.map((item) => (
            <div
              key={item.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-6"
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-white">
                    {item.id}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    Submitted: {new Date(item.submitted_at).toLocaleString()}
                  </p>
                </div>
                <span
                  className={`px-2 py-1 text-xs rounded-full ${getPriorityColor(
                    item.item?.priority || "medium"
                  )}`}
                >
                  {item.item?.priority || "medium"} priority
                </span>
              </div>

              <div className="mb-4">
                <p className="text-gray-700 dark:text-gray-300">
                  {item.item?.action_required || "Review and take action"}
                </p>
              </div>

              {/* Notes input */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Approval Notes (optional)
                </label>
                <textarea
                  value={notes[item.id] || ""}
                  onChange={(e) =>
                    setNotes((prev) => ({ ...prev, [item.id]: e.target.value }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  rows={2}
                  placeholder="Add any notes for this approval..."
                />
              </div>

              {/* Action buttons */}
              <div className="flex space-x-3">
                <button
                  onClick={() => handleApprove(item.id)}
                  disabled={actionLoading === item.id}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  {actionLoading === item.id ? "Processing..." : "Approve"}
                </button>
                <button
                  onClick={() => setShowRejectModal(item.id)}
                  disabled={actionLoading === item.id}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  {actionLoading === item.id ? "Processing..." : "Reject"}
                </button>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(item.item, null, 2));
                  }}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition"
                >
                  View Details
                </button>
              </div>

              {/* Rejection reason modal */}
              {showRejectModal === item.id && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                      Reject Approval
                    </h3>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Rejection Reason
                    </label>
                    <textarea
                      value={rejectionReason[item.id] || ""}
                      onChange={(e) =>
                        setRejectionReason((prev) => ({
                          ...prev,
                          [item.id]: e.target.value,
                        }))
                      }
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm mb-4"
                      rows={4}
                      placeholder="Please provide a reason for rejection..."
                    />
                    <div className="flex space-x-3">
                      <button
                        onClick={() => handleReject(item.id)}
                        className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition"
                      >
                        Confirm Rejection
                      </button>
                      <button
                        onClick={() => {
                          setShowRejectModal(null);
                          setRejectionReason((prev) => {
                            const next = { ...prev };
                            delete next[item.id];
                            return next;
                          });
                        }}
                        className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
