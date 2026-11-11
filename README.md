# Earnest

**Get paid. Get proof.** Earnest is a Nimiq Pay Mini App where gig work produces something freelancers have never owned: portable, verifiable proof of earnings.

Do a job, get paid wallet-to-wallet in NIM, and both sides sign the receipt. Every receipt joins your **Earn Passport**, chained to the one before it by SHA-256 hash, so your whole earnings history is tamper-evident and verifiable by anyone with the link — in their browser, with no server and no account. Then stake what you earned through Nimiq Pay's own staking transactions, without leaving the app.

**Live:** https://earnest-app2.netlify.app (open it inside Nimiq Pay for real payments, signatures and staking; in a normal browser it runs on a clearly labelled demo wallet so the full flow can be tried)

Built for the [Nimiq Mini Apps Competition](https://miniappscompetition.com/), Cycle III, Earn category. MIT licensed.

## How it works

1. **Post or claim a job.** A client posts a bounty in NIM and shares one link (`#j=…`). Anyone can open it and claim the job.
2. **Get paid.** Payment is a normal Nimiq basic transaction, wallet to wallet. Earnest never holds funds.
3. **Both sides sign.** The client wallet-signs the receipt (work accepted, amount paid, transaction reference); the worker countersigns (money received). A receipt only exists when both signatures exist.
4. **The chain seals it.** Each receipt commits to the previous receipt's hash (`src/chain.ts`). The passport's total is the sum of the chain — edit, delete or reorder any receipt and verification fails at exactly that link.
5. **Share and verify.** The passport travels as one link (`#p=…`). The public view re-runs the full chain check client-side.
6. **Grow.** The Grow tab creates a staker or adds stake through the SDK's staking transaction family (`sendNewStakerTransaction` / `sendStakeTransaction`).

## Nimiq integration

| Capability | SDK surface |
| --- | --- |
| Job payments | `sendBasicTransaction` |
| Dual-signed receipts | `sign` (message signing) |
| Staking earnings | `sendNewStakerTransaction`, `sendStakeTransaction` |
| Wallet context | `init`, `listAccounts`, `getBalance`, `getBlockNumber`, `isConsensusEstablished`, `getHostNetwork` |

SDK: `@nimiq/mini-app-sdk` 0.2.5, pinned.

## Honest limits

- Receipts prove both parties signed the same statement about a payment; they cannot prove the work was good. Disputes still need humans.
- Jobs and passports are local-first (browser storage + shareable links). There is no server and no global job index yet.
- Outside Nimiq Pay, a demo wallet simulates approvals so judges can run the full flow; nothing in demo mode touches a chain.

## Run it

```bash
npm install
npm run dev      # local dev
npm run build    # typecheck + production build into dist/
npm run preview  # serve the production build
```

## License

MIT — see `LICENSE`.
