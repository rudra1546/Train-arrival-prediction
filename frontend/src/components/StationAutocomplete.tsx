import React, { useState, useEffect, useRef } from 'react';
import { MapPin, X, ChevronDown, Check } from 'lucide-react';
import { searchStations, getStationByCode } from '../services/routeSearch';
import type { StationMeta } from '../types/route';

interface StationAutocompleteProps {
  id: string;
  label: string;
  value: string;
  onChange: (stationCode: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export const StationAutocomplete: React.FC<StationAutocompleteProps> = ({
  id,
  label,
  value,
  onChange,
  placeholder = 'Station code or city name...',
  disabled = false
}) => {
  const [inputValue, setInputValue] = useState('');
  const [suggestions, setSuggestions] = useState<StationMeta[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Sync display text when value prop changes
  useEffect(() => {
    if (!value) {
      setInputValue('');
      return;
    }
    // Attempt to lookup full station name
    getStationByCode(value).then((match) => {
      if (match) {
        setInputValue(`${match.code} - ${match.name}`);
      } else {
        setInputValue(value.toUpperCase());
      }
    });
  }, [value]);

  // Query suggestions when input changes
  const handleInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const text = e.target.value;
    setInputValue(text);

    if (!text.trim()) {
      onChange('');
      setSuggestions([]);
      setIsOpen(false);
      return;
    }

    setIsLoading(true);
    try {
      const results = await searchStations(text, 7);
      setSuggestions(results);
      setIsOpen(results.length > 0);
    } catch {
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectStation = (station: StationMeta) => {
    onChange(station.code);
    setInputValue(`${station.code} - ${station.name}`);
    setIsOpen(false);
  };

  const handleClear = () => {
    onChange('');
    setInputValue('');
    setSuggestions([]);
    setIsOpen(false);
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="station-autocomplete-group" ref={containerRef}>
      <label htmlFor={id} className="autocomplete-field-label">
        <MapPin size={14} className="label-pin-icon" aria-hidden="true" />
        <span>{label}</span>
      </label>

      <div className="autocomplete-input-wrapper">
        <input
          id={id}
          type="text"
          className="autocomplete-input"
          value={inputValue}
          onChange={handleInputChange}
          onFocus={() => {
            if (suggestions.length > 0) setIsOpen(true);
          }}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
        />

        {inputValue ? (
          <button
            type="button"
            className="autocomplete-clear-btn"
            onClick={handleClear}
            aria-label={`Clear ${label}`}
            disabled={disabled}
          >
            <X size={15} />
          </button>
        ) : (
          <span className="autocomplete-chevron" aria-hidden="true">
            <ChevronDown size={15} />
          </span>
        )}

        {/* Dropdown Menu */}
        {isOpen && (
          <ul className="autocomplete-dropdown" role="listbox">
            {isLoading ? (
              <li className="dropdown-loading-item">Searching stations...</li>
            ) : suggestions.length === 0 ? (
              <li className="dropdown-empty-item">No stations found matching &ldquo;{inputValue}&rdquo;</li>
            ) : (
              suggestions.map((st) => {
                const isSelected = value.toUpperCase() === st.code;
                return (
                  <li
                    key={st.code}
                    className={`dropdown-suggestion-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleSelectStation(st)}
                    role="option"
                    aria-selected={isSelected}
                  >
                    <div className="suggestion-main-col">
                      <span className="station-code-tag">{st.code}</span>
                      <span className="station-name-text">{st.name}</span>
                    </div>
                    {st.zone && <span className="station-zone-badge">{st.zone}</span>}
                    {isSelected && <Check size={14} className="selected-check-icon" />}
                  </li>
                );
              })
            )}
          </ul>
        )}
      </div>
    </div>
  );
};
