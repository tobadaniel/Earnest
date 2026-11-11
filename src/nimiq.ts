// Wallet adapter for NimStake.
// Inside Nimiq Pay it talks to the real wallet through @nimiq/mini-app-sdk.
// Outside Nimiq Pay (regular browser, judges, desktop) it falls back to a
// clearly-labelled demo wallet so the full flow can be tried end to end.
import { init, getHostNetwork, type NimiqProvider } from '@nimiq/mini-app-sdk'

export interface Wallet {
  mode: 'nimiq' | 'demo'
  address: string
  balanceNim: number | null
  network: string
  blockNumber: number | null
  consensus: boolean | null
}

let provider: NimiqProvider | null = null
const DEMO_ADDRESS = 'NQ48 8CKH BA24 2VR3 N249 N8MN J5XX 74DB XTP3'

function fakeTxId(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return 'demo-' + Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

export async function connectWallet(): Promise<Wallet> {
  try {
    provider = await init({ timeout: 4000 })
    const accounts = await provider.listAccounts()
    if (!accounts || !Array.isArray(accounts) || accounts.length === 0) {
      throw new Error('No accounts returned')
    }
    const address = accounts[0] as string
    let balanceNim: number | null = null
    let blockNumber: number | null = null
    let consensus: boolean | null = null
    try {
      const bal = await provider.getBalance(address)
      if (typeof bal === 'number') balanceNim = bal / 1e5
    } catch { /* balance is a nice-to-have */ }
    try { blockNumber = await provider.getBlockNumber() } catch { /* optional */ }
    try { consensus = await provider.isConsensusEstablished() } catch { /* optional */ }
    return {
      mode: 'nimiq',
      address,
      balanceNim,
      network: getHostNetwork() ?? 'mainnet',
      blockNumber,
      consensus,
    }
  } catch {
    provider = null
    return {
      mode: 'demo',
      address: DEMO_ADDRESS,
      balanceNim: 12480.5,
      network: 'demo',
      blockNumber: null,
      consensus: null,
    }
  }
}

export function isDemo(): boolean {
  return provider === null
}

/** Pay `amountNim` NIM to `recipient`. Resolves with a transaction reference. */
export async function payNim(recipient: string, amountNim: number): Promise<string> {
  const value = Math.round(amountNim * 1e5) // NIM -> luna
  if (!provider) {
    await new Promise((r) => setTimeout(r, 900)) // simulate the native approval dialog
    return fakeTxId()
  }
  const result = await provider.sendBasicTransaction({ recipient, value })
  if (typeof result !== 'string') {
    throw new Error((result as any)?.error?.message || 'Payment was not completed')
  }
  return result
}

/** Ask the wallet to sign a text message (used for the settlement receipt). */
export async function signMessage(message: string): Promise<{ publicKey: string; signature: string }> {
  if (!provider) {
    await new Promise((r) => setTimeout(r, 600))
    return { publicKey: 'demo-public-key', signature: fakeTxId() + fakeTxId() }
  }
  const result = await provider.sign(message)
  if ((result as any)?.error) {
    throw new Error((result as any).error.message || 'Signing was not completed')
  }
  return result as { publicKey: string; signature: string }
}

export function shortAddress(address: string): string {
  const clean = address.replace(/\s/g, '')
  if (clean.length <= 14) return address
  return clean.slice(0, 6) + '…' + clean.slice(-6)
}

export function explorerTxUrl(txRef: string, network: string): string | null {
  if (!txRef || txRef.startsWith('demo-')) return null
  const base = network === 'testnet' ? 'https://testnet.nimiq.watch' : 'https://nimiq.watch'
  return base
}

/**
 * Stake NIM through the Mini App SDK's staking transactions.
 * First stake creates a staker delegated to `delegation` (a validator address);
 * later stakes add to the existing staker. In demo mode the confirmation is
 * simulated so the Grow flow works in a normal browser.
 */
export async function stakeNim(delegation: string, amountNim: number, alreadyStaker: boolean): Promise<string> {
  const value = Math.round(amountNim * 1e5)
  if (!provider) {
    await new Promise((r) => setTimeout(r, 900))
    return fakeTxId()
  }
  const p = provider as any
  const result = alreadyStaker && typeof p.sendStakeTransaction === 'function'
    ? await p.sendStakeTransaction({ value })
    : await p.sendNewStakerTransaction({ delegation, value })
  if (typeof result !== 'string') {
    throw new Error((result as any)?.error?.message || 'Staking was not completed')
  }
  return result
}
