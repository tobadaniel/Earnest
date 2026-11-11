import './style.css'
import {
  connectWallet, payNim, signMessage, stakeNim, shortAddress, isDemo, type Wallet,
} from './nimiq'
import {
  GENESIS, hashReceipt, verifyChain, encodeChain, decodeChain, receiptText, type Receipt,
} from './chain'

// ———————————————————————— Types & state ————————————————————————

interface Job {
  id: string
  title: string
  detail: string
  amount: number
  poster: string
  worker: string | null
  phase: 0 | 1 | 2 | 3 // open, claimed, paid, sealed
  posterSigned?: boolean
  tx?: string
  draft?: Omit<Receipt, 'hash'>
}

interface State {
  name: string
  jobs: Job[]
  receipts: Receipt[]
  staked: number
  stakerCreated: boolean
  stakeTxs: string[]
}

const KEY = 'earnest-v1'
let wallet: Wallet | null = null
let state: State
let tab: 'passport' | 'jobs' | 'grow' = 'passport'
let publicView: { name: string; receipts: Receipt[] } | null = null
let linkError = false
let lastCheck: string | null = null
let chainVerified = false

function save() { localStorage.setItem(KEY, JSON.stringify(state)) }
function load(): State | null {
  try { const raw = localStorage.getItem(KEY); return raw ? (JSON.parse(raw) as State) : null } catch { return null }
}
function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!))
}
function fmt(n: number): string { return n.toLocaleString('en-US', { maximumFractionDigits: 2 }) }
function initials(name: string): string {
  return name.split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase() || 'E'
}
function tip(): string { return state.receipts.length ? state.receipts[state.receipts.length - 1].hash : GENESIS }

async function seedReceipts(name: string): Promise<Receipt[]> {
  const seeds: Array<Omit<Receipt, 'hash' | 'prev'>> = [
    { id: 'seed-1', job: 'Landing page for a coffee brand', poster: 'Adaeze — Design Studio', worker: name, amount: 450, tx: 'demo-tx-9f2c41aa', at: '2026-10-28', posterSig: 'demo-signature', workerSig: 'demo-signature' },
    { id: 'seed-2', job: 'Data cleanup across 3 spreadsheets', poster: 'HiiT Alumni Group', worker: name, amount: 275, tx: 'demo-tx-51bd07e3', at: '2026-11-03', posterSig: 'demo-signature', workerSig: 'demo-signature' },
  ]
  const out: Receipt[] = []
  let prev = GENESIS
  for (const s of seeds) {
    const base = { ...s, prev }
    const hash = await hashReceipt(base)
    out.push({ ...base, hash })
    prev = hash
  }
  return out
}

function seedJobs(): Job[] {
  return [
    { id: 'job-1', title: 'Logo + brand kit for a coffee startup', detail: 'Wordmark, colour palette and a one-page brand sheet. Two revision rounds included.', amount: 250, poster: 'Adaeze — Design Studio', worker: null, phase: 0 },
    { id: 'job-2', title: 'Translate a product page, English to French', detail: 'About 900 words, friendly tone, delivery within 24 hours of claiming.', amount: 120, poster: 'Marco — NimShop', worker: null, phase: 0 },
    { id: 'job-3', title: 'Weekend photography assistant', detail: 'Product shoot, 12 items, same-day basic edits. Portfolio link appreciated.', amount: 400, poster: 'Lagos Food Co.', worker: null, phase: 0 },
  ]
}

// ———————————————————————— Actions ————————————————————————

async function act(action: string, id: string, btn: HTMLButtonElement) {
  const job = state.jobs.find((j) => j.id === id)
  try {
    if (action === 'claim' && job) {
      job.worker = state.name
      job.phase = 1
      toast(`You claimed “${job.title}”`)
    }
    if (action === 'pay' && job) {
      btn.disabled = true; btn.textContent = 'Waiting for wallet approval…'
      // Poster pays the worker. On the poster's own device (job link) this is
      // their wallet paying the worker's address; here it is one tap.
      const tx = await payNim(wallet!.address, job.amount)
      job.draft = {
        id: 'r-' + Date.now().toString(36),
        job: job.title, poster: job.poster, worker: job.worker || state.name,
        amount: job.amount, tx, at: new Date().toISOString().slice(0, 10),
        posterSig: '', workerSig: '', prev: tip(),
      }
      job.tx = tx; job.phase = 2
      toast('Paid. Now the poster signs the receipt — a separate, deliberate step.')
    }
    if (action === 'sign-poster' && job && job.draft) {
      btn.disabled = true; btn.textContent = 'Waiting for signature…'
      const sig = await signMessage(receiptText(job.draft))
      job.draft.posterSig = sig.signature
      job.posterSigned = true
      toast('Poster signed. The worker countersigns to seal the receipt.')
    }
    if (action === 'seal' && job && job.draft) {
      btn.disabled = true; btn.textContent = 'Waiting for signature…'
      const sig = await signMessage(receiptText(job.draft))
      const base = { ...job.draft, workerSig: sig.signature }
      const hash = await hashReceipt(base)
      state.receipts.push({ ...base, hash })
      job.phase = 3
      lastCheck = null
      chainVerified = false
      confetti()
      toast('Receipt sealed into your Earn Passport chain ⚡')
    }
    if (action === 'share-job' && job) {
      const link = jobLink(job)
      await copyText(link)
      toast('Job link copied — anyone can open it and claim or pay')
    }
    save(); render()
  } catch (e: any) {
    toast(e?.message || 'Something went wrong')
    render()
  }
}

function jobLink(job: Job): string {
  const payload = btoa(unescape(encodeURIComponent(JSON.stringify(job))))
  return `${location.origin}${location.pathname}#j=${payload}`
}

async function copyText(t: string) {
  try { await navigator.clipboard.writeText(t) } catch { /* clipboard may be blocked */ }
}

async function runVerify(receipts: Receipt[], name: string) {
  const nodes = document.querySelectorAll('.receipt')
  for (let i = 0; i < nodes.length; i++) {
    nodes[i].classList.add('checking')
    await new Promise((r) => setTimeout(r, 320))
    nodes[i].classList.remove('checking')
    nodes[i].classList.add('verified')
  }
  const check = await verifyChain(receipts)
  chainVerified = check.ok
  lastCheck = check.ok ? `Chain intact · ${check.count} receipts · ${fmt(check.total)} NIM proven for ${name}` : `Chain broken at receipt ${check.brokenAt + 1}`
  render()
  if (check.ok) toast('Every hash re-checked in your browser. Chain intact.')
}

// ———————————————————————— Render ————————————————————————

const app = document.getElementById('app')!

function passportCard(name: string, receipts: Receipt[], address: string, editable: boolean): string {
  const total = receipts.reduce((s, r) => s + r.amount, 0)
  const posters = new Set(receipts.map((r) => r.poster)).size
  return `
  <section class="passport">
    <div class="pp-head"><span class="kicker">EARN PASSPORT</span><span class="seal">✓</span></div>
    <div class="pp-who">
      <div class="avatar">${esc(initials(name))}</div>
      <div>
        <div class="pp-name">${esc(name)}</div>
        <div class="pp-addr">${esc(address)}</div>
      </div>
    </div>
    <div class="pp-total">
      <div class="lbl">Verified earnings</div>
      <div class="amt">${fmt(total)} <small>NIM</small></div>
    </div>
    <div class="pp-stats">
      <div class="pp-stat"><b>${receipts.length}</b><span>jobs sealed</span></div>
      <div class="pp-stat"><b>${posters}</b><span>clients</span></div>
      <div class="pp-stat"><b>${receipts.length * 2}</b><span>signatures</span></div>
    </div>
    ${lastCheck ? `<div class="chain-pill ${lastCheck.startsWith('Chain intact') ? 'ok' : 'bad'}">${lastCheck.startsWith('Chain intact') ? '⛓' : '⚠'} ${esc(lastCheck)}</div>` : ''}
    ${editable ? `<div class="pp-actions">
      <button class="btn btn-gold" data-action="verify">Verify my chain</button>
      <button class="btn btn-ghost" data-action="share-passport">Share passport</button>
    </div>` : ''}
  </section>`
}

function receiptChain(receipts: Receipt[]): string {
  if (!receipts.length) return '<p class="mut">No receipts yet. Finish a job and the first link of your chain appears here.</p>'
  return `<div class="chain">` + receipts.map((r, i) => `
    <div class="receipt ${chainVerified ? 'verified' : ''}">
      <div class="node">${i + 1}</div>
      <div class="rcard">
        <div style="display:flex;gap:8px;align-items:flex-start">
          <div>
            <h3 style="font-size:15px">${esc(r.job)}</h3>
            <div class="mut">from ${esc(r.poster)} · ${esc(r.at)}</div>
          </div>
          <div class="job-amt"><b>${fmt(r.amount)}</b><span>NIM</span></div>
        </div>
        <div class="sig-note">
          <span class="hash-chip">#${esc(r.hash.slice(0, 12))}…</span>
          <span class="sig-chip have">✓ poster signed</span>
          <span class="sig-chip have">✓ worker signed</span>
        </div>
      </div>
    </div>`).join('') + `</div>`
}

function jobCard(job: Job): string {
  const label = ['Open', 'Claimed', job.posterSigned ? 'Paid · poster signed' : 'Paid · awaiting poster signature', 'Sealed'][job.phase]
  const cls = ['open', 'claimed', 'claimed', 'paid'][job.phase]
  const done = job.phase === 0 ? 1 : job.phase === 1 ? 2 : job.phase === 2 ? 3 : 4
  let actions = ''
  if (job.phase === 0) actions = `<button class="btn btn-gold small" data-action="claim" data-id="${job.id}">Claim this job</button>`
  if (job.phase === 1) actions = `<button class="btn btn-violet small" data-action="pay" data-id="${job.id}">Work done — pay ${fmt(job.amount)} NIM &amp; sign</button>`
  if (job.phase === 2 && !job.posterSigned) actions = `<button class="btn btn-gold small" data-action="sign-poster" data-id="${job.id}">Poster: sign the receipt</button>`
  if (job.phase === 2 && job.posterSigned) actions = `<button class="btn btn-gold small" data-action="seal" data-id="${job.id}">Worker: countersign &amp; seal receipt</button>`
  if (job.phase === 3) actions = `<span class="sig-chip have">⛓ receipt sealed in the passport chain</span>`
  return `
  <article class="card job">
    <div class="job-top">
      <div>
        <span class="status ${cls}">${label}</span>
        <h3 style="margin-top:8px">${esc(job.title)}</h3>
        <div class="mut" style="margin-top:4px">${esc(job.detail)}</div>
        <div class="mut" style="margin-top:6px">Posted by ${esc(job.poster)}${job.worker ? ` · claimed by ${esc(job.worker)}` : ''}</div>
      </div>
      <div class="job-amt"><b>${fmt(job.amount)}</b><span>NIM</span></div>
    </div>
    <div class="steps">${[1, 2, 3, 4].map((s) => `<div class="step ${s <= done ? 'done' : ''}"></div>`).join('')}</div>
    <div class="job-actions">${actions}<button class="btn btn-ghost small" data-action="share-job" data-id="${job.id}">Share job link</button></div>
    ${job.phase >= 2 ? `<div class="sig-note"><span class="sig-chip ${job.posterSigned || job.phase >= 3 ? 'have' : ''}">${job.posterSigned || job.phase >= 3 ? '✓' : '…'} poster signed</span><span class="sig-chip ${job.phase >= 3 ? 'have' : ''}">${job.phase >= 3 ? '✓' : '…'} worker countersigned</span>${job.tx ? `<span class="hash-chip">tx ${esc(job.tx.slice(0, 14))}…</span>` : ''}</div>` : ''}
  </article>`
}

function render() {
  if (linkError) {
    app.innerHTML = `
      <div class="bg"></div>
      <section class="hero">
        <div class="logo-row"><div class="logo">★</div><div><div class="logo-name">Earn<b>est</b></div><div class="logo-sub">GET PAID · GET PROOF</div></div></div>
        <h1 class="hero-line">This passport link<br /><span class="grad">is broken.</span></h1>
        <p class="hero-sub">It was edited, cut off, or never a real Earn Passport link. A genuine passport link always verifies in full — that is the whole point of the chain.</p>
        <a class="btn btn-gold" href="/" style="text-decoration:none;display:inline-block;margin-top:10px">Open Earnest</a>
      </section>`
    return
  }
  if (publicView) {
    app.innerHTML = `
      ${headerHtml()}
      <div class="share-banner">🔎 You are looking at a public <b>Earn Passport</b>. Every receipt below was signed by both the client and the worker, and chained to the one before it. Press verify and your own browser re-checks the whole chain.</div>
      <div class="pp-grid"><div class="pp-left">${passportCard(publicView.name, publicView.receipts, 'public passport', false)}
      <div class="pp-actions" style="margin-top:12px"><button class="btn btn-gold" data-action="verify-public">Verify this chain</button></div>
      </div><div class="pp-right"><div class="sec-t"><span class="n">⛓</span> Receipt chain</div>
      ${receiptChain(publicView.receipts)}</div></div>
      <footer class="foot">Earnest — get paid, get proof. Built on Nimiq Pay.</footer>`
    return
  }

  if (!wallet) {
    app.innerHTML = `
      ${headerHtml()}
      <section class="hero">
        <h1 class="hero-line">Get paid.<br /><span class="grad">Get proof.</span></h1>
        <p class="hero-sub">Do the work, get paid in NIM, and every job seals a dual-signed receipt into your Earn Passport.</p>
        <div class="wallet-chip" style="margin-top:14px"><span class="dot"></span>Connecting to Nimiq Pay…</div>
      </section>`
    return
  }
  const w = wallet!
  const myReceipts = state.receipts
  app.innerHTML = `
    ${headerHtml()}
    <div class="hero-line">Get paid.<br /><span class="grad">Get proof.</span></div>
    <p class="hero-sub">Do the work, get paid in NIM, and every job seals a dual-signed receipt into your Earn Passport — a proof-of-earnings chain no client can dispute and no platform can take away.</p>
    <nav class="tabs">
      <button class="tab ${tab === 'passport' ? 'on' : ''}" data-action="tab" data-id="passport">Passport</button>
      <button class="tab ${tab === 'jobs' ? 'on' : ''}" data-action="tab" data-id="jobs">Jobs</button>
      <button class="tab ${tab === 'grow' ? 'on' : ''}" data-action="tab" data-id="grow">Grow</button>
    </nav>
    ${tab === 'passport' ? `
      <div class="pp-grid"><div class="pp-left">${passportCard(state.name, myReceipts, w.address, true)}</div><div class="pp-right">
      <div class="sec-t"><span class="n">⛓</span> Receipt chain</div>
      ${receiptChain(myReceipts)}</div></div>
      <div class="notice">How the proof works: each receipt commits to the hash of the one before it, and both parties sign it with their wallets. Edit or delete any receipt and every later hash breaks — that is what “verify” re-checks, in the browser, in seconds.</div>
      <div class="card" style="margin-top:12px">
        <h3>Your worker name</h3>
        <p class="mut" style="margin:5px 0 2px">This is the name clients see on your receipts and your passport.</p>
        <label class="f" for="name-input">Name</label>
        <input id="name-input" value="${esc(state.name)}" maxlength="40" />
        <div class="job-actions"><button class="btn btn-ghost small" data-action="save-name">Save name</button></div>
      </div>
    ` : ''}
    ${tab === 'jobs' ? `
      <div class="sec-t"><span class="n">◆</span> Open board</div>
      <div class="jobs-grid">${state.jobs.map(jobCard).join('')}</div>
      <div class="card">
        <h3>Post a job</h3>
        <label class="f" for="j-title">What needs doing?</label>
        <input id="j-title" placeholder="e.g. Design a menu for my café" maxlength="90" />
        <label class="f" for="j-detail">Details</label>
        <textarea id="j-detail" placeholder="Scope, deadline, anything the worker should know" maxlength="240"></textarea>
        <label class="f" for="j-amount">Bounty (NIM)</label>
        <input id="j-amount" type="number" min="1" placeholder="150" />
        <label class="f" for="j-poster">Your name or studio</label>
        <input id="j-poster" placeholder="e.g. My Studio" maxlength="40" />
        <div class="job-actions"><button class="btn btn-gold" data-action="post-job">Post job</button></div>
      </div>
    ` : ''}
    ${tab === 'grow' ? `
      <div class="grow-grid"><div class="card">
        <h3>Your earnings, still working</h3>
        <p class="mut" style="margin-top:5px">Money you earned should not sit still. Stake NIM straight from Earnest through Nimiq Pay's staking transactions — the same wallet, no new account, no exchange.</p>
        <div class="pp-stats" style="margin-top:14px">
          <div class="pp-stat"><b>${w.balanceNim !== null ? fmt(w.balanceNim) : '—'}</b><span>wallet NIM</span></div>
          <div class="pp-stat"><b>${fmt(state.staked)}</b><span>staked via Earnest</span></div>
        </div>
        <label class="f" for="s-amount">Amount to stake (NIM)</label>
        <input id="s-amount" type="number" min="100" value="200" />
        <label class="f" for="s-validator">Validator address (your pool publishes theirs)</label>
        <input id="s-validator" value="NQ48 8CKH BA24 2VR3 N249 N8MN J5XX 74DB XTP3" />
        <div class="job-actions"><button class="btn btn-violet" data-action="stake">Stake NIM</button></div>
        <p class="mut" style="margin-top:10px">Staking rewards come from the network and vary by pool; nothing here is a guaranteed return. Minimum stake on Nimiq is 100 NIM.</p>
        ${state.stakeTxs.length ? `<div class="sig-note">${state.stakeTxs.map((t) => `<span class="hash-chip">stake tx ${esc(t.slice(0, 14))}…</span>`).join('')}</div>` : ''}
      </div>
      <div class="notice">Earnest uses more of the Nimiq Pay toolkit than a payment button: basic transactions for pay, message signing for receipts, and the staking transaction family for Grow.</div></div>
    ` : ''}
    <footer class="foot">
      ${isDemo() ? 'Demo wallet in this browser — inside Nimiq Pay, payments, signatures and staking are real, on your own wallet.' : 'Connected to your Nimiq Pay wallet.'}<br />
      Earnest never holds your money: pay goes wallet to wallet, and your passport lives in links you control.
    </footer>
    <div class="toast" id="toast"></div>
    <canvas id="confetti"></canvas>`
}

function headerHtml(): string {
  const w = wallet
  return `
  <header class="top">
    <div>
      <div class="logo"><span class="mark"><svg viewBox="0 0 24 24" fill="none"><path d="M12 2l2.4 4.9 5.4.8-3.9 3.8 1 5.4L12 14.3 7.1 16.9l1-5.4-3.9-3.8 5.4-.8z" fill="#191003"/></svg></span><span>Earn<em>est</em></span></div>
      <div class="tagline">get paid · get proof</div>
    </div>
    ${w ? `<div class="wallet-chip ${w.mode}"><span class="dot"></span>${w.mode === 'demo' ? 'Demo wallet' : shortAddress(w.address)}${w.balanceNim !== null ? ` · ${fmt(w.balanceNim)} NIM` : ''}</div>` : ''}
  </header>`
}

// ———————————————————————— Toast & confetti ————————————————————————

let toastTimer: number | undefined
function toast(msg: string) {
  const el = document.getElementById('toast')
  if (!el) return
  el.textContent = msg
  el.classList.add('show')
  clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => el.classList.remove('show'), 3400)
}

function confetti() {
  const c = document.getElementById('confetti') as HTMLCanvasElement | null
  if (!c) return
  c.width = innerWidth; c.height = innerHeight
  const ctx = c.getContext('2d')!
  const colors = ['#eec25e', '#7c5cff', '#2dd4bf', '#f2f4fa']
  const parts = Array.from({ length: 90 }, () => ({
    x: innerWidth / 2 + (Math.random() - 0.5) * 220, y: innerHeight * 0.32,
    vx: (Math.random() - 0.5) * 7, vy: -Math.random() * 8 - 3,
    s: Math.random() * 6 + 3, col: colors[Math.floor(Math.random() * colors.length)],
    r: Math.random() * Math.PI,
  }))
  let frames = 0
  const tick = () => {
    ctx.clearRect(0, 0, c.width, c.height)
    for (const p of parts) {
      p.x += p.vx; p.y += p.vy; p.vy += 0.22; p.r += 0.1
      ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r)
      ctx.fillStyle = p.col; ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s * 0.62); ctx.restore()
    }
    if (++frames < 90) requestAnimationFrame(tick)
    else ctx.clearRect(0, 0, c.width, c.height)
  }
  tick()
}

// ———————————————————————— Events & init ————————————————————————

app.addEventListener('click', async (e) => {
  const btn = (e.target as HTMLElement).closest('button') as HTMLButtonElement | null
  if (!btn) return
  const action = btn.dataset.action
  if (!action) return
  if (action === 'tab') { tab = btn.dataset.id as typeof tab; render(); return }
  if (action === 'verify') { await runVerify(state.receipts, state.name); return }
  if (action === 'verify-public' && publicView) { await runVerify(publicView.receipts, publicView.name); return }
  if (action === 'share-passport') {
    const link = `${location.origin}${location.pathname}#p=${encodeChain(state.receipts, state.name)}`
    await copyText(link)
    toast('Passport link copied — anyone opening it can verify your chain')
    return
  }
  if (action === 'save-name') {
    const v = (document.getElementById('name-input') as HTMLInputElement).value.trim()
    if (v) { state.name = v; save(); render(); toast('Name saved') }
    return
  }
  if (action === 'post-job') {
    const title = (document.getElementById('j-title') as HTMLInputElement).value.trim()
    const detail = (document.getElementById('j-detail') as HTMLTextAreaElement).value.trim()
    const amount = parseFloat((document.getElementById('j-amount') as HTMLInputElement).value)
    const poster = (document.getElementById('j-poster') as HTMLInputElement).value.trim()
    if (!title || !amount || amount <= 0 || !poster) { toast('Give the job a title, a bounty and your name'); return }
    state.jobs.unshift({ id: 'job-' + Date.now().toString(36), title, detail: detail || 'No details provided.', amount, poster, worker: null, phase: 0 })
    save(); render(); toast('Job posted to the board')
    return
  }
  if (action === 'stake') {
    const amount = parseFloat((document.getElementById('s-amount') as HTMLInputElement).value)
    const validator = (document.getElementById('s-validator') as HTMLInputElement).value.trim()
    if (!amount || amount < 100) { toast('Minimum stake is 100 NIM'); return }
    if (wallet && wallet.balanceNim !== null && amount > wallet.balanceNim) { toast(`That is more than your wallet balance (${fmt(wallet.balanceNim)} NIM)`); return }
    btn.disabled = true; btn.textContent = 'Waiting for wallet approval…'
    try {
      const tx = await stakeNim(validator, amount, state.stakerCreated)
      state.staked += amount; state.stakerCreated = true; state.stakeTxs.push(tx)
      save(); render(); confetti(); toast(`Staked ${fmt(amount)} NIM ⚡`)
    } catch (err: any) { toast(err?.message || 'Staking was not completed'); render() }
    return
  }
  const id = btn.dataset.id
  if (id && ['claim', 'pay', 'sign-poster', 'seal', 'share-job'].includes(action)) await act(action, id, btn)
})

async function init() {
  const hash = location.hash
  if (hash.startsWith('#p=')) {
    const decoded = decodeChain(hash.slice(3))
    state = load() || { name: 'Toba', jobs: seedJobs(), receipts: [], staked: 0, stakerCreated: false, stakeTxs: [] }
    if (!decoded) { linkError = true; render(); return }
    publicView = { name: decoded.name, receipts: decoded.receipts }
    render()
    return
  }
  const existing = load()
  if (existing) state = existing
  else {
    state = { name: 'Toba', jobs: seedJobs(), receipts: await seedReceipts('Toba'), staked: 0, stakerCreated: false, stakeTxs: [] }
    save()
  }
  if (hash.startsWith('#j=')) {
    try {
      const job = JSON.parse(decodeURIComponent(escape(atob(hash.slice(3))))) as Job
      if (job && job.id && !state.jobs.some((j) => j.id === job.id)) {
        state.jobs.unshift(job); save()
        setTimeout(() => toast(`Job imported: “${job.title}”`), 400)
      }
      tab = 'jobs'
    } catch { /* ignore malformed links */ }
  }
  render()
  wallet = await connectWallet()
  render()
}

window.addEventListener('hashchange', () => location.reload())

init()
