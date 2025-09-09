import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { 
  Menu, X, Bot, MessageSquare, Settings, Users, BarChart3, 
  LogOut, Moon, Sun, ChevronLeft, Home, Plus
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { SessionList } from '@/features/chat/SessionList';

interface NavItem {
  icon: React.ElementType;
  label: string;
  path: string;
  adminOnly?: boolean;
}

const navItems: NavItem[] = [
  { icon: Home, label: 'Dashboard', path: '/dashboard' },
  { icon: MessageSquare, label: 'Chat', path: '/chat' },
  { icon: Bot, label: 'Bots', path: '/bots' },
  { icon: BarChart3, label: 'Analytics', path: '/analytics', adminOnly: true },
  { icon: Users, label: 'Users', path: '/users', adminOnly: true },
  { icon: Settings, label: 'Settings', path: '/settings' },
];

export const AppLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [chatSidebarOpen, setChatSidebarOpen] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle('dark');
  };

  const isOnChatPage = location.pathname.startsWith('/chat');

  return (
    <div className="h-screen flex bg-background">
      {/* Mobile Overlay */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      {/* Main Sidebar */}
      <aside
        className={cn(
          'fixed lg:static inset-y-0 left-0 z-50 flex flex-col bg-card border-r border-border transition-all duration-300',
          sidebarOpen ? 'w-64' : 'w-16',
          mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-border">
          <div className={cn('flex items-center gap-2', !sidebarOpen && 'lg:justify-center')}>
            <Bot className="w-8 h-8 text-primary" />
            {sidebarOpen && (
              <span className="font-bold text-lg">DCRI GPT</span>
            )}
          </div>
          
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="hidden lg:block p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
          >
            <ChevronLeft className={cn('w-5 h-5 transition-transform', !sidebarOpen && 'rotate-180')} />
          </button>
          
          <button
            onClick={() => setMobileSidebarOpen(false)}
            className="lg:hidden p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            if (item.adminOnly && !user?.is_admin) return null;
            
            const isActive = location.pathname.startsWith(item.path);
            const Icon = item.icon;
            
            return (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  setMobileSidebarOpen(false);
                }}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                  isActive 
                    ? 'bg-primary text-primary-foreground' 
                    : 'hover:bg-gray-100 dark:hover:bg-gray-800',
                  !sidebarOpen && 'lg:justify-center'
                )}
                title={!sidebarOpen ? item.label : undefined}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {sidebarOpen && <span>{item.label}</span>}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border space-y-2">
          {/* Theme Toggle */}
          <button
            onClick={toggleDarkMode}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800',
              !sidebarOpen && 'lg:justify-center'
            )}
            title={!sidebarOpen ? 'Toggle theme' : undefined}
          >
            {darkMode ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            {sidebarOpen && <span>{darkMode ? 'Dark Mode' : 'Light Mode'}</span>}
          </button>

          {/* User Info & Logout */}
          {sidebarOpen ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-medium">
                  {user?.full_name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user?.full_name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={handleLogout}
              className="w-full flex justify-center p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          )}
        </div>
      </aside>

      {/* Chat Sessions Sidebar (only on chat page) */}
      {isOnChatPage && (
        <aside
          className={cn(
            'w-64 bg-gray-50 dark:bg-gray-900 border-r border-border transition-all duration-300',
            chatSidebarOpen ? 'translate-x-0' : '-translate-x-full hidden'
          )}
        >
          <div className="h-16 flex items-center justify-between px-4 border-b border-border">
            <h2 className="font-semibold">Chat Sessions</h2>
            <button
              onClick={() => setChatSidebarOpen(!chatSidebarOpen)}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          </div>
          <SessionList />
        </aside>
      )}

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        {/* Top Bar */}
        <header className="h-16 flex items-center justify-between px-4 bg-card border-b border-border">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="lg:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            >
              <Menu className="w-5 h-5" />
            </button>
            
            {isOnChatPage && !chatSidebarOpen && (
              <button
                onClick={() => setChatSidebarOpen(true)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
              >
                <MessageSquare className="w-5 h-5" />
              </button>
            )}
            
            <h1 className="text-lg font-semibold">
              {navItems.find(item => location.pathname.startsWith(item.path))?.label || 'Dashboard'}
            </h1>
          </div>

          {isOnChatPage && (
            <Button variant="outline" size="sm">
              <Plus className="w-4 h-4 mr-2" />
              New Bot
            </Button>
          )}
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-hidden">
          <Outlet />
        </div>
      </main>
    </div>
  );
};