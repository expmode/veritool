async function main() {
  const response = await fetch('./all-models.json')
  if (!response.ok) {
    renderError(`Unable to load model trajectories (${response.status})`)
    return
  }

  const payload = await response.json()
  if (!payload.models || payload.models.length === 0) {
    renderError('No model trajectories are available yet.')
    return
  }

  const requestedModel = new URLSearchParams(window.location.search).get('model')
  const initialModel = payload.models.find((model) => model.model_key === requestedModel) ?? payload.models[0]
  renderModelExplorer(payload.models, initialModel.model_key)
}

function renderModelExplorer(models, activeModelKey) {
  const activeModel = models.find((model) => model.model_key === activeModelKey) ?? models[0]
  renderModelPicker(models, activeModel.model_key)
  renderStats(activeModel)
  renderToolList(activeModel)
  if (activeModel.tools.length > 0) {
    renderToolDetail(activeModel, activeModel.tools[0])
  } else {
    renderError(`No tool trajectories recorded for ${activeModel.model}.`)
  }
}

function renderModelPicker(models, activeModelKey) {
  const picker = document.getElementById('model-picker')
  picker.innerHTML = ''

  models.forEach((model) => {
    const button = document.createElement('button')
    button.type = 'button'
    button.className = `model-chip${model.model_key === activeModelKey ? ' active' : ''}`
    button.textContent = shortenModelName(model.model)
    button.title = model.model
    button.addEventListener('click', () => {
      const url = new URL(window.location.href)
      url.searchParams.set('model', model.model_key)
      window.history.replaceState({}, '', url)
      renderModelExplorer(models, model.model_key)
    })
    picker.appendChild(button)
  })
}

function renderStats(bundle) {
  const stats = document.getElementById('trajectory-stats')
  stats.innerHTML = ''
  const items = [
    ['Model', bundle.model],
    ['Converged tools', `${bundle.aggregate_metrics.passed_tools}/${bundle.aggregate_metrics.tool_count}`],
    ['Iterations', String(bundle.aggregate_metrics.total_iterations)],
    ['Average / tool', String(bundle.aggregate_metrics.average_iterations)],
  ]
  for (const [label, value] of items) {
    const card = document.createElement('div')
    card.className = 'stat-card'
    card.innerHTML = `<span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong>`
    stats.appendChild(card)
  }
}

function renderToolList(bundle) {
  const list = document.getElementById('tool-list')
  list.innerHTML = ''

  bundle.tools.forEach((tool, index) => {
    const button = document.createElement('button')
    button.type = 'button'
    button.className = `trajectory-tool ${tool.passed ? 'success' : 'failure'}${index === 0 ? ' active' : ''}`
    button.innerHTML = `
      <span class="trajectory-tool-name">${escapeHtml(tool.tool_name)}</span>
      <span class="trajectory-tool-meta">${tool.passed ? 'Converged' : 'Budget exhausted'} · ${tool.iterations.length} iterations</span>
    `
    button.addEventListener('click', () => {
      for (const sibling of list.querySelectorAll('.trajectory-tool')) {
        sibling.classList.remove('active')
      }
      button.classList.add('active')
      renderToolDetail(bundle, tool)
    })
    list.appendChild(button)
  })
}

function renderToolDetail(bundle, tool) {
  const detail = document.getElementById('trajectory-detail')
  const acceptedCode = tool.accepted_code
    ? `<details class="trajectory-detail-block"><summary>Accepted code</summary><pre>${escapeHtml(tool.accepted_code)}</pre></details>`
    : `<div class="trajectory-empty">No accepted candidate within the iteration budget.</div>`

  detail.innerHTML = `
    <article class="trajectory-header-card">
      <div>
        <p class="section-kicker">Selected tool / ${escapeHtml(shortenModelName(bundle.model))}</p>
        <h3>${escapeHtml(tool.tool_name)}</h3>
      </div>
      <div class="trajectory-summary-pill ${tool.passed ? 'success' : 'failure'}">
        ${tool.passed ? 'Converged' : 'Budget exhausted'}
      </div>
    </article>
    <div class="trajectory-meta-grid">
      <div class="trajectory-meta-card"><span>Function</span><strong>${escapeHtml(tool.function_name)}</strong></div>
      <div class="trajectory-meta-card"><span>Iterations</span><strong>${tool.iterations.length}</strong></div>
    </div>
    ${acceptedCode}
    <div class="trajectory-iterations">
      ${tool.iterations.map(renderIteration).join('')}
    </div>
  `
}

function renderIteration(iteration) {
  const counterexampleData = iteration.counterexample
  const counterexampleHtml = counterexampleData
    ? `<details class="trajectory-detail-block" open>
         <summary>Verifier feedback</summary>
         <div class="trajectory-counterexample">
           <p><strong>${escapeHtml(counterexampleData.title)}</strong></p>
           <p>${escapeHtml(counterexampleData.description)}</p>
           <pre>${escapeHtml(JSON.stringify(counterexampleData.payload, null, 2))}</pre>
         </div>
       </details>`
    : `<div class="trajectory-empty">No counterexample; this iteration passed.</div>`

  const prompt = iteration.prompt
    ? `<details class="trajectory-detail-block" open>
         <summary>Prompt sent to model</summary>
         <pre class="prompt-block">${formatPrompt(iteration.prompt)}</pre>
       </details>`
    : `<div class="trajectory-empty">Prompt not available in cache.</div>`

  const rawResponse = iteration.raw_response
    ? `<details class="trajectory-detail-block">
         <summary>Raw model response</summary>
         <pre>${escapeHtml(iteration.raw_response)}</pre>
       </details>`
    : `<div class="trajectory-empty">Raw response not available in cache.</div>`

  const code = iteration.code
    ? `<details class="trajectory-detail-block">
         <summary>Extracted code</summary>
         <pre>${escapeHtml(iteration.code)}</pre>
       </details>`
    : ''

  return `
    <article class="iteration-card ${iteration.passed ? 'success' : 'failure'}">
      <div class="iteration-head">
        <div>
          <p class="section-kicker">Iteration ${iteration.iteration}</p>
          <h4>${escapeHtml(iteration.summary)}</h4>
        </div>
        <div class="iteration-badge ${iteration.passed ? 'success' : 'failure'}">
          ${iteration.passed ? 'Pass' : 'Fail'}
        </div>
      </div>
      <p class="iteration-evidence">Evidence level: ${escapeHtml(iteration.evidence_level)}</p>
      ${counterexampleHtml}
      ${prompt}
      ${rawResponse}
      ${code}
    </article>
  `
}

function renderError(message) {
  document.getElementById('trajectory-detail').innerHTML = `<div class="trajectory-empty">${escapeHtml(message)}</div>`
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function formatPrompt(prompt) {
  const lines = String(prompt).split('\n')
  let inCounterexampleSection = false

  return lines
    .map((line) => {
      const escaped = escapeHtml(line)
      if (line.startsWith('Counterexamples from previous failed attempts:')) {
        inCounterexampleSection = true
        return `<span class="prompt-counterexample-heading">${escaped}</span>`
      }
      if (inCounterexampleSection && (line.startsWith('- ') || line.startsWith('  Payload:'))) {
        return `<span class="prompt-counterexample-line">${escaped}</span>`
      }
      return escaped
    })
    .join('\n')
}

function shortenModelName(model) {
  return String(model).replace(/^openai\//, '')
}

main().catch((error) => {
  renderError(error instanceof Error ? error.message : 'Unknown error')
})
