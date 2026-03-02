import React from "react";

interface VaultCardProps {
  name: string;
  count: number;
  color: "blue" | "yellow" | "red" | "green" | "gray" | "orange" | "purple" | "indigo";
  description: string;
}

const colorClasses = {
  blue: "bg-blue-500",
  yellow: "bg-yellow-500",
  red: "bg-red-500",
  green: "bg-green-500",
  gray: "bg-gray-500",
  orange: "bg-orange-500",
  purple: "bg-purple-500",
  indigo: "bg-indigo-500",
};

const lightColorClasses = {
  blue: "bg-blue-100 dark:bg-blue-900",
  yellow: "bg-yellow-100 dark:bg-yellow-900",
  red: "bg-red-100 dark:bg-red-900",
  green: "bg-green-100 dark:bg-green-900",
  gray: "bg-gray-100 dark:bg-gray-900",
  orange: "bg-orange-100 dark:bg-orange-900",
  purple: "bg-purple-100 dark:bg-purple-900",
  indigo: "bg-indigo-100 dark:bg-indigo-900",
};

export default function VaultCard({ name, count, color, description }: VaultCardProps) {
  return (
    <div className={`p-4 rounded-lg shadow ${lightColorClasses[color]} transition hover:shadow-md`}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">{name}</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>
        </div>
        <div className={`w-3 h-3 rounded-full ${colorClasses[color]}`}></div>
      </div>
      <div className="mt-2">
        <span className="text-3xl font-bold text-gray-900 dark:text-white">{count}</span>
        <span className="text-sm text-gray-500 dark:text-gray-400 ml-1">items</span>
      </div>
    </div>
  );
}
