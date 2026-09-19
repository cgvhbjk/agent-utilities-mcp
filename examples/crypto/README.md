# USDC client for AI agents

Use real USDC on Base mainnet to pay for individual Agent Utilities calls without a $5 Stripe pack. The Node.js 22+ ES module includes Circle's signing SDK and our required request-binding signature; no npm install is needed. Importing it makes no network request or payment.

Downloads:
- [Client module](https://agent-utilities.agent-utilities.workers.dev/downloads/agent-utilities-crypto.mjs?utm_source=github)
- [SHA-256 checksum](https://agent-utilities.agent-utilities.workers.dev/downloads/agent-utilities-crypto.mjs.sha256?utm_source=github)
- [Runnable GTIN example](https://agent-utilities.agent-utilities.workers.dev/downloads/crypto-example.mjs?utm_source=github)
- [Example checksum](https://agent-utilities.agent-utilities.workers.dev/downloads/crypto-example.mjs.sha256?utm_source=github)
- [License notices](https://agent-utilities.agent-utilities.workers.dev/downloads/CRYPTO-CLIENT-NOTICES.txt?utm_source=github)

## Preview without funds

Download both modules into the same directory, along with their checksum files. Verify and preview:

```sh
shasum -a 256 -c agent-utilities-crypto.mjs.sha256
shasum -a 256 -c crypto-example.mjs.sha256
node crypto-example.mjs --preview
```

Preview is offline. It displays the fixed GTIN input, Base mainnet network and 300-micro-USDC ceiling (0.0003 USDC). No wallet, signature, deposit or API call is needed.

## Prepare and send a real call

Use a separately approved paying wallet with a funded Circle Gateway balance. It must differ from the merchant receiving wallet. Testnet tokens cannot pay mainnet calls. Deposits and withdrawals can incur fees; initial Base deposits can take time. The browser [wallet workspace](https://agent-utilities.agent-utilities.workers.dev/wallet?utm_source=github#wallet) offers funding controls. The client does not deposit, bridge or withdraw money.

Read [/wallet-config](https://agent-utilities.agent-utilities.workers.dev/wallet-config) and independently approve its receiving address. Set these variables through your private secret manager or local environment, never in source, a URL or a shared transcript:

- `BUYER_PRIVATE_KEY`: paying EOA wallet private key; only preparation uses it.
- `PAYMENT_NETWORK`: explicitly `eip155:8453` for this example.
- `PAYMENT_RECIPIENT`: the receiving address you have approved.

```sh
node crypto-example.mjs --prepare ./my-private-call.json
# Review your intended operation. The next command authorizes submission:
node crypto-example.mjs --send ./my-private-call.json
```

Preparation obtains a quote and signs at most 0.0003 USDC for `commerce.gtin-validate` with input `{"code":"036000291452"}`. It writes the signed request to a new file with owner-only permissions and flushes it before returning. It never overwrites an existing file and does not submit settlement. The state file contains a spend authorization and input: keep it private and out of source control.

Send within five minutes of preparation. `--send` needs no private key; it sends the saved request once. It may spend real USDC. After a lost response or an uncertain settlement, repeat **the same `--send` command with the same file**. Recovery lasts ten minutes from the server's first claim. Never prepare a fresh request to retry an uncertain payment, and do not edit the file. If preparation failed and left an empty file, no payment was submitted by that command; inspect the failure before choosing a fresh operation path.

The example deliberately separates signing and sending and performs no automatic reauthorization. Successful output includes a result, Gateway receipt and recovery deadline. Acceptance is not final on-chain confirmation. A failed network response is not proof that no payment occurred.

## Import into your own agent

```js
import { prepareCall, sendPrepared, privateKeyToAccount } from './agent-utilities-crypto.mjs';
```

`prepareCall({url, body, account, maxMicroUsdc, expectedRecipient, expectedNetwork})` requests one quote, checks the ceiling, recipient, network, token and Gateway contract, then creates the two required signatures. `account` may be `privateKeyToAccount(...)` or your signing wallet adapter with `address`, `signTypedData` and `signMessage`. Only EOA signing is supported by this integration. Network may be `eip155:8453` (Base mainnet) or `eip155:84532` (separate test deployment); never infer it from an untrusted quote.

The returned object contains `url`, `body`, `headers` and `quoteExpiresAt`. Persist it privately before the first `sendPrepared(prepared)` if your process may restart. That function sends the object unchanged, does not sign again, does not follow redirects and returns a Fetch Response. Set an independent ceiling for each new logical operation and enforce an overall budget in your agent. A per-call ceiling is not a session spending limit.

Read the chosen tool's schema from [/v1/tools](https://agent-utilities.agent-utilities.workers.dev/v1/tools?utm_source=github). An ordinary x402 client does not automatically support our extra input-binding signature. The downloadable module does. Existing MCP and Python adapters continue to use Stripe credits; importing this module does not change their payment method.
