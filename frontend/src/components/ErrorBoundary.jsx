import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({ errorInfo });

    // Auto-reload once if this is a stale chunk error (happens after new deployments)
    const isChunkError = (
      error?.name === 'ChunkLoadError' ||
      error?.message?.includes('Loading chunk') ||
      error?.message?.includes('Failed to fetch dynamically imported module') ||
      error?.message?.includes('Importing a module script failed') ||
      error?.message?.includes('error loading dynamically imported module')
    );
    if (isChunkError) {
      const reloadKey = 'chunk_reload_attempted';
      if (!sessionStorage.getItem(reloadKey)) {
        sessionStorage.setItem(reloadKey, '1');
        // Clear caches then reload
        if ('caches' in window) {
          caches.keys().then(names => names.forEach(name => caches.delete(name)));
        }
        window.location.reload(true);
      }
    }
  }

  handleReload = () => {
    sessionStorage.removeItem('chunk_reload_attempted');
    window.location.reload(true);
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'center',
          height: '100vh', 
          background: 'var(--bg-primary, #0a0a0f)', 
          color: 'var(--text-primary, #e5e5e5)',
          textAlign: 'center', 
          padding: 40
        }}>
          <AlertCircle size={64} style={{ marginBottom: 24, color: 'var(--color-error, #ef4444)' }} />
          <h1 style={{ fontSize: 32, fontWeight: 700, marginBottom: 16 }}>Something went wrong.</h1>
          <p style={{ fontSize: 16, opacity: 0.7, marginBottom: 12, maxWidth: 500 }}>
            This usually happens after a new update is deployed. Clearing your browser cache will fix it.
          </p>
          <p style={{ fontSize: 13, opacity: 0.5, marginBottom: 32, maxWidth: 500 }}>
            Error: {this.state.error?.message || 'Unknown error'}
          </p>
          
          <button 
            onClick={this.handleReload}
            style={{
              padding: '12px 32px', 
              background: 'var(--accent-primary, #7c3aed)',
              color: 'white', 
              borderRadius: 8, 
              border: 'none',
              cursor: 'pointer',
              display: 'flex', 
              alignItems: 'center', 
              gap: 8,
              fontSize: 16,
              fontWeight: 600
            }}
          >
            <RefreshCw size={18} />
            Clear Cache &amp; Reload
          </button>
          
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <div style={{
              marginTop: 40,
              padding: 20,
              background: 'rgba(239, 68, 68, 0.1)',
              borderRadius: 8,
              border: '1px solid rgba(239, 68, 68, 0.2)',
              textAlign: 'left',
              maxWidth: '80%',
              overflowX: 'auto'
            }}>
              <h3 style={{ color: '#ef4444', marginBottom: 8 }}>Developer Details:</h3>
              <pre style={{ fontSize: 12, opacity: 0.8 }}>
                {this.state.error.toString()}
                <br/>
                {this.state.errorInfo?.componentStack}
              </pre>
            </div>
          )}
        </div>
      );
    }

    return this.props.children; 
  }
}

export default ErrorBoundary;
