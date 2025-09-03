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
            :disabled="!canStart"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
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
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
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
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 110 2H10a1 1 0 01-1-1z" />
            </svg>
            Stop
          </button>
        </div>
      </div>
    </div>

    <!-- File Upload Section (if required) -->
    <div v-if="requiresFile && !isRunning" class="mb-6 bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
      <h3 class="text-lg font-medium text-gray-900 mb-4">
        📁 File Upload Required
      </h3>
      <p class="text-sm text-gray-600 mb-4">
        {{ fileRequirement?.description || 'This task requires a data file.' }}
      </p>
      
      <div 
        class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-gray-400 transition-colors"
        :class="{ 'border-blue-500 bg-blue-50': isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleFileDrop"
      >
        <input 
          type="file" 
          ref="fileInput" 
          @change="handleFileUpload" 
          accept=".csv,.xlsx,.xls" 
          class="hidden" 
        />
        
        <div v-if="!uploadedFile">
          <svg class="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
            <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <p class="mt-2 text-sm text-gray-600">
            <button type="button" @click="$refs.fileInput.click()" class="font-medium text-blue-600 hover:text-blue-500">
              Click to upload
            </button>
            or drag and drop
          </p>
          <p class="text-xs text-gray-500">CSV or Excel files only</p>
        </div>
        
        <div v-else-if="validating" class="py-4">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p class="mt-2 text-sm text-gray-600">Validating file...</p>
        </div>
        
        <div v-else-if="uploadedFile" class="py-4">
          <div class="flex items-center justify-center">
            <svg class="h-8 w-8 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
            <div class="ml-3 text-left">
              <p class="text-sm font-medium text-gray-900">{{ uploadedFile.original_filename }}</p>
              <p class="text-xs text-gray-500">{{ uploadedFile.total_rows }} rows validated</p>
            </div>
            <button 
              @click="removeFile" 
              class="ml-auto text-red-500 hover:text-red-700"
            >
              <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
        
        <div v-if="uploadError" class="mt-4 text-sm text-red-600">
          {{ uploadError }}
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Browser Viewport -->
      <div class="lg:col-span-2">
        <div class="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div class="px-4 py-3 border-b border-gray-200">
            <h3 class="text-lg font-medium text-gray-900">Browser Viewport</h3>
            <p class="text-sm text-gray-600">
              {{ sessionId ? `Session: ${sessionId.substring(0, 8)}...` : 'Live view of automation execution' }}
            </p>
          </div>
          <div class="p-0 h-96 lg:h-[600px] bg-black">
            <BrowserViewport
              :session-id="sessionId"
              :is-running="isRunning"
              @pause="pauseAutomation"
              @resume="resumeAutomation"
            />
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
            <div v-if="currentStep > 0 || progressData.processed_count" class="flex justify-between">
              <span class="text-sm text-gray-600">Progress:</span>
              <span class="text-sm text-gray-900">
                {{ progressData.processed_count || currentStep }} / {{ progressData.total_records || totalSteps }}
              </span>
            </div>
            <div v-if="progressData.success_count !== undefined" class="flex justify-between">
              <span class="text-sm text-gray-600">Success:</span>
              <span class="text-sm text-green-600 font-medium">{{ progressData.success_count }}</span>
            </div>
            <div v-if="progressData.failed_count > 0" class="flex justify-between">
              <span class="text-sm text-gray-600">Failed:</span>
              <span class="text-sm text-red-600 font-medium">{{ progressData.failed_count }}</span>
            </div>
            <div v-if="currentStep > 0 || progressData.processed_count" class="w-full bg-gray-100 rounded-full h-2">
              <div 
                class="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                :style="{ width: `${getProgressPercentage()}%` }"
              ></div>
            </div>
            <div v-if="currentMessage" class="text-sm text-gray-700 mt-2">
              {{ currentMessage }}
            </div>
            <div v-if="progressData.current_route" class="text-xs text-gray-500">
              Current: {{ progressData.current_route }}
            </div>
          </div>
        </div>

        <!-- Task Info -->
        <div v-if="task" class="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Task Information</h3>
          <div class="space-y-2 text-sm">
            <div>
              <span class="text-gray-600">Type:</span>
              <span class="ml-2 text-gray-900">{{ task.script_path ? 'Script-based' : 'Step-based' }}</span>
            </div>
            <div v-if="uploadedFile">
              <span class="text-gray-600">Data File:</span>
              <span class="ml-2 text-gray-900">{{ uploadedFile.original_filename }}</span>
            </div>
            <div v-if="task.prerequisites && task.prerequisites.length > 0">
              <span class="text-gray-600">Prerequisites:</span>
              <ul class="mt-1 ml-4 list-disc list-inside text-gray-700">
                <li v-for="(prereq, idx) in task.prerequisites" :key="idx">
                  {{ prereq.name }} ({{ prereq.type }})
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Active Sessions (for parallel execution) -->
        <div v-if="activeSessions.length > 0" class="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Active Sessions</h3>
          <div class="space-y-2 max-h-32 overflow-y-auto">
            <div v-for="session in activeSessions" :key="session.session_id" 
                 class="flex items-center justify-between p-2 bg-gray-50 rounded">
              <span class="text-xs text-gray-600">{{ session.session_id.substring(0, 8) }}...</span>
              <span :class="session.is_paused ? 'text-amber-600' : 'text-green-600'" class="text-xs font-medium">
                {{ session.is_paused ? 'Paused' : 'Running' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
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
const progressData = ref({})
const activeSessions = ref([])

// File upload state
const requiresFile = ref(false)
const fileRequirement = ref(null)
const uploadedFile = ref(null)
const validating = ref(false)
const uploadError = ref('')
const isDragging = ref(false)
const fileInput = ref(null)

// Reset all per-task state when switching tasks
const resetTaskState = () => {
  task.value = null
  sessionId.value = null
  isRunning.value = false
  isPaused.value = false
  status.value = 'idle'
  currentStep.value = 0
  totalSteps.value = 0
  currentMessage.value = ''
  progressData.value = {}
  requiresFile.value = false
  fileRequirement.value = null
  uploadedFile.value = null
  validating.value = false
  uploadError.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

// Computed
const canStart = computed(() => {
  if (!task.value) return false
  if (requiresFile.value && !uploadedFile.value) return false
  return true
})

const getProgressPercentage = computed(() => {
  if (progressData.value.processed_count && progressData.value.total_records) {
    return (progressData.value.processed_count / progressData.value.total_records) * 100
  }
  if (currentStep.value && totalSteps.value) {
    return (currentStep.value / totalSteps.value) * 100
  }
  return 0
})

// Load task data
const loadTask = async () => {
  try {
    const taskIdToLoad = props.taskId || route.params.taskId
    if (!taskIdToLoad) return
    
    const response = await axios.get(`/api/tasks/${taskIdToLoad}`)
    task.value = response.data
    totalSteps.value = response.data.steps?.length || 0
    
    // Check if task requires file upload
    requiresFile.value = false
    fileRequirement.value = null
    if (response.data.prerequisites) {
      const filePrereq = response.data.prerequisites.find(p => p.type === 'file_upload' && p.required)
      if (filePrereq) {
        requiresFile.value = true
        fileRequirement.value = filePrereq
      }
    }
  } catch (error) {
    console.error('Failed to load task:', error)
  }
}

// File handling
const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  await processFile(file)
}

const handleFileDrop = async (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file) await processFile(file)
}

const processFile = async (file) => {
  validating.value = true
  uploadError.value = ''
  
  const formData = new FormData()
  formData.append('file', file)
  formData.append('task_id', (props.taskId || route.params.taskId) ?? '')
  
  try {
    // Use API that creates a DB record and returns an id
    const response = await axios.post('/api/files/upload', formData)
    uploadedFile.value = response.data
    uploadedFile.value.total_rows = response.data.validation_results?.total_rows || 0
    validating.value = false
  } catch (error) {
    validating.value = false
    uploadError.value = error.response?.data?.detail || 'File upload failed'
    uploadedFile.value = null
  }
}

const removeFile = () => {
  uploadedFile.value = null
  uploadError.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

// Start automation
const startAutomation = async () => {
  try {
    const taskIdToRun = props.taskId || route.params.taskId
    if (!taskIdToRun) return
    
    const requestData = {}
    if (uploadedFile.value) {
      requestData.file_id = uploadedFile.value.id
    }
    
    const response = await axios.post(`/api/automation/execute/${taskIdToRun}`, requestData)
    sessionId.value = response.data.session_id
    isRunning.value = true
    status.value = 'starting'
    currentMessage.value = response.data.message
    connectWebSocket()
    
    // Load active sessions
    loadActiveSessions()
  } catch (error) {
    console.error('Failed to start automation:', error)
    alert(error.response?.data?.detail || 'Failed to start automation')
  }
}

// Pause/Resume/Stop automation
const pauseAutomation = async () => {
  try {
    if (!sessionId.value) return
    await axios.post(`/api/automation/pause/${sessionId.value}`)
    isPaused.value = true
  } catch (error) {
    console.error('Failed to pause automation:', error)
  }
}

const resumeAutomation = async () => {
  try {
    if (!sessionId.value) return
    await axios.post(`/api/automation/resume/${sessionId.value}`)
    isPaused.value = false
  } catch (error) {
    console.error('Failed to resume automation:', error)
  }
}

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

// Load active sessions
const loadActiveSessions = async () => {
  try {
    const response = await axios.get('/api/automation/active-sessions')
    activeSessions.value = response.data.sessions.filter(s => s.session_id !== sessionId.value)
  } catch (error) {
    console.error('Failed to load active sessions:', error)
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
        
        // Update progress data
        if (data.data) {
          progressData.value = { ...progressData.value, ...data.data }
          if (data.data.current_step) currentStep.value = data.data.current_step
        }
        
        // Update state based on status
        if (['completed', 'error', 'stopped', 'failed'].includes(data.status)) {
          isRunning.value = false
          isPaused.value = false
        }
        if (data.status === 'paused') isPaused.value = true
        else if (data.status === 'running') isPaused.value = false
        break
        
      case 'progress':
        progressData.value = { ...progressData.value, ...data.data }
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
    'failed': 'bg-red-100 text-red-700',
    'error': 'bg-rose-100 text-rose-700',
    'stopped': 'bg-gray-100 text-gray-700'
  }
  return colors[status] || 'bg-gray-100 text-gray-700'
}

// Lifecycle
let intervalId = null

onMounted(() => {
  resetTaskState()
  loadTask()
  loadActiveSessions()
  // Poll active sessions
  intervalId = setInterval(loadActiveSessions, 5000)
})

onUnmounted(() => {
  if (sessionId.value) wsStore.disconnect(sessionId.value)
  if (intervalId) clearInterval(intervalId)
})

// Watch for route task changes to reset state and reload
watch(() => route.params.taskId, async () => {
  resetTaskState()
  await loadTask()
})
</script>