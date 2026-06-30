import React, { createContext, useContext, useEffect, useState } from 'react';
import { useAuth } from './AuthContext';

const WebSocketContext = createContext(null);

export const useWebSocket = () => useContext(WebSocketContext);

export const WebSocketProvider = ({ children }) => {
  const { user } = useAuth();
  const [socket, setSocket] = useState(null);
  const [lastMessage, setLastMessage] = useState(null);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (!user) {
      if (socket) {
        socket.close();
        setSocket(null);
      }
      return;
    }

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    // Convert http/https to ws/wss
    const wsUrl = API_URL.replace(/^http/, 'ws') + `/ws/${user.id}`;
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket Connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);
        
        if (data.type === 'task_update') {
          showToast(`Task Update: ${data.message}`);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket Disconnected');
    };

    setSocket(ws);

    return () => {
      ws.close();
    };
  }, [user]);

  const showToast = (message) => {
    setToast(message);
    setTimeout(() => {
      setToast(null);
    }, 5000);
  };

  return (
    <WebSocketContext.Provider value={{ socket, lastMessage }}>
      {children}
      {toast && (
        <div style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          background: 'var(--color-blue)',
          color: 'white',
          padding: '12px 24px',
          borderRadius: 8,
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          zIndex: 9999,
          animation: 'slideIn 0.3s ease-out'
        }}>
          {toast}
        </div>
      )}
    </WebSocketContext.Provider>
  );
};
