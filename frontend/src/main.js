import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

// Import components
import Home from './components/Home.vue'
import TaskBuilder from './components/TaskBuilder.vue'
import AutomationRunner from './components/AutomationRunner.vue'
import TaskList from './components/TaskList.vue'

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Home', component: Home },
    { path: '/tasks', name: 'Tasks', component: TaskList },
    { path: '/builder', name: 'Builder', component: TaskBuilder },
    { path: '/runner/:taskId?', name: 'Runner', component: AutomationRunner, props: true }
  ]
})

// Create app
const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
