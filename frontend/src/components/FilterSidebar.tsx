"use client";

import type { Department, ProductFilters } from "@/lib/types";

interface FilterSidebarProps {
  filters: ProductFilters;
  departments: Department[];
  onChange: (filters: ProductFilters) => void;
  onApply: () => void;
  onClear: () => void;
}

export default function FilterSidebar({
  filters,
  departments,
  onChange,
  onApply,
  onClear,
}: FilterSidebarProps) {
  const update = (key: keyof ProductFilters, value: string) => {
    onChange({ ...filters, [key]: value });
  };

  return (
    <aside className="w-full shrink-0 rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:w-64">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
          Filters
        </h2>
        <button
          type="button"
          onClick={onClear}
          className="text-xs font-medium text-violet-600 hover:text-violet-700"
        >
          Clear all
        </button>
      </div>

      <div className="space-y-4">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-600">Category</span>
          <select
            value={filters.department_final}
            onChange={(e) => update("department_final", e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-violet-500"
          >
            <option value="">All categories</option>
            {departments.map((d) => (
              <option key={d.department} value={d.department}>
                {d.department} ({d.count.toLocaleString()})
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-600">Brand</span>
          <input
            type="text"
            value={filters.brand}
            onChange={(e) => update("brand", e.target.value)}
            placeholder="e.g. Nike"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-violet-500"
          />
        </label>

        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-600">Min price (LKR)</span>
            <input
              type="number"
              min={0}
              value={filters.min_price}
              onChange={(e) => update("min_price", e.target.value)}
              placeholder="0"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-violet-500"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-600">Max price (LKR)</span>
            <input
              type="number"
              min={0}
              value={filters.max_price}
              onChange={(e) => update("max_price", e.target.value)}
              placeholder="50000"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-violet-500"
            />
          </label>
        </div>

        <button
          type="button"
          onClick={onApply}
          className="w-full rounded-md bg-violet-600 py-2.5 text-sm font-semibold text-white hover:bg-violet-700"
        >
          Apply filters
        </button>
      </div>
    </aside>
  );
}
