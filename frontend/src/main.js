import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

// Legacy components
import Home from './components/Home.vue'
import TaskBuilder from './components/TaskBuilder.vue'
import AutomationRunner from './components/AutomationRunner.vue'
import TaskList from './components/TaskList.vue'
import LegacyLayout from './layouts/LegacyLayout.vue'

// New main UI
import MainDashboard from './components/MainDashboard.vue'
import TestTigerVNC from './components/TestTigerVNC.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // New main UI
    { path: '/', name: 'Dashboard', component: MainDashboard },

    // Legacy UI preserved under /test
    {
      path: '/test',
      component: LegacyLayout,
      children: [
        { path: '', name: 'TigerVNC_Test', component: TestTigerVNC },
        { path: 'tasks', name: 'LegacyTasks', component: TaskList },
        { path: 'builder', name: 'LegacyBuilder', component: TaskBuilder },
        { path: 'runner/:taskId?', name: 'LegacyRunner', component: AutomationRunner, props: true }
      ]
    }
  ]
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
