<template>
  <div class="p-6 space-y-4">
    <h1 class="text-2xl font-semibold text-gray-900">TigerVNC Test Harness</h1>
    <p class="text-gray-600">Use this page to create/destroy a TigerVNC session and verify noVNC connectivity.</p>

    <!-- Controls -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div>
        <label class="block text-sm text-gray-600 mb-1">User ID</label>
        <input v-model="userId"
               class="w-full border rounded px-3 py-2"
               placeholder="test-user-123" />
      </div>
      <div>
        <label class="block text-sm text-gray-600 mb-1">Task ID (optional)</label>
        <input v-model.number="taskId"
               type="number"
               min="0"
               class="w-full border rounded px-3 py-2"
               placeholder="e.g. 1" />
      </div>
      <div class="flex items-end gap-2">
        <button @click="startDemo"
                :disabled="isRunning"
                class="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50">
          Start Demo
        </button>
        <button @click="destroySession"
                :disabled="!isRunning"
                class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50">
          Stop
        </button>
      </div>
    </div>

    <!-- Session Info -->
    <div v-if="sessionDetails" class="bg-white rounded border p-4 text-sm text-gray-800">
      <div class="font-medium mb-2">Session Details</div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
        <div><span class="text-gray-500">Session ID:</span> {{ sessionDetails.session_id }}</div>
        <div><span class="text-gray-500">Display:</span> :{{ sessionDetails.display }}</div>
        <div><span class="text-gray-500">web_port:</span> {{ sessionDetails.web_port }}</div>
        <div class="md:col-span-3"><span class="text-gray-500">VNC URL:</span> {{ sessionDetails.vnc_url }}</div>
        <div class="md:col-span-3"><span class="text-gray-500">Password:</span> {{ sessionDetails.password }}</div>
      </div>
    </div>

    <!-- VNC Viewport -->
    <div class="h-[600px] bg-black rounded overflow-hidden border">
      <MultiSessionBrowserViewport
        v-if="isRunning"
        ref="viewportRef"
        :user-id="userId"
        :task-id="taskId || null"
        :is-running="isRunning"
        :show-resource-usage="true"
        @session-created="onSessionCreated"
        @session-destroyed="onSessionDestroyed"
        @connection-changed="onConnectionChanged"
      />
      <div v-else class="h-full flex items-center justify-center text-gray-400">
        Start a session to display the VNC canvas here.
      </div>
    </div>

    <!-- Status -->
    <div class="text-sm text-gray-600">
      <span class="text-gray-500">Status:</span> {{ statusMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import MultiSessionBrowserViewport from './MultiSessionBrowserViewport.vue'

// Generate a default userId
const defaultId = (typeof crypto !== 'undefined' && crypto.randomUUID)
  ? crypto.randomUUID()
  : `test-${Date.now()}-${Math.random().toString(36).slice(2)}`

const userId = ref(defaultId)
const taskId = ref(null)
const isRunning = ref(false)
const statusMessage = ref('Idle')
const sessionDetails = ref(null)
const autoLaunchChromium = ref(false)

const viewportRef = ref(null)

const startSession = async () => {
  if (isRunning.value) return
  isRunning.value = true
  statusMessage.value = 'Starting session...'
  // MultiSessionBrowserViewport will auto-request a session on mount
}

const startDemo = async () => {
  autoLaunchChromium.value = true
  statusMessage.value = 'Starting demo... requesting session and preparing Chromium...'
  await startSession()
}

const destroySession = async () => {
  try {
    if (viewportRef.value) {
      await viewportRef.value.cleanup()
    }
  } catch (e) {
    // ignore
  } finally {
    isRunning.value = false
    sessionDetails.value = null
    statusMessage.value = 'Session destroyed'
  }
}

const runChromiumDemo = async () => {
  try {
    if (!sessionDetails.value) {
      statusMessage.value = 'No active session';
      return;
    }
    statusMessage.value = 'Launching Chromium demo...';
    await axios.post(`/api/test-browser/session/${sessionDetails.value.session_id}`);
    statusMessage.value = 'Chromium launched. Check the VNC canvas.';
  } catch (e) {
    statusMessage.value = `Failed to launch Chromium: ${e?.message || e}`;
  }
}

const onSessionCreated = async (session) => {
  sessionDetails.value = session
  statusMessage.value = 'Session created. Connecting VNC...'
  // Auto-launch Chromium demo on session if requested
  if (autoLaunchChromium.value) {
    try {
      statusMessage.value = 'Launching Chromium on session...'
      await axios.post(`/api/test-browser/session/${session.session_id}`)
      statusMessage.value = 'Chromium launched on session. Check the VNC canvas.'
    } catch (e) {
      statusMessage.value = `Failed to launch Chromium: ${e?.message || e}`
    } finally {
      autoLaunchChromium.value = false
    }
  }
}

const onSessionDestroyed = () => {
  statusMessage.value = 'Session destroyed'
  sessionDetails.value = null
}

const onConnectionChanged = (state) => {
  statusMessage.value = `Connection: ${state}`
}
</script>
