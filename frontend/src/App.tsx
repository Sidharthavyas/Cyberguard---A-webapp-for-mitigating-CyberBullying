/**
 * Main App component with routing and protected routes.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import LoginPage from './pages/LoginPage';
import CallbackPage from './pages/CallbackPage';
import ServerSelectionPage from './pages/ServerSelectionPage';
import Dashboard from './pages/Dashboard';

// Protected route wrapper - checks for any platform's auth token
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const hasToken = localStorage.getItem('twitter_access_token') || localStorage.getItem('discord_access_token');

  if (!hasToken) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/callback" element={<CallbackPage />} />
          <Route path="/server-selection" element={<ServerSelectionPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
