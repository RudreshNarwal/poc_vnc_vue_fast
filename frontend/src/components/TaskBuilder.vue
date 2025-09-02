<template>
  <div class="px-4 py-6 sm:px-0">
    <div class="mb-8">
      <h1 class="text-2xl font-semibold text-white">
        {{ isEditing ? 'Edit Task' : 'Create New Task' }}
      </h1>
      <p class="mt-2 text-sm text-gray-300">
        Build your browser automation workflow step by step
      </p>
    </div>

    <form @submit.prevent="saveTask" class="space-y-8">
      <!-- Task Details -->
      <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h2 class="text-lg font-medium text-white mb-4">Task Details</h2>
        
        <div class="grid grid-cols-1 gap-6">
          <div>
            <label for="name" class="block text-sm font-medium text-gray-300">
              Task Name
            </label>
            <input
              type="text"
              id="name"
              v-model="task.name"
              required
              class="mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              placeholder="Enter task name"
            />
          </div>
          
          <div>
            <label for="description" class="block text-sm font-medium text-gray-300">
              Description (Optional)
            </label>
            <textarea
              id="description"
              v-model="task.description"
              rows="3"
              class="mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              placeholder="Describe what this task does"
            />
          </div>
        </div>
      </div>

      <!-- Steps -->
      <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-medium text-white">Automation Steps</h2>
          <button
            type="button"
            @click="addStep"
            class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Add Step
          </button>
        </div>

        <div v-if="task.steps.length === 0" class="text-center py-8 text-gray-400">
          No steps added yet. Click "Add Step" to get started.
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="(step, index) in task.steps"
            :key="index"
            class="bg-gray-700 rounded-lg p-4 border border-gray-600"
          >
            <div class="flex justify-between items-start mb-3">
              <span class="text-sm font-medium text-gray-300">Step {{ index + 1 }}</span>
              <button
                type="button"
                @click="removeStep(index)"
                class="text-red-400 hover:text-red-300"
              >
                Remove
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-300 mb-1">
                  Action
                </label>
                <select
                  v-model="step.action"
                  class="block w-full rounded-md bg-gray-600 border-gray-500 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option value="">Select action</option>
                  <option value="navigate">Navigate to URL</option>
                  <option value="click">Click Element</option>
                  <option value="type">Type Text</option>
                  <option value="select">Select Option</option>
                  <option value="wait">Wait</option>
                  <option value="screenshot">Take Screenshot</option>
                  <option value="interactive_pause">Interactive Pause</option>
                </select>
              </div>

              <div v-if="needsTarget(step.action)">
                <label class="block text-sm font-medium text-gray-300 mb-1">
                  {{ getTargetLabel(step.action) }}
                </label>
                <input
                  type="text"
                  v-model="step.target"
                  class="block w-full rounded-md bg-gray-600 border-gray-500 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  :placeholder="getTargetPlaceholder(step.action)"
                />
              </div>

              <div v-if="needsValue(step.action)">
                <label class="block text-sm font-medium text-gray-300 mb-1">
                  {{ getValueLabel(step.action) }}
                </label>
                <input
                  type="text"
                  v-model="step.value"
                  class="block w-full rounded-md bg-gray-600 border-gray-500 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  :placeholder="getValuePlaceholder(step.action)"
                />
              </div>
            </div>

            <div class="mt-3">
              <label class="block text-sm font-medium text-gray-300 mb-1">
                Description (Optional)
              </label>
              <input
                type="text"
                v-model="step.description"
                class="block w-full rounded-md bg-gray-600 border-gray-500 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                placeholder="Describe this step"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Prerequisites -->
      <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-medium text-white">Prerequisites</h2>
          <button
            type="button"
            @click="addPrerequisite"
            class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
          >
            Add Prerequisite
          </button>
        </div>

        <div v-if="task.prerequisites.length === 0" class="text-center py-4 text-gray-400">
          No prerequisites required.
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="(prereq, index) in task.prerequisites"
            :key="index"
            class="bg-gray-700 rounded-lg p-3 border border-gray-600"
          >
            <div class="flex justify-between items-start mb-2">
              <span class="text-sm font-medium text-gray-300">Prerequisite {{ index + 1 }}</span>
              <button
                type="button"
                @click="removePrerequisite(index)"
                class="text-red-400 hover:text-red-300"
              >
                Remove
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <select
                  v-model="prereq.type"
                  class="block w-full rounded-md bg-gray-600 border-gray-500 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option value="">Select type</option>
                  <option value="file_upload">File Upload</option>
                  <option value="environment_variable">Environment Variable</option>
                </select>
              </div>
              <div>
                <input
                  type="text"
                  v-model="prereq.name"
                  placeholder="Name"
                  class="block w-full rounded-md bg-gray-600 border-gray-500 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex justify-end space-x-3">
        <router-link
          to="/tasks"
          class="inline-flex items-center px-4 py-2 border border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-300 bg-gray-700 hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
        >
          Cancel
        </router-link>
        <button
          type="submit"
          :disabled="!isValid || saving"
          class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ saving ? 'Saving...' : (isEditing ? 'Update Task' : 'Create Task') }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const task = ref({
  name: '',
  description: '',
  steps: [],
  prerequisites: []
})

const saving = ref(false)
const isEditing = ref(false)
const editingId = ref(null)

const isValid = computed(() => {
  return task.value.name.trim() && task.value.steps.length > 0
})

const addStep = () => {
  task.value.steps.push({
    action: '',
    target: '',
    value: '',
    description: ''
  })
}

const removeStep = (index) => {
  task.value.steps.splice(index, 1)
}

const addPrerequisite = () => {
  task.value.prerequisites.push({
    type: '',
    name: '',
    description: '',
    required: true
  })
}

const removePrerequisite = (index) => {
  task.value.prerequisites.splice(index, 1)
}

const needsTarget = (action) => {
  return ['navigate', 'click', 'type', 'select', 'wait'].includes(action)
}

const needsValue = (action) => {
  return ['type', 'select', 'wait'].includes(action)
}

const getTargetLabel = (action) => {
  const labels = {
    'navigate': 'URL',
    'click': 'CSS Selector',
    'type': 'CSS Selector',
    'select': 'CSS Selector',
    'wait': 'Wait Type'
  }
  return labels[action] || 'Target'
}

const getTargetPlaceholder = (action) => {
  const placeholders = {
    'navigate': 'https://example.com',
    'click': '#button-id or .button-class',
    'type': '#input-id or .input-class',
    'select': '#select-id or .select-class',
    'wait': 'wait_for_element or delay'
  }
  return placeholders[action] || 'Enter target'
}

const getValueLabel = (action) => {
  const labels = {
    'type': 'Text to Type',
    'select': 'Option Value',
    'wait': 'Value'
  }
  return labels[action] || 'Value'
}

const getValuePlaceholder = (action) => {
  const placeholders = {
    'type': 'Text to enter',
    'select': 'option-value',
    'wait': 'CSS selector or milliseconds'
  }
  return placeholders[action] || 'Enter value'
}

const saveTask = async () => {
  try {
    saving.value = true
    
    const taskData = {
      name: task.value.name,
      description: task.value.description,
      steps: task.value.steps.filter(step => step.action),
      prerequisites: task.value.prerequisites.filter(prereq => prereq.type && prereq.name)
    }

    if (isEditing.value) {
      await axios.put(`/api/tasks/${editingId.value}`, taskData)
    } else {
      await axios.post('/api/tasks/', taskData)
    }

    router.push('/tasks')
  } catch (error) {
    console.error('Failed to save task:', error)
    alert('Failed to save task')
  } finally {
    saving.value = false
  }
}

const loadTask = async (taskId) => {
  try {
    const response = await axios.get(`/api/tasks/${taskId}`)
    const taskData = response.data
    
    task.value = {
      name: taskData.name,
      description: taskData.description || '',
      steps: taskData.steps || [],
      prerequisites: taskData.prerequisites || []
    }
    
    isEditing.value = true
    editingId.value = taskId
  } catch (error) {
    console.error('Failed to load task:', error)
    router.push('/tasks')
  }
}

onMounted(() => {
  const editId = route.query.edit
  if (editId) {
    loadTask(parseInt(editId))
  }
})
</script>
