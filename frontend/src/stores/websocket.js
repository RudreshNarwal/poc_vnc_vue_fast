import { defineStore } from 'pinia'

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    connections: new Map(),
    vncConnection: null
  }),
  
  actions: {
    connect(sessionId) {
      // Prevent duplicate connections
      if (this.connections.has(sessionId)) {
        return this.connections.get(sessionId)
      }
      
      const ws = new WebSocket(`/ws/${sessionId}`)
      this.connections.set(sessionId, ws)
      
      ws.onopen = () => {
        console.log(`WebSocket connected for session: ${sessionId}`)
      }
      
      ws.onclose = () => {
        console.log(`WebSocket disconnected for session: ${sessionId}`)
        this.connections.delete(sessionId)
      }
      
      ws.onerror = (error) => {
        console.error(`WebSocket error for session ${sessionId}:`, error)
      }
      
      return ws
    },
    
    disconnect(sessionId) {
      const ws = this.connections.get(sessionId)
      if (ws) {
        ws.close()
        this.connections.delete(sessionId)
      }
    },
    
    disconnectAll() {
      this.connections.forEach(ws => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close()
        }
      })
      this.connections.clear()
    },
    
    sendMessage(sessionId, message) {
      const ws = this.connections.get(sessionId)
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message))
      }
    },
    
    getConnectionStatus(sessionId) {
      const ws = this.connections.get(sessionId)
      if (!ws) return 'disconnected'
      
      switch (ws.readyState) {
        case WebSocket.CONNECTING:
          return 'connecting'
        case WebSocket.OPEN:
          return 'connected'
        case WebSocket.CLOSING:
          return 'closing'
        case WebSocket.CLOSED:
          return 'disconnected'
        default:
          return 'unknown'
      }
    }
  },
  
  getters: {
    isConnected: (state) => (sessionId) => {
      const ws = state.connections.get(sessionId)
      return ws && ws.readyState === WebSocket.OPEN
    },
    
    activeConnections: (state) => {
      return Array.from(state.connections.keys())
    }
  }
})
