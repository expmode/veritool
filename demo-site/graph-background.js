const canvas = document.getElementById('graph-background')

if (canvas instanceof HTMLCanvasElement) {
  const context = canvas.getContext('2d')
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  if (context) {
    const state = {
      width: 0,
      height: 0,
      nodes: [],
      rafId: 0,
      density: 0,
    }

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      state.width = window.innerWidth
      state.height = window.innerHeight
      canvas.width = Math.floor(state.width * dpr)
      canvas.height = Math.floor(state.height * dpr)
      canvas.style.width = `${state.width}px`
      canvas.style.height = `${state.height}px`
      context.setTransform(dpr, 0, 0, dpr, 0, 0)

      const targetCount = Math.max(40, Math.min(86, Math.floor((state.width * state.height) / 28000)))
      state.density = targetCount
      state.nodes = Array.from({ length: targetCount }, createNode)
    }

    function createNode() {
      const angle = Math.random() * Math.PI * 2
      const speed = reduceMotion ? 0 : 0.12 + Math.random() * 0.22
      return {
        x: Math.random() * state.width,
        y: Math.random() * state.height,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        radius: 0.9 + Math.random() * 1.8,
        phase: Math.random() * Math.PI * 2,
      }
    }

    function step() {
      context.clearRect(0, 0, state.width, state.height)

      for (const node of state.nodes) {
        node.phase += 0.008
        if (!reduceMotion) {
          node.x += node.vx
          node.y += node.vy

          if (node.x < -30 || node.x > state.width + 30) {
            node.vx *= -1
          }
          if (node.y < -30 || node.y > state.height + 30) {
            node.vy *= -1
          }
        }
      }

      drawConnections()
      drawNodes()
      state.rafId = window.requestAnimationFrame(step)
    }

    function drawConnections() {
      const maxDistance = Math.min(250, Math.max(140, state.width * 0.17))
      for (let i = 0; i < state.nodes.length; i += 1) {
        const a = state.nodes[i]
        for (let j = i + 1; j < state.nodes.length; j += 1) {
          const b = state.nodes[j]
          const dx = a.x - b.x
          const dy = a.y - b.y
          const distance = Math.hypot(dx, dy)
          if (distance > maxDistance) {
            continue
          }

          const strength = 1 - distance / maxDistance
          const pulse = 0.65 + 0.35 * Math.sin(a.phase + b.phase)
          context.beginPath()
          context.moveTo(a.x, a.y)
          context.lineTo(b.x, b.y)
          context.strokeStyle = `rgba(92, 78, 182, ${0.07 + strength * 0.18 * pulse})`
          context.lineWidth = 0.7 + strength * 0.95
          context.stroke()
        }
      }
    }

    function drawNodes() {
      for (const node of state.nodes) {
        const glow = 0.45 + 0.25 * Math.sin(node.phase)
        context.beginPath()
        context.arc(node.x, node.y, node.radius, 0, Math.PI * 2)
        context.fillStyle = `rgba(130, 92, 42, ${0.34 + glow * 0.24})`
        context.fill()

        context.beginPath()
        context.arc(node.x, node.y, node.radius * 0.52, 0, Math.PI * 2)
        context.fillStyle = `rgba(44, 122, 114, ${0.28 + glow * 0.2})`
        context.fill()
      }
    }

    resize()
    step()

    window.addEventListener('resize', resize)
    window.addEventListener('pagehide', () => {
      window.cancelAnimationFrame(state.rafId)
    })
  }
}
