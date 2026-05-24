async function main() {
  const response = await fetch('./all-models.json')
  if (!response.ok) {
    renderLeaderboardError(`Unable to load leaderboard data (${response.status})`)
    return
  }

  const payload = await response.json()
  const models = payload.models || []
  if (models.length === 0) {
    renderLeaderboardError('No model runs are available yet.')
    return
  }

  renderLeaderboardStats(models)
  renderLeaderboardCards(models)
  renderLeaderboardTable(models)
}

function renderLeaderboardStats(models) {
  const stats = document.getElementById('leaderboard-stats')
  const best = models[0]
  const mostPassing = Math.max(...models.map((model) => model.aggregate_metrics.passed_tools))
  const tiedWinners = models.filter((model) => model.aggregate_metrics.passed_tools === mostPassing).length
  const totalPasses = models.reduce((sum, model) => sum + model.aggregate_metrics.passed_tools, 0)

  const items = [
    ['Models', String(models.length)],
    ['Top model', shortenModelName(best.model)],
    ['Shared top score', `${mostPassing}/6${tiedWinners > 1 ? ` (${tiedWinners} tied)` : ''}`],
    ['Total passing tools', String(totalPasses)],
  ]

  stats.innerHTML = items
    .map(([label, value]) => `<div class="stat-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join('')
}

function renderLeaderboardCards(models) {
  const grid = document.getElementById('leaderboard-grid')
  grid.innerHTML = models
    .map((model, index) => {
      const converged = model.aggregate_metrics.passed_tools
      const exhausted = model.aggregate_metrics.tool_count - converged
      const passRate = ((model.aggregate_metrics.passed_tools / model.aggregate_metrics.tool_count) * 100).toFixed(1)
      return `
        <article class="leaderboard-card ${index === 0 ? 'top' : ''}">
          <div class="leaderboard-card-head">
            <span class="leaderboard-rank">#${index + 1}</span>
            <h3>${escapeHtml(shortenModelName(model.model))}</h3>
          </div>
          <div class="leaderboard-metrics">
            <div class="leaderboard-metric">
              <span>Converged</span>
              <strong>${converged}/${model.aggregate_metrics.tool_count}</strong>
            </div>
            <div class="leaderboard-metric">
              <span>Convergence rate</span>
              <strong>${passRate}%</strong>
            </div>
            <div class="leaderboard-metric">
              <span>Avg iterations</span>
              <strong>${escapeHtml(String(model.aggregate_metrics.average_iterations))}</strong>
            </div>
            <div class="leaderboard-metric">
              <span>Budget exhausted</span>
              <strong>${exhausted}</strong>
            </div>
          </div>
          <a class="button secondary leaderboard-link" href="./trajectories.html?model=${encodeURIComponent(model.model_key)}">
            Open trajectories
          </a>
        </article>
      `
    })
    .join('')
}

function renderLeaderboardTable(models) {
  const tbody = document.querySelector('#leaderboard-table tbody')
  tbody.innerHTML = models
    .map((model) => {
      const toolPills = model.tools
        .map(
          (tool) =>
            `<span class="tool-pill ${tool.passed ? 'success' : 'failure'}">${escapeHtml(tool.tool_name)} · ${tool.passed ? 'P' : 'F'}</span>`
        )
        .join('')

      return `
        <tr>
          <td>${escapeHtml(shortenModelName(model.model))}</td>
          <td>${model.aggregate_metrics.passed_tools}/${model.aggregate_metrics.tool_count}</td>
          <td>${escapeHtml(String(model.aggregate_metrics.average_iterations))}</td>
          <td><div class="tool-pill-row">${toolPills}</div></td>
        </tr>
      `
    })
    .join('')
}

function renderLeaderboardError(message) {
  const stats = document.getElementById('leaderboard-stats')
  stats.innerHTML = `<div class="stat-card"><span>Error</span><strong>${escapeHtml(message)}</strong></div>`
  document.getElementById('leaderboard-grid').innerHTML = `<div class="trajectory-empty">${escapeHtml(message)}</div>`
}

function shortenModelName(model) {
  return String(model).replace(/^openai\//, '')
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

main().catch((error) => {
  renderLeaderboardError(error instanceof Error ? error.message : 'Unknown error')
})
