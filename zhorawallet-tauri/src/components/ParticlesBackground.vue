<template>
  <div class="fixed inset-0 pointer-events-none overflow-hidden">
    <canvas ref="canvas" class="w-full h-full opacity-20"></canvas>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const canvas = ref<HTMLCanvasElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null
let animationId: number | null = null
let nodes: Node[] = []

class Node {
  x: number
  y: number
  vx: number
  vy: number
  connections: Node[]
  maxConnections: number

  constructor(width: number, height: number) {
    this.x = Math.random() * width
    this.y = Math.random() * height
    this.vx = (Math.random() - 0.5) * 0.8
    this.vy = (Math.random() - 0.5) * 0.8
    this.connections = []
    this.maxConnections = 4
  }

  update(width: number, height: number) {
    this.x += this.vx
    this.y += this.vy

    // Bounce off edges
    if (this.x < 0 || this.x > width) {
      this.vx *= -1
      this.x = Math.max(0, Math.min(width, this.x))
    }
    if (this.y < 0 || this.y > height) {
      this.vy *= -1
      this.y = Math.max(0, Math.min(height, this.y))
    }
  }

  draw(ctx: CanvasRenderingContext2D) {
    // Draw node as a small circle
    ctx.beginPath()
    ctx.arc(this.x, this.y, 3, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)'
    ctx.fill()

    // Draw glow
    const gradient = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, 8)
    gradient.addColorStop(0, 'rgba(255, 255, 255, 0.3)')
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)')
    ctx.beginPath()
    ctx.arc(this.x, this.y, 8, 0, Math.PI * 2)
    ctx.fillStyle = gradient
    ctx.fill()
  }

  drawConnections(ctx: CanvasRenderingContext2D) {
    this.connections.forEach(node => {
      const dx = node.x - this.x
      const dy = node.y - this.y
      const distance = Math.sqrt(dx * dx + dy * dy)

      // Draw line
      ctx.beginPath()
      ctx.moveTo(this.x, this.y)
      ctx.lineTo(node.x, node.y)

      // Gradient line
      const gradient = ctx.createLinearGradient(this.x, this.y, node.x, node.y)
      gradient.addColorStop(0, 'rgba(255, 255, 255, 0.6)')
      gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.3)')
      gradient.addColorStop(1, 'rgba(255, 255, 255, 0.6)')

      ctx.strokeStyle = gradient
      ctx.lineWidth = 1.5
      ctx.stroke()

      // Draw arrow at midpoint
      const midX = (this.x + node.x) / 2
      const midY = (this.y + node.y) / 2
      const angle = Math.atan2(dy, dx)

      const arrowSize = 6
      ctx.save()
      ctx.translate(midX, midY)
      ctx.rotate(angle)

      ctx.beginPath()
      ctx.moveTo(arrowSize, 0)
      ctx.lineTo(-arrowSize / 2, -arrowSize / 2)
      ctx.lineTo(-arrowSize / 2, arrowSize / 2)
      ctx.closePath()
      ctx.fillStyle = 'rgba(255, 255, 255, 0.7)'
      ctx.fill()

      ctx.restore()

      // Pulsing effect on connection
      const pulse = Math.sin(Date.now() / 1000 + distance) * 0.5 + 0.5
      ctx.beginPath()
      ctx.arc(midX, midY, 2 + pulse * 2, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(255, 255, 255, ${0.4 + pulse * 0.3})`
      ctx.fill()
    })
  }
}

function updateConnections() {
  // Clear all connections
  nodes.forEach(node => {
    node.connections = []
  })

  // Create new connections
  nodes.forEach((node, i) => {
    if (node.connections.length >= node.maxConnections) return

    // Find closest nodes
    const distances = nodes
      .map((other, j) => ({
        node: other,
        distance: Math.sqrt(
          Math.pow(other.x - node.x, 2) + Math.pow(other.y - node.y, 2)
        ),
        index: j
      }))
      .filter(d => d.index !== i && d.distance < 250)
      .sort((a, b) => a.distance - b.distance)

    // Connect to closest nodes
    for (const { node: other } of distances) {
      if (node.connections.length >= node.maxConnections) break
      if (other.connections.length >= other.maxConnections) continue
      if (node.connections.includes(other)) continue

      node.connections.push(other)

      if (node.connections.length >= node.maxConnections) break
    }
  })
}

function init() {
  if (!canvas.value) return

  ctx = canvas.value.getContext('2d')
  if (!ctx) return

  canvas.value.width = window.innerWidth
  canvas.value.height = window.innerHeight

  nodes = []
  const nodeCount = Math.floor((canvas.value.width * canvas.value.height) / 25000)

  for (let i = 0; i < nodeCount; i++) {
    nodes.push(new Node(canvas.value.width, canvas.value.height))
  }

  updateConnections()
  animate()
}

let lastConnectionUpdate = 0
function animate() {
  if (!ctx || !canvas.value) return

  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height)

  // Update connections every 100ms
  const now = Date.now()
  if (now - lastConnectionUpdate > 100) {
    updateConnections()
    lastConnectionUpdate = now
  }

  // Update and draw
  nodes.forEach(node => {
    node.update(canvas.value!.width, canvas.value!.height)
  })

  // Draw connections first (behind nodes)
  nodes.forEach(node => {
    node.drawConnections(ctx!)
  })

  // Draw nodes on top
  nodes.forEach(node => {
    node.draw(ctx!)
  })

  animationId = requestAnimationFrame(animate)
}

function handleResize() {
  init()
}

onMounted(() => {
  init()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
  window.removeEventListener('resize', handleResize)
})
</script>
