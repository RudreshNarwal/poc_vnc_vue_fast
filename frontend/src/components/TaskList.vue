<template>
  <div class="px-4 py-6 sm:px-0">
    <div class="sm:flex sm:items-center">
      <div class="sm:flex-auto">
        <h1 class="text-2xl font-semibold text-gray-900">Automation Tasks</h1>
        <p class="mt-2 text-sm text-gray-600">
          Manage your browser automation tasks
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

    <!-- Task List -->
    <div v-else-if="tasks.length > 0" class="mt-8 flow-root">
      <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
        <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
          <div class="overflow-hidden shadow-sm ring-1 ring-gray-200 md:rounded-lg bg-white">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">
                    Name
                  </th>
                  <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                    Status
                  </th>
                  <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                    Steps
                  </th>
                  <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                    Created
                  </th>
                  <th scope="col" class="relative py-3.5 pl-3 pr-4 sm:pr-6">
                    <span class="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white">
                <tr v-for="task in tasks" :key="task.id">
                  <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm sm:pl-6">
                    <div class="flex items-center">
                      <div>
                        <div class="font-medium text-gray-900">{{ task.name }}</div>
                        <div class="text-gray-600">{{ task.description || 'No description' }}</div>
                      </div>
                    </div>
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm">
                    <span
                      :class="getStatusColor(task.status)"
                      class="inline-flex rounded-full px-2 py-0.5 text-xs font-semibold"
                    >
                      {{ task.status || 'ready' }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-700">
                    {{ task.steps.length }} steps
                  </td>
                  <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-700">
                    {{ formatDate(task.created_at) }}
                  </td>
                  <td class="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                    <div class="flex justify-end space-x-3">
                      <router-link
                        :to="`/test/runner/${task.id}`"
                        class="text-blue-600 hover:text-blue-700"
                      >
                        Run
                      </router-link>
                      <button
                        @click="editTask(task)"
                        class="text-amber-600 hover:text-amber-700"
                      >
                        Edit
                      </button>
                      <button
                        @click="deleteTask(task)"
                        class="text-red-600 hover:text-red-700"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="mt-8 text-center">
      <svg class="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
        <path d="M34 40h10v-4a6 6 0 00-10.712-3.714M34 40H14m20 0v-4a9.971 9.971 0 00-.712-3.714M14 40H4v-4a6 6 0 0110.713-3.714M14 40v-4c0-1.313.253-2.566.713-3.714m0 0A10.003 10.003 0 0124 26c4.21 0 7.813 2.602 9.288 6.286M30 14a6 6 0 11-12 0 6 6 0 0112 0zm12 6a4 4 0 11-8 0 4 4 0 018 0zm-28 0a4 4 0 11-8 0 4 0 08 0z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const tasks = ref([])
const loading = ref(true)

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
    year: 'numeric',
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

onMounted(() => {
  loadTasks()
})
</script>
