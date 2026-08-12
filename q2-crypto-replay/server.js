const express = require('express');
const crypto = require('crypto');

const app = express();
app.use(express.text({ type: 'application/json' })); 

const transactions = {}; 

app.post('/api/transaction', (req, res) => {
    const tx_id = crypto.randomUUID();
    const salt = crypto.randomBytes(16).toString('hex');
    
    transactions[tx_id] = { salt: salt, processedTokens: new Set() };
    
    res.set('X-Challenge-Token', salt);
    res.status(201).json({ transaction_id: tx_id, status: "created" });
});

app.put('/api/transaction/:id', (req, res) => {
    const tx_id = req.params.id;
    if (!transactions[tx_id]) {
        return res.status(404).json({ error: "Transaction not found" });
    }

    const salt = transactions[tx_id].salt;
    const clientMac = req.get('X-Frugal-Mac');
    const clientTimestamp = req.get('X-Timestamp');

    if (!clientMac || !clientTimestamp) {
        return res.status(400).json({ error: "Missing cryptographic headers" });
    }

    const rawBody = req.body; 
    const payloadToHash = salt + clientTimestamp + rawBody;
    const expectedMac = crypto.createHmac('sha512', salt).update(payloadToHash).digest('hex');

    if (clientMac !== expectedMac) {
        return res.status(401).json({ error: "Invalid HMAC signature" });
    }

    const replayKey = `${clientMac}_${clientTimestamp}`;
    if (transactions[tx_id].processedTokens.has(replayKey)) {
        return res.status(409).json({ error: "Conflict: Cryptographic Replay Attack Detected" });
    }

    transactions[tx_id].processedTokens.add(replayKey);
    return res.status(200).json({ message: "Transaction updated securely", transaction_id: tx_id });
});

const PORT = 3006;
app.listen(PORT, () => {
    console.log(`[Mock Gateway] High-Security API listening on port ${PORT}`);
});
