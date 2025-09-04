<!-- MultiSessionBrowserViewport.vue -->
<template>
  <div class="relative w-full h-full bg-black">
    <!-- Session Info Bar -->
    <div
      v-if="sessionInfo"
      class="absolute top-0 left-0 right-0 bg-gray-900/90 text-white p-2 flex justify-between items-center z-10"
    >
      <div class="flex items-center gap-4">
        <span class="text-sm">Session: {{ sessionInfo.session_id.substring(0, 8) }}</span>
        <span class="text-sm">Display: :{{ sessionInfo.display }}</span>
        <span class="text-sm">User: {{ sessionInfo.user_id }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span :class="statusClasses" class="px-2 py-1 rounded text-xs">
          {{ connectionStatus }}
        </span>
        <button @click="requestNewSession" class="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm">
          New Session
        </button>
      </div>
    </div>

    <!-- VNC Screen -->
    <div :id="`vnc-screen-${uniqueId}`" class="w-full h-full pt-10"></div>

    <!-- Loading State -->
    <div v-if="isConnecting" class="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center">
      <div class="text-white text-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
        <p>Requesting VNC session...</p>
        <p class="text-sm mt-2 text-gray-400">{{ connectionMessage }}</p>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="connectionError" class="absolute inset-0 bg-red-900/20 flex items-center justify-center">
      <div class="bg-white rounded-lg p-6 max-w-md">
        <h3 class="text-lg font-semibold text-red-600 mb-2">Connection Error</h3>
        <p class="text-gray-700 mb-4">{{ connectionError }}</p>
        <button @click="retry" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Retry
        </button>
      </div>
    </div>

    <!-- Session Queue Status -->
    <div v-if="queuePosition > 0" class="absolute bottom-4 left-4 bg-yellow-500/90 text-white px-3 py-2 rounded">
      Queue Position: {{ queuePosition }} / {{ totalInQueue }}
    </div>

    <!-- Resource Usage -->
    <div
      v-if="showResourceUsage && resourceStats"
      class="absolute bottom-4 right-4 bg-gray-900/90 text-white p-2 rounded text-xs"
    >
      <div>CPU: {{ resourceStats.cpu }}%</div>
      <div>Memory: {{ resourceStats.memory }}%</div>
      <div>Sessions: {{ resourceStats.active }}/{{ resourceStats.max }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import RFB from '@novnc/novnc/core/rfb'

const props = defineProps({
  userId: {
    type: String,
    required: true
  },
  taskId: {
    type: Number,
    default: null
  },
  isRunning: Boolean,
  showResourceUsage: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['session-created', 'session-destroyed', 'connection-changed'])

// Unique ID for this component instance
const uniqueId = ref((typeof crypto !== 'undefined' && crypto.randomUUID) ? crypto.randomUUID() : `id-${Date.now()}-${Math.random().toString(36).slice(2)}`)

// Connection state
const vnc = ref(null)
const sessionInfo = ref(null)
const connectionStatus = ref('disconnected')
const connectionMessage = ref('')
const isConnecting = ref(false)
const connectionError = ref('')

// Queue management
const queuePosition = ref(0)
const totalInQueue = ref(0)

// Resource stats
const resourceStats = ref(null)
const resourcePollInterval = ref(null)

// Session management API
class SessionManager {
  constructor(apiUrl = '/api/sessions') {
    this.apiUrl = apiUrl
    this.retryCount = 0
    this.maxRetries = 3
  }

  async createSession(userId, taskId = null) {
    const response = await fetch(`${this.apiUrl}/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        task_id: taskId,
        timeout_minutes: 30
      })
    })

    if (response.status === 503) {
      // Server is at capacity
      const data = await response.json()
      throw new Error(`Server at capacity: ${data.detail}`)
    }

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`)
    }

    return await response.json()
  }

  async destroySession(sessionId) {
    await fetch(`${this.apiUrl}/${sessionId}`, {
      method: 'DELETE'
    })
  }

  async getSessionInfo(sessionId) {
    const response = await fetch(`${this.apiUrl}/${sessionId}`)
    if (!response.ok) {
      throw new Error('Session not found')
    }
    return await response.json()
  }

  async getQueueStatus() {
    const response = await fetch(`${this.apiUrl}/queue/status`)
    return await response.json()
  }

  async getResourceStats() {
    const response = await fetch(`${this.apiUrl}/stats`)
    return await response.json()
  }
}

const sessionManager = new SessionManager()

/**
 * Interaction policy:
 * - While automation is running (props.isRunning = true) we set viewOnly=true to prevent interference.
 * - After Stop/completion (props.isRunning = false) we enable full mouse/keyboard control for manual use.
 */
const allowInput = computed(() => !props.isRunning)

// Computed
const statusClasses = computed(() => {
  const base = 'px-2 py-1 rounded text-xs font-medium'
  if (connectionStatus.value === 'connected') {
    return `${base} bg-green-500 text-white`
  } else if (connectionStatus.value === 'connecting') {
    return `${base} bg-yellow-500 text-white`
  } else {
    return `${base} bg-gray-500 text-white`
  }
})

// Methods
const requestNewSession = async () => {
  try {
    isConnecting.value = true
    connectionError.value = ''
    connectionMessage.value = 'Requesting session from server...'

    // Check if user already has a session
    const existingSession = localStorage.getItem(`vnc_session_${props.userId}`)
    if (existingSession) {
      try {
        const existing = JSON.parse(existingSession)
        const info = await sessionManager.getSessionInfo(existing.session_id)
        if (info && info.status === 'active') {
          sessionInfo.value = info
          await connectToVNC(info)
          return
        }
      } catch {
        // Existing session invalid, create new one
        localStorage.removeItem(`vnc_session_${props.userId}`)
      }
    }

    // Request new session
    connectionMessage.value = 'Allocating resources...'
    const session = await sessionManager.createSession(props.userId, props.taskId)
    
    sessionInfo.value = session
    localStorage.setItem(`vnc_session_${props.userId}`, JSON.stringify(session))
    
    emit('session-created', session)
    
    // Wait for VNC server to be ready
    connectionMessage.value = 'Starting VNC server...'
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    await connectToVNC(session)
    
  } catch (error) {
    console.error('Failed to create session:', error)
    connectionError.value = error.message
    
    if (error.message.includes('capacity')) {
      // Server at capacity, show queue position
      pollQueueStatus()
    }
  } finally {
    isConnecting.value = false
  }
}

const connectToVNC = async (session) => {
  try {
    connectionMessage.value = 'Connecting to display...'
    connectionStatus.value = 'connecting'
    
    const screen = document.getElementById(`vnc-screen-${uniqueId.value}`)
    if (!screen) return
    
    // Clean up existing connection
    if (vnc.value) {
      vnc.value.disconnect()
    }
    
    // Connect to the session's dedicated VNC port
    vnc.value = new RFB(screen, session.vnc_url || `ws://localhost:${session.web_port}/websockify`, {
      shared: true,
      // Input policy: disable input while automation runs; enable for manual control
      viewOnly: !allowInput.value,
      focusOnClick: true,
      // Make local clicks map correctly to remote by scaling instead of clipping
      scaleViewport: true,
      clipViewport: false,
      dragViewport: false,
      // Resize remote session to client size (helps full-window click mapping)
      resizeSession: true,
      credentials: {
        password: session.password || ''
      }
    })
    
    vnc.value.addEventListener('connect', () => {
      connectionStatus.value = 'connected'
      connectionMessage.value = ''
      emit('connection-changed', 'connected')
      // ensure interactive settings are applied post-connect
      try {
        vnc.value.scaleViewport = true
        vnc.value.clipViewport = false
        vnc.value.viewOnly = !allowInput.value
        vnc.value.focus()
        // focus canvas to receive inputs
        const canvas = screen.querySelector('canvas')
        if (canvas) {
          canvas.style.pointerEvents = 'auto'
          canvas.style.cursor = 'default'
          canvas.tabIndex = 0
          canvas.focus()
        }
      } catch (_) {}
      startResourcePolling()
    })
    
    vnc.value.addEventListener('disconnect', (event) => {
      connectionStatus.value = 'disconnected'
      emit('connection-changed', 'disconnected')
      
      if (!event.detail.clean) {
        // Unexpected disconnect, try to reconnect
        setTimeout(() => {
          if (sessionInfo.value) {
            connectToVNC(sessionInfo.value)
          }
        }, 3000)
      }
    })
    
    vnc.value.addEventListener('credentialsrequired', () => {
      // Handle password if needed
      vnc.value.sendCredentials({ password: session.password || '' })
    })
    
  } catch (error) {
    console.error('VNC connection error:', error)
    connectionStatus.value = 'error'
    connectionError.value = `Connection failed: ${error.message}`
  }
}

const pollQueueStatus = async () => {
  const pollInterval = setInterval(async () => {
    try {
      const status = await sessionManager.getQueueStatus()
      queuePosition.value = status.position
      totalInQueue.value = status.total
      
      if (status.position === 0) {
        clearInterval(pollInterval)
        requestNewSession() // Try again
      }
    } catch {
      clearInterval(pollInterval)
    }
  }, 5000)
}

const startResourcePolling = () => {
  if (!props.showResourceUsage) return
  
  resourcePollInterval.value = setInterval(async () => {
    try {
      const stats = await sessionManager.getResourceStats()
      resourceStats.value = {
        cpu: Math.round(stats.cpu_percent),
        memory: Math.round(stats.memory_percent),
        active: stats.active_sessions,
        max: stats.max_sessions
      }
    } catch (error) {
      console.error('Failed to fetch resource stats:', error)
    }
  }, 10000) // Poll every 10 seconds
}

const retry = () => {
  connectionError.value = ''
  requestNewSession()
}

const cleanup = async () => {
  // Stop resource polling
  if (resourcePollInterval.value) {
    clearInterval(resourcePollInterval.value)
  }
  
  // Disconnect VNC
  if (vnc.value) {
    vnc.value.disconnect()
    vnc.value = null
  }
  
  // Destroy session
  if (sessionInfo.value) {
    try {
      await sessionManager.destroySession(sessionInfo.value.session_id)
      emit('session-destroyed', sessionInfo.value.session_id)
    } catch (error) {
      console.error('Failed to destroy session:', error)
    }
    
    localStorage.removeItem(`vnc_session_${props.userId}`)
    sessionInfo.value = null
  }
}

/**
 * When automation running state changes, toggle viewOnly accordingly.
 * - true while running (prevent interference)
 * - false after stop/completion (manual control enabled)
 */
watch(() => props.isRunning, (running) => {
  if (vnc.value) {
    vnc.value.viewOnly = running ? true : false
  }
})

// Lifecycle
onMounted(() => {
  requestNewSession()
})

onUnmounted(() => {
  cleanup()
})

// Watch for task changes
watch(() => props.taskId, (newTaskId) => {
  if (newTaskId && sessionInfo.value) {
    // Recreate session for new task
    cleanup().then(() => {
      requestNewSession()
    })
  }
})

// Expose methods for parent component
defineExpose({
  requestNewSession,
  cleanup,
  getSessionInfo: () => sessionInfo.value
})
</script>

<style scoped>
/* Ensure VNC canvas fills container */
:deep(canvas) {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain;
  pointer-events: auto !important;
  cursor: default !important;
  user-select: none !important;
}
</style>
