<template>
  <div class="relative w-full h-full bg-black">
    <div id="vnc-screen" class="w-full h-full"></div>

    <div v-if="connectionStatus"
         :class="statusClasses"
         class="absolute top-4 right-4 px-3 py-1 rounded text-sm">
      {{ connectionStatus }}
    </div>

    <div v-if="scriptCompleted"
         class="absolute top-4 left-4 bg-green-500 text-white px-3 py-1 rounded text-sm font-medium">
      ✓ Manual Control Active
    </div>

    <div v-if="isPaused"
         class="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2">
      <button @click="resume"
              class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
        Resume Automation
      </button>
    </div>

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
import { ref, onUnmounted, watch, computed } from 'vue'
import RFB from '@novnc/novnc/core/rfb'

const props = defineProps({
  sessionId: String,
  isRunning: Boolean
})

const emit = defineEmits(['resume'])

const vnc = ref(null)
const connectionStatus = ref('')
const isConnecting = ref(false)
const isPaused = ref(false)
const scriptCompleted = ref(false)

// Compute view-only: allow interaction when paused or after completion
const isViewOnly = computed(() => {
  return props.isRunning && !isPaused.value && !scriptCompleted.value
})

const statusClasses = computed(() => {
  const base = 'px-3 py-1 rounded text-sm font-medium'
  if (connectionStatus.value === 'Connected' || connectionStatus.value === 'Manual Control Active') {
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

    const response = await fetch('/api/vnc/config')
    const vncConfig = await response.json()
    const screen = document.getElementById('vnc-screen')
    if (!screen) return
    if (vnc.value) vnc.value.disconnect()

    vnc.value = new RFB(screen, vncConfig.url, {
      scaleViewport: true,
      viewOnly: isViewOnly.value
    })

    vnc.value.addEventListener('connect', () => {
      connectionStatus.value = 'Connected'
      isConnecting.value = false
      vnc.value.viewOnly = isViewOnly.value
      try { vnc.value.scaleViewport = true } catch {}
    })

    vnc.value.addEventListener('disconnect', () => {
      connectionStatus.value = 'Disconnected'
      isConnecting.value = false
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

const resume = () => {
  isPaused.value = false
  emit('resume')
}

watch(() => props.isRunning, (newVal) => {
  if (newVal) {
    scriptCompleted.value = false
    isPaused.value = false
    setTimeout(connectVNC, 1000)
  } else if (!scriptCompleted.value) {
    disconnectVNC()
  }
})

// apply viewOnly updates
watch(isViewOnly, (newVal) => {
  if (vnc.value) vnc.value.viewOnly = newVal
})

// Handle WebSocket messages
watch(() => props.sessionId, (newVal) => {
  if (newVal) {
    const ws = new WebSocket(`/ws/${newVal}`)
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'status') {
        switch (data.status) {
          case 'paused':
            isPaused.value = true
            break
          case 'completed':
            scriptCompleted.value = true
            isPaused.value = false
            connectionStatus.value = 'Manual Control Active'
            break
          case 'running':
            isPaused.value = false
            scriptCompleted.value = false
            break
          case 'stopped':
          case 'error':
            isPaused.value = false
            scriptCompleted.value = false
            break
        }
      }
    }
  }
})

onUnmounted(() => {
  disconnectVNC()
})
</script>
