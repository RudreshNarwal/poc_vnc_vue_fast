<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <!-- Navigation -->
    <nav class="bg-gray-800 border-b border-gray-700">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <h1 class="text-xl font-bold text-blue-400">Automation Studio</h1>
            </div>
            <div class="hidden md:block">
              <div class="ml-10 flex items-baseline space-x-4">
                <router-link
                  to="/"
                  class="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium"
                  :class="{ 'bg-gray-700': $route.name === 'Home' }"
                >
                  Home
                </router-link>
                <router-link
                  to="/tasks"
                  class="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium"
                  :class="{ 'bg-gray-700': $route.name === 'Tasks' }"
                >
                  Tasks
                </router-link>
                <router-link
                  to="/builder"
                  class="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium"
                  :class="{ 'bg-gray-700': $route.name === 'Builder' }"
                >
                  Builder
                </router-link>
              </div>
            </div>
          </div>
          
          <!-- Health Status -->
          <div class="flex items-center space-x-2">
            <div class="flex items-center">
              <div 
                :class="healthStatus === 'healthy' ? 'bg-green-500' : 'bg-red-500'"
                class="w-2 h-2 rounded-full mr-2"
              ></div>
              <span class="text-sm text-gray-300">{{ healthStatus }}</span>
            </div>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
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
  // Check health every 30 seconds
  setInterval(checkHealth, 30000)
})
</script>
