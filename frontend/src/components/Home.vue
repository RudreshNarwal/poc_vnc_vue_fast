<template>
  <div class="px-4 py-6 sm:px-0">
    <!-- Hero Section -->
    <div class="text-center mb-12">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">
        Browser Automation Studio
      </h1>
      <p class="text-xl text-gray-600 max-w-3xl mx-auto">
        Create, manage, and execute browser automation tasks with real-time visual feedback through VNC integration.
      </p>
    </div>

    <!-- Feature Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
      <div class="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
        <div class="text-blue-600 mb-4">
          <svg class="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
          </svg>
        </div>
        <h3 class="text-xl font-semibold text-gray-900 mb-2">Visual Automation</h3>
        <p class="text-gray-600">
          Watch your automation tasks execute in real-time through our integrated VNC viewer.
        </p>
      </div>

      <div class="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
        <div class="text-green-600 mb-4">
          <svg class="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
          </svg>
        </div>
        <h3 class="text-xl font-semibold text-gray-900 mb-2">Task Builder</h3>
        <p class="text-gray-600">
          Create complex automation workflows with our intuitive step-by-step builder.
        </p>
      </div>

      <div class="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
        <div class="text-purple-600 mb-4">
          <svg class="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2M7 4h10M7 4l-2 16h14l-2-16M11 9v4m4-4v4"></path>
          </svg>
        </div>
        <h3 class="text-xl font-semibold text-gray-900 mb-2">File Integration</h3>
        <p class="text-gray-600">
          Upload Excel, CSV, and other files to provide data for your automation tasks.
        </p>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="text-center">
      <h2 class="text-2xl font-bold text-gray-900 mb-6">Quick Actions</h2>
      <div class="flex justify-center space-x-4 mb-4">
        <router-link
          to="/builder"
          class="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors"
        >
          Create New Task
        </router-link>
        <router-link
          to="/tasks"
          class="bg-gray-100 hover:bg-gray-200 text-gray-900 px-8 py-3 rounded-lg font-semibold transition-colors border border-gray-200"
        >
          View All Tasks
        </router-link>
      </div>
      <!-- Test Actions -->
      <div class="flex justify-center space-x-4">
        <button
          @click="testBrowser"
          :disabled="browserTesting"
          class="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-semibold transition-colors"
        >
          {{ browserTesting ? 'Testing...' : 'Test Browser + VNC' }}
        </button>
        <button
          @click="openVNC"
          class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2 rounded-lg font-semibold transition-colors"
        >
          Open VNC Viewer
        </button>
      </div>

      <!-- Test Results -->
      <div v-if="testResult" class="mt-4 p-4 rounded-lg" :class="testResult.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'">
        <p>{{ testResult.message }}</p>
      </div>
    </div>

    <!-- System Status -->
    <div class="mt-12 bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="text-center">
          <div class="text-2xl font-bold text-green-600">{{ systemStatus.backend ? '✓' : '✗' }}</div>
          <div class="text-sm text-gray-600">Backend</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-green-600">{{ systemStatus.database ? '✓' : '✗' }}</div>
          <div class="text-sm text-gray-600">Database</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-green-600">{{ systemStatus.vnc ? '✓' : '✗' }}</div>
          <div class="text-sm text-gray-600">VNC Server</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-blue-600">{{ systemStatus.timezone }}</div>
          <div class="text-sm text-gray-600">Timezone</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const systemStatus = ref({
  backend: false,
  database: false,
  vnc: false,
  timezone: 'Unknown'
})

const browserTesting = ref(false)
const testResult = ref(null)

const checkSystemStatus = async () => {
  try {
    const response = await axios.get('/api/health')
    systemStatus.value = {
      backend: true,
      database: true,
      vnc: true,
      timezone: response.data.timezone
    }
  } catch (error) {
    systemStatus.value = {
      backend: false,
      database: false,
      vnc: false,
      timezone: 'Unknown'
    }
  }
}

const testBrowser = async () => {
  browserTesting.value = true
  testResult.value = null
  try {
    const response = await axios.get('/api/test-browser')
    testResult.value = response.data
  } catch (error) {
    testResult.value = { status: 'error', message: 'Failed to test browser: ' + error.message }
  } finally {
    browserTesting.value = false
  }
}

const openVNC = () => {
  window.open('http://localhost:7900/vnc.html', '_blank')
}

onMounted(() => {
  checkSystemStatus()
})
</script>
