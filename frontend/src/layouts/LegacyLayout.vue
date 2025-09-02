<template>
  <div class="min-h-screen bg-gray-50 text-gray-900">
    <nav class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <h1 class="text-xl font-bold text-blue-600">Automation Studio</h1>
            </div>
            <div class="hidden md:block">
              <div class="ml-10 flex items-baseline space-x-4">
                <router-link
                  to="/test"
                  class="hover:bg-gray-100 px-3 py-2 rounded-md text-sm font-medium text-gray-700"
                  :class="{ 'bg-gray-100': $route.name === 'LegacyHome' }"
                >
                  Home
                </router-link>
                <router-link
                  to="/test/tasks"
                  class="hover:bg-gray-100 px-3 py-2 rounded-md text-sm font-medium text-gray-700"
                  :class="{ 'bg-gray-100': $route.name === 'LegacyTasks' }"
                >
                  Tasks
                </router-link>
                <router-link
                  to="/test/builder"
                  class="hover:bg-gray-100 px-3 py-2 rounded-md text-sm font-medium text-gray-700"
                  :class="{ 'bg-gray-100': $route.name === 'LegacyBuilder' }"
                >
                  Builder
                </router-link>
              </div>
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <div class="flex items-center">
              <div 
                :class="healthStatus === 'healthy' ? 'bg-green-500' : 'bg-red-500'"
                class="w-2 h-2 rounded-full mr-2"
              ></div>
              <span class="text-sm text-gray-600">{{ healthStatus }}</span>
            </div>
          </div>
        </div>
      </div>
    </nav>

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const healthStatus = ref('checking')

const checkHealth = async () => {
  try {
    const response = await axios.get('/api/health')
    healthStatus.value = response.data.status
  } catch (error) {
    healthStatus.value = 'error'
    console.error('Health check failed:', error)
  }
}

onMounted(() => {
  checkHealth()
  setInterval(checkHealth, 30000)
})
</script>
