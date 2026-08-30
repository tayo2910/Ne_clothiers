<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useCustomerStore } from '@/stores/customers'
import client from '@/api/client'
import StatusBadge from '@/components/StatusBadge.vue'
import logo from '@/assets/ne.png'
import { Bar, Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend)

const auth = useAuthStore()
const customerStore = useCustomerStore()

const loginForm = reactive({ username: '', password: '' })
const loginError = ref('')

const stats = ref({
  total_customers: 0,
  active_orders: 0,
  due_this_week: 0,
  avg_order_value: 0,
  total_collected: 0,
})

const alerts = ref({ overdue: [], due_this_week: [] })

const outfitChartData = ref(null)
const statusChartData = ref(null)
const revenueChartData = ref(null)

const searchTable = ref('')
const outfitFilter = ref('')
const editingOrder = ref(null)
const editForm = reactive({
  name: '',
  phone: '',
  email: '',
  outfit_type: '',
  status: '',
  amount: '',
})

const statuses = ['Pending', 'In Progress', 'Ready', 'Delivered']
const outfitTypes = ['agbada', 'senator', 'suit', 'kaftan']

const filteredCustomers = computed(() => {
  let list = customerStore.customers
  if (searchTable.value.trim()) {
    const q = searchTable.value.trim().toLowerCase()
    list = list.filter(
      (c) =>
        (c.name && c.name.toLowerCase().includes(q)) ||
        (c.phone && c.phone.includes(q)) ||
        (c.id && String(c.id).includes(q))
    )
  }
  if (outfitFilter.value) {
    list = list.filter((c) => c.outfit_type === outfitFilter.value)
  }
  return list
})

function chartOptions(title) {
  return {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: true, text: title, color: '#93C5FD' },
    },
    scales: {
      x: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
    },
  }
}

async function handleLogin() {
  try {
    loginError.value = ''
    await auth.login(loginForm.username, loginForm.password)
    await loadDashboard()
  } catch {
    loginError.value = 'Invalid credentials'
  }
}

async function loadDashboard() {
  try {
    const [statsRes, alertsRes, ordersRes] = await Promise.all([
      client.get('/admin/stats'),
      client.get('/admin/alerts'),
      client.get('/orders'),
    ])
    stats.value = statsRes.data
    alerts.value = alertsRes.data
    const orders = ordersRes.data
    customerStore.customers = orders

    const outfitCounts = {}
    const statusCounts = {}
    const revenueByDate = {}

    orders.forEach((o) => {
      const outfit = o.outfit_type || 'unknown'
      outfitCounts[outfit] = (outfitCounts[outfit] || 0) + 1
      const st = o.status || 'Pending'
      statusCounts[st] = (statusCounts[st] || 0) + 1
      if (o.amount) {
        const date = o.created_at ? new Date(o.created_at).toLocaleDateString() : 'Unknown'
        revenueByDate[date] = (revenueByDate[date] || 0) + Number(o.amount)
      }
    })

    outfitChartData.value = {
      labels: Object.keys(outfitCounts),
      datasets: [
        {
          label: 'Orders',
          data: Object.values(outfitCounts),
          backgroundColor: ['#2563EB', '#10B981', '#F59E0B', '#EF4444'],
          borderRadius: 6,
        },
      ],
    }

    statusChartData.value = {
      labels: Object.keys(statusCounts),
      datasets: [
        {
          label: 'Orders',
          data: Object.values(statusCounts),
          backgroundColor: ['#F59E0B', '#2563EB', '#10B981', '#94a3b8'],
          borderRadius: 6,
        },
      ],
    }

    const sortedDates = Object.keys(revenueByDate).sort((a, b) => new Date(a) - new Date(b))
    revenueChartData.value = {
      labels: sortedDates,
      datasets: [
        {
          label: 'Revenue',
          data: sortedDates.map((d) => revenueByDate[d]),
          borderColor: '#10B981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#10B981',
        },
      ],
    }
  } catch (err) {
    console.error('Failed to load dashboard', err)
  }
}

function startEdit(order) {
  editingOrder.value = order.id
  editForm.name = order.name || ''
  editForm.phone = order.phone || ''
  editForm.email = order.email || ''
  editForm.outfit_type = order.outfit_type || ''
  editForm.status = order.status || 'Pending'
  editForm.amount = order.amount ? String(order.amount) : ''
}

function cancelEdit() {
  editingOrder.value = null
}

async function saveEdit(order) {
  try {
    const data = { ...editForm }
    if (data.amount) data.amount = Number(data.amount)
    const res = await client.patch(`/orders/${order.id}`, data)
    Object.assign(order, res.data)
    editingOrder.value = null
  } catch {
    alert('Failed to update order')
  }
}

async function deleteOrder(order) {
  if (!confirm('Delete this order permanently?')) return
  try {
    await client.delete(`/orders/${order.id}`)
    customerStore.customers = customerStore.customers.filter((c) => c.id !== order.id)
  } catch {
    alert('Failed to delete order')
  }
}

async function updateStatus(order, newStatus) {
  if (!newStatus) return
  try {
    const res = await client.patch(`/orders/${order.id}`, { status: newStatus })
    Object.assign(order, res.data)
    await loadDashboard()
  } catch {
    alert('Failed to update status')
  }
}

function downloadPDF(order) {
  window.open(`/api/orders/${order.id}/receipt`, '_blank')
}

async function exportCSV() {
  try {
    const res = await client.get('/admin/export/csv', { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = 'orders.csv'
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    alert('CSV export failed')
  }
}

async function exportExcel() {
  try {
    const res = await client.get('/admin/export/excel', { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = 'orders.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    alert('Excel export failed')
  }
}

onMounted(() => {
  if (auth.isAuthenticated) loadDashboard()
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <div v-if="!auth.isAuthenticated" class="max-w-sm mx-auto pt-16">
      <div class="bg-card border border-white/5 rounded-xl p-8">
        <div class="text-center mb-6">
          <img :src="logo" alt="NE Clothiers logo" class="w-14 h-14 mx-auto mb-3 rounded-xl object-contain" />
          <h2 class="text-xl font-bold text-white">Admin Login</h2>
          <p class="text-sm text-slate-400 mt-1">Sign in to access the dashboard</p>
        </div>
        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1.5">Username</label>
            <input
              v-model="loginForm.username"
              type="text"
              required
              class="w-full bg-slate-800 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
            <input
              v-model="loginForm.password"
              type="password"
              required
              class="w-full bg-slate-800 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors"
            />
          </div>
          <p v-if="loginError" class="text-red-400 text-sm text-center">{{ loginError }}</p>
          <button
            type="submit"
            class="w-full py-2.5 rounded-lg bg-primary hover:bg-primary-light text-white font-medium transition-all duration-200 cursor-pointer"
          >Sign In</button>
        </form>
      </div>
    </div>

    <div v-else>
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-3xl font-bold text-white">Admin Dashboard</h1>
          <p class="text-slate-400 mt-1">Overview of your tailoring business</p>
        </div>
        <div class="flex space-x-2">
          <button
            @click="exportCSV"
            class="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-slate-300 hover:bg-white/10 transition-colors cursor-pointer"
          >CSV</button>
          <button
            @click="exportExcel"
            class="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-slate-300 hover:bg-white/10 transition-colors cursor-pointer"
          >Excel</button>
        </div>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <div class="bg-card border border-white/5 rounded-xl p-4">
          <p class="text-xs text-slate-400 uppercase tracking-wider">Total Customers</p>
          <p class="text-2xl font-bold text-white mt-1">{{ stats.total_customers }}</p>
        </div>
        <div class="bg-card border border-white/5 rounded-xl p-4">
          <p class="text-xs text-slate-400 uppercase tracking-wider">Active Orders</p>
          <p class="text-2xl font-bold text-primary-light mt-1">{{ stats.active_orders }}</p>
        </div>
        <div class="bg-card border border-white/5 rounded-xl p-4">
          <p class="text-xs text-slate-400 uppercase tracking-wider">Due This Week</p>
          <p class="text-2xl font-bold text-gold mt-1">{{ stats.due_this_week }}</p>
        </div>
        <div class="bg-card border border-white/5 rounded-xl p-4">
          <p class="text-xs text-slate-400 uppercase tracking-wider">Avg Order Value</p>
          <p class="text-2xl font-bold text-green mt-1">₦{{ Number(stats.avg_order_value || 0).toLocaleString() }}</p>
        </div>
        <div class="bg-card border border-white/5 rounded-xl p-4">
          <p class="text-xs text-slate-400 uppercase tracking-wider">Total Collected</p>
          <p class="text-2xl font-bold text-green mt-1">₦{{ Number(stats.total_collected || 0).toLocaleString() }}</p>
        </div>
      </div>

      <div
        v-if="(alerts.overdue && alerts.overdue.length > 0) || (alerts.due_this_week && alerts.due_this_week.length > 0)"
        class="mb-8 space-y-2"
      >
        <div
          v-for="alert in (alerts.overdue || [])"
          :key="alert.id"
          class="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 flex items-center justify-between"
        >
          <div class="flex items-center space-x-2">
            <span class="text-red-400 text-sm">⚠</span>
            <span class="text-sm text-red-300">Order #{{ alert.id }} overdue - {{ alert.name }}</span>
          </div>
          <StatusBadge :status="alert.status" />
        </div>
        <div
          v-for="alert in (alerts.due_this_week || [])"
          :key="alert.id"
          class="bg-yellow-500/10 border border-yellow-500/20 rounded-xl px-4 py-3 flex items-center justify-between"
        >
          <div class="flex items-center space-x-2">
            <span class="text-yellow-400 text-sm">⏰</span>
            <span class="text-sm text-yellow-300">Order #{{ alert.id }} due this week - {{ alert.name }}</span>
          </div>
          <StatusBadge :status="alert.status" />
        </div>
      </div>

      <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div class="bg-card border border-white/5 rounded-xl p-4">
          <Bar v-if="outfitChartData" :data="outfitChartData" :options="chartOptions('Orders by Outfit')" />
        </div>
        <div class="bg-card border border-white/5 rounded-xl p-4">
          <Bar v-if="statusChartData" :data="statusChartData" :options="chartOptions('Orders by Status')" />
        </div>
        <div class="bg-card border border-white/5 rounded-xl p-4 md:col-span-2 lg:col-span-1">
          <Line v-if="revenueChartData" :data="revenueChartData" :options="chartOptions('Revenue Over Time')" />
        </div>
      </div>

      <div class="bg-card border border-white/5 rounded-xl overflow-hidden">
        <div class="p-4 border-b border-white/5">
          <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div class="flex items-center space-x-2">
              <input
                v-model="searchTable"
                type="text"
                placeholder="Search records..."
                class="bg-slate-800 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-primary w-48"
              />
              <select
                v-model="outfitFilter"
                class="bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-primary"
              >
                <option value="">All Outfits</option>
                <option v-for="ot in outfitTypes" :key="ot" :value="ot" class="capitalize">{{ ot }}</option>
              </select>
            </div>
            <span class="text-xs text-slate-500">{{ filteredCustomers.length }} records</span>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-white/5 text-slate-400 text-xs uppercase tracking-wider">
                <th class="text-left px-4 py-3 font-medium">ID</th>
                <th class="text-left px-4 py-3 font-medium">Name</th>
                <th class="text-left px-4 py-3 font-medium">Phone</th>
                <th class="text-left px-4 py-3 font-medium">Outfit</th>
                <th class="text-left px-4 py-3 font-medium">Status</th>
                <th class="text-left px-4 py-3 font-medium">Amount</th>
                <th class="text-left px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="order in filteredCustomers"
                :key="order.id"
                class="border-b border-white/5 hover:bg-white/5 transition-colors"
              >
                <td class="px-4 py-3 font-mono text-primary-light">#{{ order.id }}</td>

                <td v-if="editingOrder === order.id" class="px-4 py-3">
                  <input
                    v-model="editForm.name"
                    class="w-full bg-slate-800 border border-white/10 rounded px-2 py-1 text-white text-xs"
                  />
                </td>
                <td v-else class="px-4 py-3 text-white">{{ order.name }}</td>

                <td v-if="editingOrder === order.id" class="px-4 py-3">
                  <input
                    v-model="editForm.phone"
                    class="w-full bg-slate-800 border border-white/10 rounded px-2 py-1 text-white text-xs"
                  />
                </td>
                <td v-else class="px-4 py-3 text-slate-300">{{ order.phone }}</td>

                <td v-if="editingOrder === order.id" class="px-4 py-3">
                  <select
                    v-model="editForm.outfit_type"
                    class="bg-slate-800 border border-white/10 rounded px-2 py-1 text-white text-xs capitalize"
                  >
                    <option v-for="ot in outfitTypes" :key="ot" :value="ot">{{ ot }}</option>
                  </select>
                </td>
                <td v-else class="px-4 py-3 capitalize text-slate-300">{{ order.outfit_type }}</td>

                <td v-if="editingOrder === order.id" class="px-4 py-3">
                  <select
                    v-model="editForm.status"
                    class="bg-slate-800 border border-white/10 rounded px-2 py-1 text-white text-xs"
                  >
                    <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
                  </select>
                </td>
                <td v-else class="px-4 py-3">
                  <StatusBadge :status="order.status" />
                </td>

                <td v-if="editingOrder === order.id" class="px-4 py-3">
                  <input
                    v-model="editForm.amount"
                    type="number"
                    step="0.01"
                    class="w-24 bg-slate-800 border border-white/10 rounded px-2 py-1 text-white text-xs"
                  />
                </td>
                <td v-else class="px-4 py-3 text-green font-medium">
                  ₦{{ Number(order.amount || 0).toLocaleString() }}
                </td>

                <td class="px-4 py-3">
                  <div class="flex items-center space-x-1 flex-wrap gap-1">
                    <button
                      v-if="editingOrder === order.id"
                      @click="saveEdit(order)"
                      class="px-2 py-1 text-xs rounded bg-green text-white hover:bg-green/80 cursor-pointer"
                    >Save</button>
                    <button
                      v-if="editingOrder === order.id"
                      @click="cancelEdit"
                      class="px-2 py-1 text-xs rounded bg-slate-700 text-slate-300 hover:bg-slate-600 cursor-pointer"
                    >Cancel</button>
                    <button
                      v-if="editingOrder !== order.id"
                      @click="startEdit(order)"
                      class="px-2 py-1 text-xs rounded bg-white/10 text-slate-300 hover:bg-white/20 cursor-pointer"
                    >Edit</button>
                    <button
                      @click="deleteOrder(order)"
                      class="px-2 py-1 text-xs rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 cursor-pointer"
                    >Del</button>
                    <button
                      @click="downloadPDF(order)"
                      class="px-2 py-1 text-xs rounded bg-primary/20 text-primary-light hover:bg-primary/30 cursor-pointer"
                    >PDF</button>
                    <select
                      @change="updateStatus(order, $event.target.value)"
                      class="bg-slate-800 border border-white/10 rounded px-1.5 py-1 text-white text-xs"
                    >
                      <option value="" disabled selected>Status</option>
                      <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
                    </select>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
