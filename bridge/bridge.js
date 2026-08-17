/**
 * bridge.js
 * ---------
 * Puente MINIMO entre Python y Minecraft Java Edition, usando
 * mineflayer. Este archivo NO contiene logica de alto nivel (no sabe
 * que es una "formacion" ni un "reunir"): solo expone primitivas
 * (connect, disconnect, chat, command, move_to, jump, look_at,
 * follow, stop) via WebSocket con mensajes JSON, y reenvia el estado
 * de cada bot (status, position, health, chat, spawn, error) a quien
 * este escuchando.
 *
 * Toda la arquitectura, decisiones de "quien va a donde" y logica que
 * el usuario pueda ampliar viven en Python (ver bots/, controllers/).
 * Este bridge se mantiene deliberadamente pequenyo.
 *
 * Protocolo (JSON por linea sobre WebSocket):
 *
 *   Python -> Bridge
 *     {type:"connect", botId, name, host, port, version, auth}
 *     {type:"disconnect", botId}
 *     {type:"chat", botId, message}
 *     {type:"command", botId, command}
 *     {type:"move_to", botId, x, y, z}
 *     {type:"jump", botId}
 *     {type:"look_at", botId, x, y, z}
 *     {type:"follow", botId, targetType, target}
 *     {type:"stop", botId}
 *
 *   Bridge -> Python
 *     {type:"status", botId, state, error?}
 *     {type:"position", botId, x, y, z, yaw, pitch}
 *     {type:"health", botId, health, food}
 *     {type:"chat", botId, message}
 *     {type:"spawn", botId}
 *     {type:"goal_reached", botId}
 *     {type:"error", botId, message}
 *     {type:"bridge_log", level, message}
 */

'use strict';

const WebSocket = require('ws');
const mineflayer = require('mineflayer');
const { Vec3 } = require('vec3');

const HOST = process.env.BRIDGE_HOST || '127.0.0.1';
const PORT = parseInt(process.env.BRIDGE_PORT || '8765', 10);

const POSITION_TICK_MS = 500;
const MOVE_TICK_MS = 150;
const FOLLOW_TICK_MS = 250;
const ARRIVE_DISTANCE = 0.6;
const FOLLOW_STOP_DISTANCE = 2.5;

/** botId (number) -> { bot, moveInterval, followInterval, host, port } */
const bots = new Map();

const wss = new WebSocket.Server({ host: HOST, port: PORT });
const clients = new Set();

function log(message, level = 'INFO') {
  const line = `[${level}] ${message}`;
  // eslint-disable-next-line no-console
  console.log(line);
  broadcast({ type: 'bridge_log', level, message });
}

function broadcast(payload) {
  const raw = JSON.stringify(payload);
  for (const ws of clients) {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(raw);
    }
  }
}

function clearMoveInterval(entry) {
  if (entry.moveInterval) {
    clearInterval(entry.moveInterval);
    entry.moveInterval = null;
  }
}

function clearFollowInterval(entry) {
  if (entry.followInterval) {
    clearInterval(entry.followInterval);
    entry.followInterval = null;
  }
}

function cleanupBot(botId) {
  const entry = bots.get(botId);
  if (!entry) return;
  clearMoveInterval(entry);
  clearFollowInterval(entry);
  bots.delete(botId);
}

// ---------------------------------------------------------------------
// Conexion / desconexion
// ---------------------------------------------------------------------

function connectBot({ botId, name, host, port, version, auth }) {
  if (bots.has(botId)) {
    log(`Bot ${botId} ya existia, desconectando antes de reconectar`, 'WARN');
    disconnectBot(botId);
  }

  broadcast({ type: 'status', botId, state: 'CONNECTING' });

  let bot;
  try {
    bot = mineflayer.createBot({
      host,
      port,
      username: name,
      version: version && version !== 'auto' ? version : false,
      auth: auth === 'microsoft' ? 'microsoft' : 'offline',
    });
  } catch (err) {
    broadcast({ type: 'status', botId, state: 'ERROR', error: String(err.message || err) });
    return;
  }

  const entry = { bot, moveInterval: null, followInterval: null, host, port };
  bots.set(botId, entry);

  bot.once('login', () => {
    broadcast({ type: 'status', botId, state: 'CONNECTED' });
  });

  bot.once('spawn', () => {
    broadcast({ type: 'spawn', botId });
  });

  bot.on('end', (reason) => {
    broadcast({ type: 'status', botId, state: 'DISCONNECTED', error: reason ? String(reason) : undefined });
    cleanupBot(botId);
  });

  bot.on('kicked', (reason) => {
    broadcast({ type: 'error', botId, message: `Expulsado por el servidor: ${reason}` });
  });

  bot.on('error', (err) => {
    broadcast({ type: 'status', botId, state: 'ERROR', error: String(err.message || err) });
  });

  bot.on('chat', (username, message) => {
    broadcast({ type: 'chat', botId, message: `<${username}> ${message}` });
  });
}

function disconnectBot(botId) {
  const entry = bots.get(botId);
  if (!entry) {
    broadcast({ type: 'status', botId, state: 'DISCONNECTED' });
    return;
  }
  clearMoveInterval(entry);
  clearFollowInterval(entry);
  try {
    entry.bot.quit();
  } catch (err) {
    log(`Error al desconectar bot ${botId}: ${err.message}`, 'WARN');
  }
  cleanupBot(botId);
  broadcast({ type: 'status', botId, state: 'DISCONNECTED' });
}

// ---------------------------------------------------------------------
// Movimiento (abstraccion simple: caminar mirando hacia el objetivo)
// ---------------------------------------------------------------------

function moveTo(botId, x, y, z) {
  const entry = bots.get(botId);
  if (!entry || !entry.bot.entity) {
    broadcast({ type: 'error', botId, message: 'move_to: el bot no esta listo (sin entity)' });
    return;
  }
  clearMoveInterval(entry);
  clearFollowInterval(entry);

  const target = new Vec3(x, y, z);

  entry.moveInterval = setInterval(() => {
    const { bot } = entry;
    if (!bot.entity) return;

    const dist = bot.entity.position.distanceTo(target);
    if (dist < ARRIVE_DISTANCE) {
      bot.setControlState('forward', false);
      bot.clearControlStates();
      clearMoveInterval(entry);
      broadcast({ type: 'goal_reached', botId });
      return;
    }

    bot.lookAt(target.offset(0, 1.62, 0), true);
    bot.setControlState('forward', true);

    // Salto ligero si el bot lleva tiempo sin avanzar (posible obstaculo).
    if (bot.entity.velocity && Math.abs(bot.entity.velocity.y) < 0.01) {
      const horizontalSpeed = Math.hypot(bot.entity.velocity.x, bot.entity.velocity.z);
      if (horizontalSpeed < 0.02) {
        bot.setControlState('jump', true);
        setTimeout(() => {
          if (bots.get(botId)) entry.bot.setControlState('jump', false);
        }, 150);
      }
    }
  }, MOVE_TICK_MS);
}

function stopBot(botId) {
  const entry = bots.get(botId);
  if (!entry) return;
  clearMoveInterval(entry);
  clearFollowInterval(entry);
  try {
    entry.bot.clearControlStates();
  } catch (err) {
    // el bot puede no tener entity todavia; no es un error grave
  }
}

function jumpBot(botId) {
  const entry = bots.get(botId);
  if (!entry || !entry.bot.entity) return;
  entry.bot.setControlState('jump', true);
  setTimeout(() => {
    if (bots.get(botId)) entry.bot.setControlState('jump', false);
  }, 250);
}

function lookAtBot(botId, x, y, z) {
  const entry = bots.get(botId);
  if (!entry || !entry.bot.entity) return;
  entry.bot.lookAt(new Vec3(x, y, z), true);
}

// ---------------------------------------------------------------------
// Seguir (jugador / otro bot / coordenadas fijas)
// ---------------------------------------------------------------------

function followTarget(botId, targetType, target) {
  const entry = bots.get(botId);
  if (!entry || !entry.bot.entity) {
    broadcast({ type: 'error', botId, message: 'follow: el bot no esta listo (sin entity)' });
    return;
  }
  clearMoveInterval(entry);
  clearFollowInterval(entry);

  entry.followInterval = setInterval(() => {
    const { bot } = entry;
    if (!bot.entity) return;

    let targetPos = null;
    if (targetType === 'player') {
      const player = bot.players[target];
      if (player && player.entity) targetPos = player.entity.position;
    } else if (targetType === 'bot') {
      const leaderEntry = bots.get(target);
      if (leaderEntry && leaderEntry.bot.entity) targetPos = leaderEntry.bot.entity.position;
    } else if (targetType === 'coords' && target) {
      targetPos = new Vec3(target.x, target.y, target.z);
    }

    if (!targetPos) return;

    const dist = bot.entity.position.distanceTo(targetPos);
    if (dist < FOLLOW_STOP_DISTANCE) {
      bot.setControlState('forward', false);
      return;
    }
    bot.lookAt(targetPos.offset(0, 1.62, 0), true);
    bot.setControlState('forward', true);
  }, FOLLOW_TICK_MS);
}

// ---------------------------------------------------------------------
// Chat / comandos
// ---------------------------------------------------------------------

function sendChat(botId, message) {
  const entry = bots.get(botId);
  if (!entry) {
    broadcast({ type: 'error', botId, message: 'chat: bot no conectado' });
    return;
  }
  try {
    entry.bot.chat(message);
  } catch (err) {
    broadcast({ type: 'error', botId, message: `chat fallo: ${err.message}` });
  }
}

function sendCommand(botId, command) {
  // El servidor de Minecraft interpreta cualquier mensaje que empiece
  // por "/" como comando; no se hace nada especial para saltarse
  // permisos: si el bot no tiene permiso, el propio servidor
  // respondera con un mensaje de error que se reenviara como chat.
  sendChat(botId, command);
}

// ---------------------------------------------------------------------
// Bucle periodico de posicion / vida
// ---------------------------------------------------------------------

setInterval(() => {
  for (const [botId, entry] of bots) {
    const { bot } = entry;
    if (!bot || !bot.entity) continue;
    broadcast({
      type: 'position',
      botId,
      x: bot.entity.position.x,
      y: bot.entity.position.y,
      z: bot.entity.position.z,
      yaw: bot.entity.yaw,
      pitch: bot.entity.pitch,
    });
    if (typeof bot.health === 'number') {
      broadcast({ type: 'health', botId, health: bot.health, food: bot.food });
    }
  }
}, POSITION_TICK_MS);

// ---------------------------------------------------------------------
// Servidor WebSocket
// ---------------------------------------------------------------------

wss.on('connection', (ws) => {
  clients.add(ws);
  log(`Cliente Python conectado (${clients.size} activo/s)`);

  ws.on('message', (raw) => {
    let data;
    try {
      data = JSON.parse(raw.toString());
    } catch (err) {
      log(`Mensaje no-JSON recibido: ${raw}`, 'WARN');
      return;
    }

    const { type, botId } = data;
    try {
      switch (type) {
        case 'connect':
          connectBot(data);
          break;
        case 'disconnect':
          disconnectBot(botId);
          break;
        case 'chat':
          sendChat(botId, data.message);
          break;
        case 'command':
          sendCommand(botId, data.command);
          break;
        case 'move_to':
          moveTo(botId, data.x, data.y, data.z);
          break;
        case 'jump':
          jumpBot(botId);
          break;
        case 'look_at':
          lookAtBot(botId, data.x, data.y, data.z);
          break;
        case 'follow':
          followTarget(botId, data.targetType, data.target);
          break;
        case 'stop':
          stopBot(botId);
          break;
        default:
          log(`Tipo de mensaje desconocido: ${type}`, 'WARN');
      }
    } catch (err) {
      broadcast({ type: 'error', botId, message: `Excepcion procesando '${type}': ${err.message}` });
      log(`Excepcion procesando '${type}' para bot ${botId}: ${err.stack}`, 'ERROR');
    }
  });

  ws.on('close', () => {
    clients.delete(ws);
    log(`Cliente Python desconectado (${clients.size} activo/s)`);
  });
});

log(`Bridge escuchando en ws://${HOST}:${PORT}`);
