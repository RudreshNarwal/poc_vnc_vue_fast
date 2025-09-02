<template>
  <div class="relative w-full h-full bg-black">
    <!-- VNC Screen -->
    <div id="vnc-screen" class="w-full h-full"></div>
    
    <!-- Connection Status -->
    <div v-if="connectionStatus" 
         :class="statusClasses"
         class="absolute top-4 right-4 px-3 py-1 rounded text-sm">
      {{ connectionStatus }}
    </div>
    
    <!-- Interactive Controls -->
    <div v-if="isPaused" 
         class="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2">
      <button @click="resume" 
              class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
        Resume Automation
      </button>
    </div>
    
    <!-- Loading Overlay -->
    <div v-if="isConnecting" 
         class="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center">
      <div class="text-white text-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
        <p>Connecting to browser...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import RFB from '@novnc/novnc/core/rfb'

const props = defineProps({
  sessionId: String,
  isRunning: Boolean
})

const emit = defineEmits(['pause', 'resume'])

const vnc = ref(null)
const connectionStatus = ref('')
const isConnecting = ref(false)
const isPaused = ref(false)
const vncConfig = ref(null)

const statusClasses = computed(() => {
  const base = 'px-3 py-1 rounded text-sm font-medium'
  if (connectionStatus.value === 'Connected') {
    return `${base} bg-green-500 text-white`
  } else if (connectionStatus.value === 'Connecting...') {
    return `${base} bg-yellow-500 text-white`
  } else {
    return `${base} bg-red-500 text-white`
  }
})

const connectVNC = async () => {
  try {
    isConnecting.value = true
    connectionStatus.value = 'Connecting...'
    
    // Get VNC config from backend
    const response = await fetch('/api/vnc/config')
    vncConfig.value = await response.json()
    
    const screen = document.getElementById('vnc-screen')
    if (!screen) return
    
    // Clear previous connection
    if (vnc.value) {
      vnc.value.disconnect()
    }
    
    // Create new RFB connection - NO PASSWORD
    vnc.value = new RFB(
      screen, 
      vncConfig.value.url,
      {
        scaleViewport: true,
        resizeSession: false,
        showDotCursor: true,
        viewOnly: !isPaused.value,
        clipViewport: false,
        dragViewport: false,
        focusOnClick: true,
        background: 'rgb(0, 0, 0)'
      }
    )
    
    // Event handlers
    vnc.value.addEventListener('connect', () => {
      connectionStatus.value = 'Connected'
      isConnecting.value = false
      console.log('VNC connected successfully')
    })
    
    vnc.value.addEventListener('disconnect', (e) => {
      connectionStatus.value = 'Disconnected'
      isConnecting.value = false
      console.log('VNC disconnected:', e.detail)
    })
    
    vnc.value.addEventListener('credentialsrequired', () => {
      // No credentials needed - passwordless setup
      console.log('VNC: No credentials required')
    })
    
  } catch (error) {
    console.error('VNC connection error:', error)
    connectionStatus.value = 'Connection failed'
    isConnecting.value = false
  }
}

const disconnectVNC = () => {
  if (vnc.value) {
    vnc.value.disconnect()
    vnc.value = null
  }
}

const pause = () => {
  isPaused.value = true
  if (vnc.value) {
    vnc.value.viewOnly = false  // Enable interaction
  }
  emit('pause')
}

const resume = () => {
  isPaused.value = false
  if (vnc.value) {
    vnc.value.viewOnly = true  // Disable interaction
  }
  emit('resume')
}

// Auto-connect when running
watch(() => props.isRunning, (newVal) => {
  if (newVal) {
    setTimeout(connectVNC, 1000)  // Give browser time to start
  } else {
    disconnectVNC()
  }
})

// Handle WebSocket messages for pause state
watch(() => props.sessionId, (newVal) => {
  if (newVal) {
    const ws = new WebSocket(`/ws/${newVal}`)
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.status === 'paused') {
        isPaused.value = true
        if (vnc.value) vnc.value.viewOnly = false
      } else if (data.status === 'running') {
        isPaused.value = false
        if (vnc.value) vnc.value.viewOnly = true
      }
    }
  }
})

onUnmounted(() => {
  disconnectVNC()
})
</script>
