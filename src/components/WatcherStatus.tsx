import React from "react";

interface WatcherStatusProps {
  name: string;
  status: string;
  message: string;
  lastUpdate: string;
}

export default function WatcherStatus({ name, status, message, lastUpdate }: WatcherStatusProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "bg-green-500";
      case "stopped":
        return "bg-red-500";
      case "demo":
        return "bg-yellow-500";
      case "error":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
      case "stopped":
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
      case "demo":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
      case "error":
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
    }
  };

  return (
    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-medium text-gray-900 dark:text-white">{name}</h3>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${getStatusColor(status)}`}></div>
          <span className={`px-2 py-0.5 text-xs rounded-full ${getStatusBadge(status)}`}>
            {status || "unknown"}
          </span>
        </div>
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{message}</p>
      {lastUpdate && (
        <p className="text-xs text-gray-400 dark:text-gray-500">
          Last update: {new Date(lastUpdate).toLocaleString()}
        </p>
      )}
    </div>
  );
}
