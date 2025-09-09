import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

import { AppLayout } from '@/components/layout/AppLayout';
import { ProtectedRoute } from '@/components/common/ProtectedRoute';
import { AuthForm } from '@/features/auth/AuthForm';
import { ChatPage } from '@/pages/ChatPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { useAuthStore } from '@/stores/authStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  const { fetchUser } = useAuthStore();

  useEffect(() => {
    // Try to fetch user on app load if token exists
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchUser();
    }
  }, [fetchUser]);

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<AuthForm />} />
          
          {/* Protected Routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="bots" element={<BotsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="users" element={<UsersPage />} />
          </Route>
          
          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>
      
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#333',
            color: '#fff',
          },
        }}
      />
      
    </QueryClientProvider>
  );
}

// Placeholder components (to be implemented)
const BotsPage = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold">Bots Management</h1>
    <p className="text-muted-foreground mt-2">Create and manage your AI bots here.</p>
  </div>
);

const SettingsPage = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold">Settings</h1>
    <p className="text-muted-foreground mt-2">Manage your account and preferences.</p>
  </div>
);

const AnalyticsPage = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold">Analytics</h1>
    <p className="text-muted-foreground mt-2">View platform usage and statistics.</p>
  </div>
);

const UsersPage = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold">User Management</h1>
    <p className="text-muted-foreground mt-2">Manage platform users and permissions.</p>
  </div>
);

export default App;
