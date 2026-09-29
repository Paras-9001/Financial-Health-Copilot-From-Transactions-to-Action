"use client";

import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ForecastPoint, SpendingCategory } from "@/lib/types";

export function CashFlowChart({ points }: { points: ForecastPoint[] }) {
  const data = points.map((point) => ({ date: point.date.slice(5), balance: Number(point.projected_balance), lower: Number(point.lower_bound), range: Number(point.upper_bound) - Number(point.lower_bound) }));
  return <div className="chart" role="img" aria-label="Projected cash-flow balance with confidence band"><ResponsiveContainer width="100%" height={320}><AreaChart data={data} margin={{ top: 12, right: 12, left: 8, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" /><XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" /><YAxis tick={{ fontSize: 11 }} width={70} tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} /><Tooltip formatter={(value) => `₹${Number(value).toLocaleString("en-IN")}`} /><Area dataKey="lower" stackId="band" stroke="none" fill="transparent" /><Area dataKey="range" stackId="band" stroke="none" fill="#ddd6fe" fillOpacity={0.65} /><Area type="monotone" dataKey="balance" stroke="#7c3aed" fill="#ede9fe" strokeWidth={3} /></AreaChart></ResponsiveContainer></div>;
}

export function SpendingChart({ categories }: { categories: SpendingCategory[] }) {
  const data = categories.slice(0, 8).map((item) => ({ name: item.name, amount: Number(item.amount) }));
  return <div className="chart" role="img" aria-label="Spending by category bar chart"><ResponsiveContainer width="100%" height={320}><BarChart data={data} layout="vertical" margin={{ left: 22, right: 16 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e7e5e4" /><XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} /><YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={90} /><Tooltip formatter={(value) => `₹${Number(value).toLocaleString("en-IN")}`} /><Bar dataKey="amount" fill="#2563eb" radius={[0, 6, 6, 0]} /></BarChart></ResponsiveContainer></div>;
}
