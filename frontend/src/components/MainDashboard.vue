<template>
  <div class="min-h-screen bg-gray-50 text-gray-900">
    <!-- App Header -->
    <header class="h-14 border-b border-gray-200 flex items-center justify-between px-5 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/70">
      <div class="text-base font-semibold tracking-tight">Automation Tasks</div>
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center gap-2 text-xs" :class="isRunning ? 'text-green-700' : 'text-gray-500'">
          <span class="w-2 h-2 rounded-full" :class="isRunning ? 'bg-green-500' : 'bg-gray-300'"></span>
          {{ isRunning ? 'Live' : 'Idle' }}
        </span>
        <div class="flex items-center gap-2">
          <button
            v-if="!isRunning && selectedTaskId"
            class="px-3.5 py-1.5 text-sm rounded-md bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm active:scale-[.99]"
            @click="startAutomation"
          >Start</button>
          <button
            v-if="isRunning && !isPaused"
            class="px-3.5 py-1.5 text-sm rounded-md bg-amber-500 hover:bg-amber-600 text-white shadow-sm"
            @click="pauseAutomation"
          >Pause</button>
          <button
            v-if="isRunning && isPaused"
            class="px-3.5 py-1.5 text-sm rounded-md bg-blue-600 hover:bg-blue-700 text-white shadow-sm"
            @click="resumeAutomation"
          >Resume</button>
          <button
            v-if="isRunning"
            class="px-3.5 py-1.5 text-sm rounded-md bg-red-600 hover:bg-red-700 text-white shadow-sm"
            @click="stopAutomation"
          >Stop</button>
        </div>
      </div>
    </header>

    <div class="flex h-[calc(100vh-56px)]">
      <!-- Left Sidebar: Task navigator -->
      <aside class="w-80 border-r border-gray-200 p-4 overflow-y-auto bg-white hidden md:block">
        <div class="mb-3">
          <input v-model="taskSearch" placeholder="Search tasks..." class="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition" />
        </div>
        <div class="space-y-3">
          <button
            v-for="task in filteredTasks"
            :key="task.id"
            class="w-full text-left p-3 rounded-xl bg-white border border-gray-200 shadow-sm hover:shadow transition"
            :class="{ 'ring-2 ring-blue-600': task.id === selectedTaskId }"
            @click="selectTask(task.id)"
          >
            <div class="flex items-center justify-between">
              <div class="text-sm font-medium truncate">{{ task.name }}</div>
              <span class="text-[10px] px-2 py-0.5 rounded-full" :class="statusPill(task.status)">{{ task.status || 'Ready' }}</span>
            </div>
            <div class="text-xs text-gray-500 mt-1 line-clamp-2">{{ task.description }}</div>
          </button>
        </div>
      </aside>

      <!-- Setup/Steps Panel -->
      <aside class="w-[360px] border-r border-gray-200 p-4 space-y-4 bg-gray-50 hidden lg:block">
        <!-- Prerequisites Upload (placeholder UI) -->
        <section>
          <div class="text-xs font-semibold text-gray-700 mb-2">Prerequisites</div>
          <div class="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-center shadow-sm">
            <div class="mx-auto mb-2 w-12 h-12 rounded-full bg-gray-50 border border-gray-200 flex items-center justify-center">
              <svg class="w-5 h-5 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            </div>
            <div class="text-sm text-gray-700">Drop your files here, or <button class="text-blue-600 hover:underline">browse</button></div>
            <div class="text-[10px] text-gray-500 mt-1">Supports: .xlsx, .xls, .csv</div>
          </div>
        </section>

        <!-- Automation Steps -->
        <section>
          <div class="flex items-center justify-between mb-2">
            <div class="text-xs font-semibold text-gray-700">Automation Steps</div>
            <button class="text-xs px-2.5 py-1.5 rounded-lg bg-white border border-gray-300 shadow-sm hover:shadow">Edit Steps</button>
          </div>
          <div class="space-y-2">
            <div v-for="(step, idx) in currentSteps" :key="idx" class="flex items-center gap-2 bg-white border border-gray-200 rounded-lg p-2.5 shadow-sm">
              <div class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-semibold" :class="stepClass(idx)">
                <template v-if="idx + 1 < currentStep">
                  <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>
                </template>
                <template v-else>
                  {{ idx + 1 }}
                </template>
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm truncate">{{ step.action || step }}</div>
              </div>
            </div>
          </div>
        </section>

        <!-- Run Settings -->
        <section class="pt-2 border-t border-gray-200">
          <div class="text-xs font-semibold text-gray-700 mb-2">Run Settings</div>
          <div class="space-y-3 text-sm text-gray-700">
            <label class="flex items-center gap-2"><input type="checkbox" class="accent-blue-600" v-model="headless"/> Headless mode</label>
            <label class="flex items-center gap-2"><input type="checkbox" class="accent-blue-600" v-model="takeScreens"/> Take screenshots</label>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <div class="text-xs text-gray-500">Timeout (seconds)</div>
                <input v-model.number="timeout" class="w-full bg-white border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-600" />
              </div>
              <div>
                <div class="text-xs text-gray-500">Retry Attempts</div>
                <input v-model.number="retries" class="w-full bg-white border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-600" />
              </div>
              <div class="col-span-2">
                <div class="text-xs text-gray-500">Wait Between Steps (ms)</div>
                <input v-model.number="waitBetween" class="w-full bg-white border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-600" />
              </div>
            </div>
          </div>
        </section>
      </aside>

      <!-- Center: Browser viewport with toolbar -->
      <section class="flex-1 flex flex-col">
        <!-- Browser toolbar -->
        <div class="px-5 py-3 border-b border-gray-200 bg-white">
          <div class="max-w-5xl">
            <div class="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
              <div class="flex items-center gap-2 px-3 py-2.5 border-b border-gray-200">
                <div class="flex items-center gap-1">
                  <span class="w-3 h-3 rounded-full bg-red-500"></span>
                  <span class="w-3 h-3 rounded-full bg-yellow-400"></span>
                  <span class="w-3 h-3 rounded-full bg-green-500"></span>
                </div>
                <input v-model="addressBar" class="flex-1 bg-gray-50 rounded-md px-3 py-1.5 text-sm border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-600" />
                <button class="px-2.5 py-1.5 rounded-md bg-gray-50 border border-gray-300 text-xs hover:shadow" @click="reload">⟳</button>
                <button class="px-2.5 py-1.5 rounded-md bg-gray-50 border border-gray-300 text-xs hover:shadow" @click="toggleFullscreen">⤢</button>
              </div>
              <div class="h-[640px] bg-black">
                <BrowserViewport :session-id="sessionId" :is-running="isRunning" @pause="onPause" @resume="onResume" />
              </div>
            </div>
          </div>
        </div>

        <!-- Bottom run history bar -->
        <div class="px-5 py-3 border-t border-gray-200 text-xs text-gray-600 bg-white">Run History</div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { useWebSocketStore } from '../stores/websocket.js'
import BrowserViewport from './BrowserViewport.vue'

const wsStore = useWebSocketStore()

// Tasks
const tasks = ref([])
const taskSearch = ref('')
const selectedTaskId = ref(null)

const filteredTasks = computed(() => {
  const q = taskSearch.value.trim().toLowerCase()
  if (!q) return tasks.value
  return tasks.value.filter(t => (t.name || '').toLowerCase().includes(q))
})

const currentTask = computed(() => tasks.value.find(t => t.id === selectedTaskId.value))
const currentSteps = computed(() => (currentTask.value?.steps || ['Navigate to test form website','Wait for form to load','Hand over control for user interaction','Click Add Route button']))

// Automation state
const sessionId = ref(null)
const isRunning = ref(false)
const isPaused = ref(false)
const status = ref('idle')
const currentStep = ref(0)

// Settings (local for UI only)
const addressBar = ref('about:blank')
const headless = ref(false)
const takeScreens = ref(true)
const timeout = ref(30000)
const retries = ref(1)
const waitBetween = ref(0)

// Helpers
const statusPill = (s) => {
  if (s === 'completed') return 'bg-emerald-100 text-emerald-700'
  if (s === 'running') return 'bg-green-100 text-green-700'
  if (s === 'error') return 'bg-rose-100 text-rose-700'
  return 'bg-blue-100 text-blue-700'
}

const stepClass = (idx) => {
  if (idx + 1 < currentStep.value) return 'bg-green-500 text-white shadow-sm'
  if (idx + 1 === currentStep.value && isRunning.value) return 'bg-blue-600 text-white shadow-sm'
  return 'bg-gray-200 text-gray-700'
}

// Actions
const selectTask = (id) => {
  selectedTaskId.value = id
}

const connectWebSocket = () => {
  if (!sessionId.value) return
  const websocket = wsStore.connect(sessionId.value)
  websocket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'status') {
      status.value = data.status
      if (data.data?.current_step) currentStep.value = data.data.current_step
      if (data.status === 'completed' || data.status === 'error' || data.status === 'stopped') {
        isRunning.value = false
        isPaused.value = false
      }
      if (data.status === 'paused') isPaused.value = true
      else if (data.status === 'running') isPaused.value = false
    }
    if (data.type === 'step_complete') {
      if (data.data?.step) currentStep.value = data.data.step
    }
  }
}

const startAutomation = async () => {
  try {
    if (!selectedTaskId.value) return
    const resp = await axios.post(`/api/automation/execute/${selectedTaskId.value}`)
    sessionId.value = resp.data.session_id
    isRunning.value = true
    status.value = 'starting'
    currentStep.value = 0
    connectWebSocket()
  } catch (e) {
    console.error('Failed to start automation', e)
    alert('Failed to start automation')
  }
}

const pauseAutomation = async () => {
  try {
    if (!sessionId.value) return
    await axios.post(`/api/automation/pause/${sessionId.value}`)
    isPaused.value = true
  } catch {}
}
const resumeAutomation = async () => {
  try {
    if (!sessionId.value) return
    await axios.post(`/api/automation/resume/${sessionId.value}`)
    isPaused.value = false
  } catch {}
}
const stopAutomation = async () => {
  try {
    if (!sessionId.value) return
    await axios.post(`/api/automation/stop/${sessionId.value}`)
    isRunning.value = false
    isPaused.value = false
  } catch {}
}

// Toolbar dummy actions
const reload = () => {}
const toggleFullscreen = () => {}
const onPause = () => {}
const onResume = () => {}

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/tasks/')
    tasks.value = data
    if (tasks.value.length) selectedTaskId.value = tasks.value[0].id
  } catch (e) {
    console.error('Failed to load tasks', e)
  }
})
</script>
