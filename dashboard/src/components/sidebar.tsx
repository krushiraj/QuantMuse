'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Briefcase,
  History,
  Bell,
  TrendingUp,
  Globe,
} from 'lucide-react';

const navItems = [
  { href: '/', label: 'Portfolio', icon: LayoutDashboard },
  { href: '/positions', label: 'Positions', icon: Briefcase },
  { href: '/trades', label: 'Trades', icon: History },
  { href: '/signals', label: 'Signals', icon: Bell },
  { href: '/performance', label: 'Performance', icon: TrendingUp },
  { href: '/markets', label: 'Markets', icon: Globe },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r bg-card h-screen sticky top-0">
      <div className="p-6">
        <h1 className="text-xl font-bold">Paper Trading</h1>
        <p className="text-sm text-muted-foreground">QuantMuse Dashboard</p>
      </div>
      <nav className="px-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
