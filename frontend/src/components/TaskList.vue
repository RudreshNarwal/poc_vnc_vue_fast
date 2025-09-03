<template>
  <div class="px-4 py-6 sm:px-0">
    <div class="sm:flex sm:items-center">
      <div class="sm:flex-auto">
        <h1 class="text-2xl font-semibold text-gray-900">Automation Tasks</h1>
        <p class="mt-2 text-sm text-gray-600">
          Manage your browser automation tasks. Some tasks may require file uploads.
        </p>
      </div>
      <div class="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
        <router-link
          to="/test/builder"
          class="inline-flex items-center justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Create Task
        </router-link>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="mt-8 text-center">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
      <p class="mt-2 text-gray-600">Loading tasks...</p>
    </div>

    <!-- Task Grid View -->
    <div v-else-if="tasks.length > 0" class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="task in tasks" :key="task.id" 
           class="bg-white overflow-hidden shadow rounded-lg border border-gray-200 hover:shadow-lg transition-shadow">
        <div class="px-6 py-4">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-lg font-medium text-gray-900">{{ task.name }}</h3>
            <span :class="getStatusColor(task.status)" 
                  class="inline-flex rounded-full px-2 py-0.5 text-xs font-semibold">
              {{ task.status || 'ready' }}
            </span>
          </div>
          
          <p class="text-sm text-gray-600 mb-4 line-clamp-2">
            {{ task.description || 'No description available' }}
          </p>
          
          <!-- Task Metadata -->
          <div class="space-y-2 text-sm">
            <div class="flex items-center text-gray-500">
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <span>{{ task.script_path ? 'Script-based' : 'Step-based' }} ({{ task.steps?.length || 0 }} steps)</span>
            </div>
            
            <div v-if="hasFileRequirement(task)" class="flex items-center text-amber-600">
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <span class="font-medium">File upload required</span>
            </div>
            
            <div class="flex items-center text-gray-500">
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{{ formatDate(task.created_at) }}</span>
            </div>
            
            <!-- Recent Executions -->
            <div v-if="task.executions && task.executions.length > 0" class="pt-2 border-t border-gray-100">
              <div class="text-xs text-gray-500">Recent executions: {{ task.executions.length }}</div>
            </div>
          </div>
        </div>
        
        <!-- Action Buttons -->
        <div class="bg-gray-50 px-6 py-3 flex justify-between items-center">
          <router-link
            :to="`/test/runner/${task.id}`"
            class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Run
          </router-link>
          
          <div class="flex space-x-2">
            <button
              @click="editTask(task)"
              class="text-amber-600 hover:text-amber-700"
              title="Edit task"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
            <button
              @click="deleteTask(task)"
              class="text-red-600 hover:text-red-700"
              title="Delete task"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Active Sessions Panel (if any) -->
    <div v-if="activeSessions.total_active > 0" class="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div class="flex items-center">
        <svg class="w-5 h-5 text-blue-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <span class="text-sm font-medium text-blue-900">
          {{ activeSessions.total_active }} automation{{ activeSessions.total_active > 1 ? 's' : '' }} currently running
        </span>
        <span class="ml-2 text-xs text-blue-700">
          (Max parallel: {{ activeSessions.max_parallel }})
        </span>
      </div>
      <div class="mt-2 flex flex-wrap gap-2">
        <span v-for="session in activeSessions.sessions" :key="session.session_id"
              class="inline-flex items-center px-2 py-1 rounded text-xs font-medium"
              :class="session.is_paused ? 'bg-amber-100 text-amber-800' : 'bg-green-100 text-green-800'">
          {{ session.session_id.substring(0, 8) }}
          <span class="ml-1">({{ session.is_paused ? 'Paused' : 'Running' }})</span>
        </span>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="mt-8 text-center">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 48 48">
        <path d="M34 40h10v-4a6 6 0 00-10.712-3.714M34 40H14m20 0v-4a9.971 9.971 0 00-.712-3.714M14 40H4v-4a6 6 0 0110.713-3.714M14 40v-4c0-1.313.253-2.566.713-3.714m0 0A10.003 10.003 0 0124 26c4.21 0 7.813 2.602 9.288 6.286M30 14a6 6 0 11-12 0 6 6 0 0112 0zm12 6a4 4 0 11-8 0 4 4 0 018 0zm-28 0a4 4 0 11-8 0 4 4 0 018 0z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <h3 class="mt-2 text-sm font-medium text-gray-900">No tasks</h3>
      <p class="mt-1 text-sm text-gray-600">Get started by creating a new automation task.</p>
      <div class="mt-6">
        <router-link
          to="/test/builder"
          class="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Create Task
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const tasks = ref([])
const loading = ref(true)
const activeSessions = ref({ total_active: 0, sessions: [], max_parallel: 5 })

const loadTasks = async () => {
  try {
    loading.value = true
    const response = await axios.get('/api/tasks/')
    tasks.value = response.data
  } catch (error) {
    console.error('Failed to load tasks:', error)
  } finally {
    loading.value = false
  }
}

const loadActiveSessions = async () => {
  try {
    const response = await axios.get('/api/automation/active-sessions')
    activeSessions.value = response.data
  } catch (error) {
    console.error('Failed to load active sessions:', error)
  }
}

const hasFileRequirement = (task) => {
  if (!task.prerequisites) return false
  return task.prerequisites.some(p => p.type === 'file_upload' && p.required)
}

const getStatusColor = (status) => {
  const colors = {
    'draft': 'bg-gray-100 text-gray-700',
    'ready': 'bg-blue-100 text-blue-700',
    'running': 'bg-amber-100 text-amber-700',
    'completed': 'bg-emerald-100 text-emerald-700',
    'failed': 'bg-rose-100 text-rose-700'
  }
  return colors[status] || 'bg-gray-100 text-gray-700'
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const editTask = (task) => {
  router.push(`/test/builder?edit=${task.id}`)
}

const deleteTask = async (task) => {
  if (confirm(`Are you sure you want to delete "${task.name}"?`)) {
    try {
      await axios.delete(`/api/tasks/${task.id}`)
      await loadTasks()
    } catch (error) {
      console.error('Failed to delete task:', error)
      alert('Failed to delete task')
    }
  }
}

// Lifecycle
let intervalId = null

onMounted(() => {
  loadTasks()
  loadActiveSessions()
  // Poll for active sessions every 5 seconds
  intervalId = setInterval(loadActiveSessions, 5000)
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>