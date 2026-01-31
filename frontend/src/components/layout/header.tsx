'use client';

import { useEffect, useState } from 'react';
import { Bell, Search, Moon, Sun, User } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Header() {
  const [isDark, setIsDark] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    // Check system preference on mount
    const darkModePreference = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme === 'dark' || (!savedTheme && darkModePreference)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggleDarkMode = () => {
    setIsDark(!isDark);
    if (isDark) {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    } else {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    }
  };

  return (
    <header className="h-16 border-b border-border bg-card px-6 flex items-center justify-between">
      {/* Search */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search conversations, agents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              'w-full pl-10 pr-4 py-2 rounded-lg text-sm',
              'bg-background border border-input',
              'placeholder:text-muted-foreground',
              'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
              'transition-colors'
            )}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        {/* Notifications */}
        <button
          className={cn(
            'relative p-2 rounded-lg transition-colors',
            'text-muted-foreground hover:text-foreground hover:bg-accent'
          )}
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        {/* Theme Toggle */}
        <button
          onClick={toggleDarkMode}
          className={cn(
            'p-2 rounded-lg transition-colors',
            'text-muted-foreground hover:text-foreground hover:bg-accent'
          )}
        >
          {isDark ? (
            <Sun className="w-5 h-5" />
          ) : (
            <Moon className="w-5 h-5" />
          )}
        </button>

        {/* User Menu */}
        <button
          className={cn(
            'flex items-center gap-2 p-2 rounded-lg transition-colors',
            'text-muted-foreground hover:text-foreground hover:bg-accent'
          )}
        >
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
            <User className="w-4 h-4 text-primary" />
          </div>
        </button>
      </div>
    </header>
  );
}
