<template>
  <div class="p-4 space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">Multi Session Test</h1>
      <div class="flex items-center gap-2">
        <button
          class="px-3 py-1.5 rounded bg-emerald-600 text-white hover:bg-emerald-700 text-sm"
          @click="startAll"
        >
          Start All
        </button>
        <button
          class="px-3 py-1.5 rounded bg-red-600 text-white hover:bg-red-700 text-sm"
          @click="closeAll"
        >
          Close All
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Google -->
      <div class="bg-white border rounded-lg overflow-hidden">
        <div class="px-3 py-2 border-b flex items-center justify-between">
          <div class="font-medium text-sm">Google Keep</div>
          <div class="text-xs text-gray-500">{{ statuses.google }}</div>
        </div>
        <div class="h-[360px] bg-black">
          <MultiSessionBrowserViewport
            v-if="mount.google"
            ref="refGoogle"
            :user-id="ids.google"
            :task-id="null"
            :is-running="false"
            @session-created="(s) => onSessionCreated('google', s)"
            @session-destroyed="() => (statuses.google = 'closed')"
            @connection-changed="(st) => (statuses.google = st)"
          />
          <div v-else class="h-full flex items-center justify-center text-gray-400 text-sm">
            Click "Start All" to begin
          </div>
        </div>
      </div>

      <!-- Gmail -->
      <div class="bg-white border rounded-lg overflow-hidden">
        <div class="px-3 py-2 border-b flex items-center justify-between">
          <div class="font-medium text-sm">Outlook Mail</div>
          <div class="text-xs text-gray-500">{{ statuses.gmail }}</div>
        </div>
        <div class="h-[360px] bg-black">
          <MultiSessionBrowserViewport
            v-if="mount.gmail"
            ref="refGmail"
            :user-id="ids.gmail"
            :task-id="null"
            :is-running="false"
            @session-created="(s) => onSessionCreated('gmail', s)"
            @session-destroyed="() => (statuses.gmail = 'closed')"
            @connection-changed="(st) => (statuses.gmail = st)"
          />
          <div v-else class="h-full flex items-center justify-center text-gray-400 text-sm">
            Click "Start All" to begin
          </div>
        </div>
      </div>

      <!-- YouTube -->
      <div class="bg-white border rounded-lg overflow-hidden">
        <div class="px-3 py-2 border-b flex items-center justify-between">
          <div class="font-medium text-sm">Fast.com</div>
          <div class="text-xs text-gray-500">{{ statuses.youtube }}</div>
        </div>
        <div class="h-[360px] bg-black">
          <MultiSessionBrowserViewport
            v-if="mount.youtube"
            ref="refYouTube"
            :user-id="ids.youtube"
            :task-id="null"
            :is-running="false"
            @session-created="(s) => onSessionCreated('youtube', s)"
            @session-destroyed="() => (statuses.youtube = 'closed')"
            @connection-changed="(st) => (statuses.youtube = st)"
          />
          <div v-else class="h-full flex items-center justify-center text-gray-400 text-sm">
            Click "Start All" to begin
          </div>
        </div>
      </div>

      <!-- Outlook -->
      <div class="bg-white border rounded-lg overflow-hidden">
        <div class="px-3 py-2 border-b flex items-center justify-between">
          <div class="font-medium text-sm">Rhobots</div>
          <div class="text-xs text-gray-500">{{ statuses.outlook }}</div>
        </div>
        <div class="h-[360px] bg-black">
          <MultiSessionBrowserViewport
            v-if="mount.outlook"
            ref="refOutlook"
            :user-id="ids.outlook"
            :task-id="null"
            :is-running="false"
            @session-created="(s) => onSessionCreated('outlook', s)"
            @session-destroyed="() => (statuses.outlook = 'closed')"
            @connection-changed="(st) => (statuses.outlook = st)"
          />
          <div v-else class="h-full flex items-center justify-center text-gray-400 text-sm">
            Click "Start All" to begin
          </div>
        </div>
      </div>
    </div>

    <div class="text-xs text-gray-500">
      Sessions auto-launch target URLs after connection. Use "Close All" to free resources.
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import axios from 'axios'
import MultiSessionBrowserViewport from './MultiSessionBrowserViewport.vue'

// Deterministic user ids per pane (namespace to avoid collisions)
const ids = {
  google: 'multi-google',
  gmail: 'multi-gmail',
  youtube: 'multi-youtube',
  outlook: 'multi-outlook'
}

const urls = {
  google: 'https://www.google.com/keep/',
  gmail: 'https://outlook.office365.com/mail/',
  youtube: 'https://fast.com/',
  outlook: 'https://www.rhobots.ai/'
}

const mount = reactive({
  google: false,
  gmail: false,
  youtube: false,
  outlook: false
})

const statuses = reactive({
  google: 'idle',
  gmail: 'idle',
  youtube: 'idle',
  outlook: 'idle'
})

// refs to child components to call cleanup()
const refGoogle = ref(null)
const refGmail = ref(null)
const refYouTube = ref(null)
const refOutlook = ref(null)

const onSessionCreated = async (key, session) => {
  try {
    statuses[key] = 'launching'
    await axios.post(`/api/test-browser/session/${session.session_id}`, {
      url: urls[key]
    })
    statuses[key] = 'launched'
  } catch (e) {
    statuses[key] = 'error'
    console.error(`Failed launching ${key}:`, e)
  }
}

const startAll = () => {
  mount.google = true
  mount.gmail = true
  mount.youtube = true
  mount.outlook = true
  statuses.google = 'starting'
  statuses.gmail = 'starting'
  statuses.youtube = 'starting'
  statuses.outlook = 'starting'
}

const closeAll = async () => {
  const clean = async (r) => {
    try {
      if (r?.value?.cleanup) {
        await r.value.cleanup()
      }
    } catch {}
  }
  await Promise.all([
    clean(refGoogle),
    clean(refGmail),
    clean(refYouTube),
    clean(refOutlook)
  ])
  mount.google = false
  mount.gmail = false
  mount.youtube = false
  mount.outlook = false
  statuses.google = 'closed'
  statuses.gmail = 'closed'
  statuses.youtube = 'closed'
  statuses.outlook = 'closed'
}
</script>
