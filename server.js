const express = require('express');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3000;
const DATA_FILE = path.join(__dirname, 'data', 'sessions.json');

app.use(express.json({ limit: '2mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// ── Storage ──────────────────────────────────────────────────────

function loadData() {
  const dir = path.dirname(DATA_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  if (!fs.existsSync(DATA_FILE)) fs.writeFileSync(DATA_FILE, JSON.stringify({ sessions: [] }, null, 2));
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}

function saveData(data) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
}

// ── Sessions ──────────────────────────────────────────────────────

// GET /api/sessions — список сессий (краткая информация)
app.get('/api/sessions', (req, res) => {
  const data = loadData();
  const list = data.sessions.map(s => ({
    id: s.id,
    employeeName: s.employeeName,
    createdBy: s.createdBy,
    expectedCount: s.expectedCount,
    responseCount: s.responses.length,
    createdAt: s.createdAt,
  }));
  res.json({ sessions: list.reverse() });
});

// POST /api/sessions — создать сессию
app.post('/api/sessions', (req, res) => {
  const { employeeName, expectedCount, createdBy } = req.body;
  if (!employeeName) return res.status(400).json({ error: 'Укажите имя сотрудника' });
  const data = loadData();
  const session = {
    id: crypto.randomBytes(5).toString('hex'),
    adminKey: crypto.randomBytes(10).toString('hex'),
    employeeName: employeeName.trim(),
    createdBy: (createdBy || '').trim(),
    expectedCount: parseInt(expectedCount) || 0,
    createdAt: new Date().toISOString(),
    responses: [],
  };
  data.sessions.push(session);
  saveData(data);
  res.json({ session });
});

// GET /api/sessions/:id — получить сессию
// Без adminKey → только публичная информация
// С правильным adminKey → полные данные с ответами
app.get('/api/sessions/:id', (req, res) => {
  const data = loadData();
  const session = data.sessions.find(s => s.id === req.params.id);
  if (!session) return res.status(404).json({ error: 'Сессия не найдена' });

  if (req.query.adminKey === session.adminKey) {
    res.json({ session });
  } else {
    res.json({
      session: {
        id: session.id,
        employeeName: session.employeeName,
        expectedCount: session.expectedCount,
        responseCount: session.responses.length,
        createdAt: session.createdAt,
      }
    });
  }
});

// DELETE /api/sessions/:id — удалить сессию (требует adminKey)
app.delete('/api/sessions/:id', (req, res) => {
  const { adminKey } = req.body;
  const data = loadData();
  const idx = data.sessions.findIndex(s => s.id === req.params.id);
  if (idx === -1) return res.status(404).json({ error: 'Не найдена' });
  if (data.sessions[idx].adminKey !== adminKey) return res.status(403).json({ error: 'Неверный ключ' });
  data.sessions.splice(idx, 1);
  saveData(data);
  res.json({ success: true });
});

// ── Responses ──────────────────────────────────────────────────────

// POST /api/sessions/:id/responses — добавить ответ
app.post('/api/sessions/:id/responses', (req, res) => {
  const data = loadData();
  const idx = data.sessions.findIndex(s => s.id === req.params.id);
  if (idx === -1) return res.status(404).json({ error: 'Сессия не найдена' });

  const { respondentName, gateAnswers, answers, gateFailed, gateFailedAt, result } = req.body;
  if (!respondentName) return res.status(400).json({ error: 'Укажите имя' });

  const dup = data.sessions[idx].responses.find(
    r => r.respondentName.trim().toLowerCase() === respondentName.trim().toLowerCase()
  );
  if (dup) return res.status(409).json({ error: 'Ответ от этого участника уже записан' });

  const response = {
    id: crypto.randomBytes(4).toString('hex'),
    respondentName: respondentName.trim(),
    gateAnswers: gateAnswers || {},
    answers: answers || {},
    gateFailed: !!gateFailed,
    gateFailedAt: gateFailedAt || null,
    result: result || null,
    submittedAt: new Date().toISOString(),
  };
  data.sessions[idx].responses.push(response);
  saveData(data);
  res.json({ success: true, responseId: response.id });
});

// ── Start ──────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('🚀  Скоринговый инструмент запущен');
  console.log(`\n    Админ-панель:  http://localhost:${PORT}`);
  console.log(`    Опрос для участников выдаётся из панели\n`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('Для остановки нажмите Ctrl+C\n');
});
