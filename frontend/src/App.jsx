import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { WebSocketProvider } from './context/WebSocketContext';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import { AlertCircle, Home } from 'lucide-react';

// Lazy-loaded pages — only loaded when navigated to (code splitting)
const Landing = lazy(() => import('./pages/Landing'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Documents = lazy(() => import('./pages/Documents'));
const Chat = lazy(() => import('./pages/Chat'));
const Meetings = lazy(() => import('./pages/Meetings'));
const Tasks = lazy(() => import('./pages/Tasks'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Settings = lazy(() => import('./pages/Settings'));
const Graph = lazy(() => import('./pages/Graph'));

// Loading fallback
function LoadingFallback() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', background: 'var(--bg-primary, #0a0a0f)'
    }}>
      <div className="spinner" />
    </div>
  );
}

// 404 Page
function NotFound() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      height: '100vh', background: 'var(--bg-primary, #0a0a0f)', color: 'var(--text-primary, #e5e5e5)',
      textAlign: 'center', padding: 40
    }}>
      <AlertCircle size={48} style={{ marginBottom: 16, opacity: 0.5 }} />
      <h1 style={{ fontSize: 48, fontWeight: 700, marginBottom: 8 }}>404</h1>
      <p style={{ fontSize: 16, opacity: 0.6, marginBottom: 24 }}>Page not found</p>
      <Link to="/" style={{
        padding: '10px 24px', background: 'var(--accent-primary, #7c3aed)',
        color: 'white', borderRadius: 8, textDecoration: 'none',
        display: 'flex', alignItems: 'center', gap: 8
      }}>
        <Home size={16} /> Back to Home
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <AuthProvider>
          <WebSocketProvider>
            <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/meetings" element={<Meetings />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/graph" element={<Graph />} />
            </Route>
            <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
          </WebSocketProvider>
        </AuthProvider>
      </ErrorBoundary>
    </BrowserRouter>
  );
}
