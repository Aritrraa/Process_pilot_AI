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
    // You can also log the error to an error reporting service here
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
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
          <p style={{ fontSize: 16, opacity: 0.7, marginBottom: 32, maxWidth: 500 }}>
            An unexpected error occurred in the application interface. Our team has been notified.
          </p>
          
          <button 
            onClick={this.handleReload}
            style={{
              padding: '12px 24px', 
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
            Reload Application
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
