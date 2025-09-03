import { defineStore } from 'pinia'

/**
 * Store FileResponse objects keyed by task id.
 * FileResponse shape (from backend /api/files/upload):
 * {
 *   id, filename, original_filename, file_type,
 *   status, validation_results, task_id, created_at, url
 * }
 */
export const useUploadsStore = defineStore('uploads', {
  state: () => ({
    byTaskId: {} // { [taskId: number]: FileResponse }
  }),
  getters: {
    getByTaskId: (state) => (taskId) => state.byTaskId[taskId]
  },
  actions: {
    setForTask(taskId, fileResponse) {
      this.byTaskId[taskId] = fileResponse
    },
    clearForTask(taskId) {
      delete this.byTaskId[taskId]
    }
  }
})
