import { useState, useEffect, useRef } from "react";
import { Search, X } from "lucide-react";

interface AutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  suggestions: string[];
  placeholder?: string;
  label?: string;
  className?: string;
}

export default function Autocomplete({
  value,
  onChange,
  suggestions,
  placeholder = "Escribir para buscar...",
  label,
  className = "",
}: AutocompleteProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [filtered, setFiltered] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (value.trim() === "") {
      setFiltered(suggestions.slice(0, 10));
    } else {
      const lower = value.toLowerCase();
      const matches = suggestions.filter((s) => s.toLowerCase().includes(lower));
      setFiltered(matches.slice(0, 10));
    }
  }, [value, suggestions]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (item: string) => {
    onChange(item);
    setIsOpen(false);
  };

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      {label && <label className="block text-xs text-gray-400 mb-1.5">{label}</label>}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          className="w-full pl-8 pr-8 py-2 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none placeholder-gray-600"
        />
        {value && (
          <button
            onClick={() => { onChange(""); setIsOpen(false); }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
          >
            <X size={14} />
          </button>
        )}
      </div>
      {isOpen && filtered.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-dark-800 border border-dark-700/50 rounded-xl shadow-xl max-h-48 overflow-y-auto">
          {filtered.map((item) => (
            <button
              key={item}
              onClick={() => handleSelect(item)}
              className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-dark-700/50 hover:text-white transition-colors first:rounded-t-xl last:rounded-b-xl"
            >
              {item}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
