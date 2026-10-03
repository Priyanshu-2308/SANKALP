"use client";

import { useEffect, useRef, useState } from "react";
import { searchPlaces } from "@/lib/api";
import { Place } from "@/lib/types";

interface StationAutocompleteProps {
  id: string;
  label: string;
  placeholder: string;
  value: Place | null;
  onSelect: (place: Place | null) => void;
  required?: boolean;
}

export default function StationAutocomplete({
  id,
  label,
  placeholder,
  value,
  onSelect,
  required = false,
}: StationAutocompleteProps) {
  const [query, setQuery] = useState(value ? `${value.name} (${value.code})` : "");
  const [results, setResults] = useState<Place[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const wrapperRef = useRef<HTMLDivElement>(null);

  // Sync external value changes
  useEffect(() => {
    if (value) {
      setQuery(`${value.name} (${value.code})`);
    } else {
      setQuery("");
    }
  }, [value]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounced search
  useEffect(() => {
    if (!isOpen || query.trim().length === 0) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const resp = await searchPlaces(query.trim(), 8);
        setResults(resp.results);
      } catch (err) {
        console.error("Autocomplete search error:", err);
      } finally {
        setIsLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query, isOpen]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVal = e.target.value;
    setQuery(newVal);
    onSelect(null);
    setIsOpen(true);
    setHighlightedIndex(-1);
  };

  const handleSelectPlace = (place: Place) => {
    onSelect(place);
    setQuery(`${place.name} (${place.code})`);
    setIsOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || results.length === 0) {
      if (e.key === "ArrowDown") {
        setIsOpen(true);
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (highlightedIndex >= 0 && highlightedIndex < results.length) {
        handleSelectPlace(results[highlightedIndex]);
      }
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  const getNodeTypeBadge = (type: string) => {
    switch (type) {
      case "AIRPORT":
        return { label: "Flight", color: "bg-blue-50 text-blue-700 border-blue-200" };
      case "BUS_TERMINAL":
        return { label: "Bus", color: "bg-amber-50 text-amber-700 border-amber-200" };
      default:
        return { label: "Rail", color: "bg-emerald-50 text-emerald-700 border-emerald-200" };
    }
  };

  return (
    <div ref={wrapperRef} className="relative flex flex-col gap-1 w-full">
      <label htmlFor={id} className="text-xs font-medium text-ink-secondary">
        {label}
      </label>

      <div className="relative">
        <input
          id={id}
          type="text"
          value={query}
          onChange={handleInputChange}
          onFocus={() => {
            setIsOpen(true);
            if (query.trim().length === 0) {
              searchPlaces("", 6).then((res) => setResults(res.results));
            }
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          required={required}
          autoComplete="off"
          className="w-full bg-surface-container-lowest border border-ink-border rounded-lg px-3 py-2.5 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none focus:border-ink-primary transition-colors"
        />

        {value && (
          <button
            type="button"
            onClick={() => {
              onSelect(null);
              setQuery("");
            }}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-ink-muted hover:text-ink-primary p-1"
            title="Clear selection"
          >
            ✕
          </button>
        )}
      </div>

      {isOpen && (results.length > 0 || isLoading) && (
        <ul className="absolute top-full left-0 right-0 z-50 mt-1 max-h-64 overflow-y-auto bg-surface-container-lowest border border-ink-border rounded-lg shadow-sm py-1">
          {isLoading && (
            <li className="px-3 py-2 text-xs text-ink-muted italic">Searching transit nodes...</li>
          )}
          {results.map((place, idx) => {
            const badge = getNodeTypeBadge(place.place_type);
            const isHighlighted = idx === highlightedIndex;

            return (
              <li
                key={place.id}
                onMouseEnter={() => setHighlightedIndex(idx)}
                onClick={() => handleSelectPlace(place)}
                className={`px-3 py-2 cursor-pointer transition-colors flex items-center justify-between text-xs ${
                  isHighlighted ? "bg-surface-container" : "hover:bg-surface-container-low"
                }`}
              >
                <div className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-1.5 font-medium text-ink-primary">
                    <span>{place.name}</span>
                    <span className="text-[11px] text-ink-muted">({place.code})</span>
                  </div>
                  <div className="text-[11px] text-ink-secondary">
                    {place.city}, {place.state}
                  </div>
                </div>
                <span className={`px-1.5 py-0.5 rounded border text-[10px] font-medium ${badge.color}`}>
                  {badge.label}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
