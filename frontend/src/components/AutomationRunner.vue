<template>
  <div class="px-4 py-6 sm:px-0">
    <!-- Header -->
    <div class="mb-6">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-2xl font-semibold text-gray-900">
            {{ task?.name || 'Automation Runner' }}
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            {{ task?.description || 'Execute browser automation tasks' }}
          </p>
        </div>
        <!-- Control Buttons -->
        <div class="flex space-x-3">
          <button
            v-if="!isRunning && !sessionId"
            @click="startAutomation"
            :disabled="!task"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
          >
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h1m4 0h1m6-10V4a2 2 0 00-2-2H5a2 2 0 00-2 2v16l4-2 4 2 4-2 4 2V4z" />
            </svg>
            Start Automation
          </button>
          <button
            v-if="isRunning && !isPaused"
            @click="pauseAutomation"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-amber-500 hover:bg-amber-600"
          >
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6" />
            </svg>
            Pause
          </button>
          <button
            v-if="isRunning && isPaused"
            @click="resumeAutomation"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h1m4 0h1" />
            </svg>
            Resume
          </button>
          <button
            v-if="isRunning"
            @click="stopAutomation"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
          >
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10h6v4H9z" />
            </svg>
            Stop
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Browser Viewport -->
      <div class="lg:col-span-2">
        <div class="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div class="px-4 py-3 border-b border-gray-200">
            <h3 class="text-lg font-medium text-gray-900">Browser Viewport</h3>
            <p class="text-sm text-gray-600">Live view of automation execution</p>
          </div>
          <div class="p-0 h-96 lg:h-[600px] bg-black">
            <BrowserViewport :session-id="sessionId" :is-running="isRunning" @pause="onPause" @resume="onResume" />
          </div>
        </div>
      </div>

      <!-- Control Panel -->
      <div class="space-y-6">
        <!-- Status Panel -->
        <div class="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Status</h3>
          <div class="space-y-3">
            <div class="flex justify-between">
              <span class="text-sm text-gray-600">Status:</span>
              <span :class="getStatusColor(status)" class="inline-flex rounded-full px-2 py-0.5 text-xs font-semibold">
                {{ status }}
              </span>
            </div>
            <div v-if="currentStep > 0" class="flex justify-between">
              <span class="text-sm text-gray-600">Progress:</span>
              <span class="text-sm text-gray-900">{{ currentStep }} / {{ totalSteps }}</span>
            </div>
            <div v-if="currentStep > 0" class="w-full bg-gray-100 rounded-full h-2">
              <div class="bg-blue-600 h-2 rounded-full transition-all duration-300" :style="{ width: `${(currentStep / totalSteps) * 100}%` }"></div>
            </div>
            <div v-if="currentMessage" class="text-sm text-gray-700">
              {{ currentMessage }}
            </div>
          </div>
        </div>

        <!-- Task Steps -->
        <div v-if="task" class="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Steps</h3>
          <div class="space-y-2 max-h-64 overflow-y-auto">
            <div
              v-for="(step, index) in task.steps"
              :key="index"
              class="flex items-center p-2 rounded"
              :class="{
                'bg-blue-600 text-white': index + 1 === currentStep && isRunning,
                'bg-emerald-600 text-white': index + 1 < currentStep,
                'bg-gray-100 text-gray-900': index + 1 > currentStep
              }"
            >
              <div class="flex-shrink-0 w-6 h-6 mr-3">
                <div v-if="index + 1 < currentStep" class="w-6 h-6 bg-emerald-500 rounded-full flex items-center justify-center">
                  <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div v-else-if="index + 1 === currentStep && isRunning" class="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                  <div class="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                </div>
                <div v-else class="w-6 h-6 bg-gray-300 rounded-full flex items-center justify-center text-xs text-gray-900">
                  {{ index + 1 }}
                </div>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium" :class="index + 1 > currentStep ? 'text-gray-900' : 'text-white'">
                  {{ step.action }}
                </p>
                <p v-if="step.description" class="text-xs" :class="index + 1 > currentStep ? 'text-gray-600' : 'text-white/80'">
                  {{ step.description }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Screenshots -->
        <div v-if="screenshots.length > 0" class="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Screenshots</h3>
          <div class="space-y-2 max-h-48 overflow-y-auto">
            <div v-for="(screenshot, index) in screenshots" :key="index" class="flex items-center p-2 bg-gray-50 rounded border border-gray-200">
              <img :src="screenshot" :alt="`Step ${index + 1} screenshot`" class="w-12 h-8 object-cover rounded mr-3" />
              <span class="text-sm text-gray-900">Step {{ index + 1 }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import BrowserViewport from './BrowserViewport.vue'
import { useWebSocketStore } from '../stores/websocket.js'

const route = useRoute()
const props = defineProps({
  taskId: String
})

const wsStore = useWebSocketStore()

// Reactive state
const task = ref(null)
const sessionId = ref(null)
const isRunning = ref(false)
const isPaused = ref(false)
const status = ref('idle')
const currentStep = ref(0)
const totalSteps = ref(0)
const currentMessage = ref('')
const screenshots = ref([])

// Load task data
const loadTask = async () => {
  try {
    const taskIdToLoad = props.taskId || route.params.taskId
    if (!taskIdToLoad) return
    const response = await axios.get(`/api/tasks/${taskIdToLoad}`)
    task.value = response.data
    totalSteps.value = response.data.steps.length
  } catch (error) {
    console.error('Failed to load task:', error)
  }
}

// Start automation
const startAutomation = async () => {
  try {
    const taskIdToRun = props.taskId || route.params.taskId
    if (!taskIdToRun) return
    const response = await axios.post(`/api/automation/execute/${taskIdToRun}`)
    sessionId.value = response.data.session_id
    isRunning.value = true
    status.value = 'starting'
    currentMessage.value = 'Starting automation...'
    connectWebSocket()
  } catch (error) {
    console.error('Failed to start automation:', error)
    alert('Failed to start automation')
  }
}

// Pause automation
const pauseAutomation = async () => {
  try {
    if (!sessionId.value) return
    await axios.post(`/api/automation/pause/${sessionId.value}`)
    isPaused.value = true
  } catch (error) {
    console.error('Failed to pause automation:', error)
  }
}

// Resume automation
const resumeAutomation = async () => {
  try {
    if (!sessionId.value) return
    await axios.post(`/api/automation/resume/${sessionId.value}`)
    isPaused.value = false
  } catch (error) {
    console.error('Failed to resume automation:', error)
  }
}

// Stop automation
const stopAutomation = async () => {
  try {
    if (!sessionId.value) return
    await axios.post(`/api/automation/stop/${sessionId.value}`)
    isRunning.value = false
    isPaused.value = false
    status.value = 'stopped'
    currentMessage.value = 'Automation stopped'
    if (sessionId.value) wsStore.disconnect(sessionId.value)
  } catch (error) {
    console.error('Failed to stop automation:', error)
  }
}

// Connect WebSocket for real-time updates
const connectWebSocket = () => {
  if (!sessionId.value) return
  const websocket = wsStore.connect(sessionId.value)
  websocket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    switch (data.type) {
      case 'status':
        status.value = data.status
        currentMessage.value = data.message
        if (data.data?.current_step) currentStep.value = data.data.current_step
        if (data.data?.screenshot) screenshots.value.push(data.data.screenshot)
        if (['completed', 'error', 'stopped'].includes(data.status)) {
          isRunning.value = false
          isPaused.value = false
        }
        if (data.status === 'paused') isPaused.value = true
        else if (data.status === 'running') isPaused.value = false
        break
      case 'step_complete':
        if (data.data?.step) currentStep.value = data.data.step
        if (data.data?.screenshot) screenshots.value.push(data.data.screenshot)
        break
    }
  }
}

// Get status color
const getStatusColor = (status) => {
  const colors = {
    'idle': 'bg-gray-100 text-gray-700',
    'starting': 'bg-blue-100 text-blue-700',
    'running': 'bg-amber-100 text-amber-700',
    'paused': 'bg-orange-100 text-orange-700',
    'completed': 'bg-emerald-100 text-emerald-700',
    'error': 'bg-rose-100 text-rose-700',
    'stopped': 'bg-gray-100 text-gray-700'
  }
  return colors[status] || 'bg-gray-100 text-gray-700'
}

// Lifecycle
onMounted(() => {
  loadTask()
})

onUnmounted(() => {
  if (sessionId.value) wsStore.disconnect(sessionId.value)
})
</script>
