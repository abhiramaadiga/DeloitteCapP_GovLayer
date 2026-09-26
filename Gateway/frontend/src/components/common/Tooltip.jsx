import React, { useState, useRef } from 'react';

/**
 * Tooltip Component
 * Provides clean, elegant pop-up hover effects across buttons, status badges, and KPI ribbons.
 */
export default function Tooltip({
  content,
  children,
  position = 'top',
  delay = 100,
  className = '',
}) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef(null);

  const show = () => {
    timeoutRef.current = setTimeout(() => setVisible(true), delay);
  };

  const hide = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(false);
  };

  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  return (
    <div
      className={`relative inline-flex ${className}`}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {visible && content && (
        <div
          role="tooltip"
          className={`absolute z-50 px-2.5 py-1.5 text-[11px] font-mono leading-tight text-zinc-200 bg-zinc-900 border border-zinc-700/80 rounded-lg shadow-xl shadow-black/60 whitespace-nowrap pointer-events-none popup-scale ${positionClasses[position]}`}
        >
          {content}
          {/* Subtle triangle arrow */}
          <div
            className={`absolute w-1.5 h-1.5 bg-zinc-900 border-zinc-700/80 rotate-45 ${
              position === 'top'
                ? 'top-full left-1/2 -translate-x-1/2 -translate-y-1/2 border-r border-b'
                : position === 'bottom'
                ? 'bottom-full left-1/2 -translate-x-1/2 translate-y-1/2 border-l border-t'
                : position === 'left'
                ? 'left-full top-1/2 -translate-y-1/2 -translate-x-1/2 border-t border-r'
                : 'right-full top-1/2 -translate-y-1/2 translate-x-1/2 border-b border-l'
            }`}
          />
        </div>
      )}
    </div>
  );
}
